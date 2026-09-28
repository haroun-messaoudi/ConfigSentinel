import hashlib
from datetime import timedelta
import time
from celery import shared_task
from django.utils import timezone
from netmiko import NetmikoAuthenticationException, NetmikoTimeoutException
from django.db import transaction

from .collector import pull_config, diff_configs, DeviceConnectionError
from .risk import score_diff
from .models import Device, Snapshot, ConfigChange, Alert
from .signals import change_request_poll_result

FAILURE_THRESHOLD = 3


def _mark_poll_failed(device, message):
    device.last_poll_attempted_at = timezone.now()
    device.last_poll_status = "ERROR"
    device.last_poll_error = message
    device.consecutive_failures += 1

    update_fields = ["last_poll_attempted_at", "last_poll_status", "last_poll_error", "consecutive_failures"]

    if device.consecutive_failures >= FAILURE_THRESHOLD and device.is_active:
        device.is_active = False
        update_fields.append("is_active")

    device.save(update_fields=update_fields)


def _announce_poll_result(triggered_by_change_request_id, raw_config=None, error_message=None):
    """Passes post-action running config or poll failure to the actions app."""
    if triggered_by_change_request_id:
        change_request_poll_result.send(
            sender=pull_config_task,
            change_request_id=triggered_by_change_request_id,
            raw_config=raw_config,
            error_message=error_message,
        )


@shared_task
def pull_config_task(device_id, triggered_by_change_request_id=None):
    """Pulls one device right now. Used by the scheduler,
    the 'check now' button, and post-push verification.
    """
    device = Device.objects.get(pk=device_id)

    try:
        start = time.perf_counter()
        raw_text = pull_config(device)
        duration_ms = int((time.perf_counter() - start) * 1000)

    except DeviceConnectionError as e:
        _mark_poll_failed(device, str(e))
        _announce_poll_result(triggered_by_change_request_id, error_message=str(e))
        return

    except Exception as exc:
        _mark_poll_failed(
            device,
            f"Unexpected error: {exc}",
        )
        _announce_poll_result(triggered_by_change_request_id, error_message=f"Unexpected error: {exc}")
        return

    # Successful poll
    completed_at = timezone.now()
    device.last_poll_attempted_at = completed_at
    device.last_poll_status = "OK"
    device.last_poll_error = ""
    device.last_polled_at = completed_at
    device.last_poll_duration_ms = duration_ms
    device.consecutive_failures = 0

    device.save(update_fields=[
        "last_poll_attempted_at",
        "last_poll_status",
        "last_poll_error",
        "last_polled_at",
        "last_poll_duration_ms",
        "consecutive_failures",
    ])

    config_hash = hashlib.sha256(raw_text.encode()).hexdigest()

    with transaction.atomic():
        device = Device.objects.select_for_update().get(pk=device_id)

        latest = device.snapshots.order_by("-taken_at").first()

        if latest and latest.config_hash == config_hash:
            _announce_poll_result(triggered_by_change_request_id, raw_config=raw_text)
            return

        is_first_snapshot = latest is None

        snapshot = Snapshot.objects.create(
            device=device,
            raw_text=raw_text,
            config_hash=config_hash,
            is_baseline=is_first_snapshot,
        )

        if is_first_snapshot:
            _announce_poll_result(triggered_by_change_request_id, raw_config=raw_text)
            return

        diff_text = diff_configs(latest.raw_text, raw_text)

        if not diff_text.strip():
            _announce_poll_result(triggered_by_change_request_id, raw_config=raw_text)
            return

        severity_class, matched_concepts = score_diff(
            diff_text,
            device.detection_profile,
        )

        change = ConfigChange.objects.create(
            device=device,
            old_snapshot=latest,
            new_snapshot=snapshot,
            diff_text=diff_text,
            severity_class=severity_class,
            change_request_id=triggered_by_change_request_id,
            status=(
                "FLAGGED"
                if severity_class is not None
                else "INFORMATIONAL"
            ),
        )

        if matched_concepts:
            change.matched_concepts.set(matched_concepts)

        if severity_class is not None:
            Alert.objects.create(change=change)

        _announce_poll_result(triggered_by_change_request_id, raw_config=raw_text)


@shared_task
def poll_due_devices():
    """Runs frequently via Celery beat. Only actually polls devices whose interval has elapsed."""
    now = timezone.now()
    for device in Device.objects.filter(is_active=True):
        last_poll = device.last_poll_attempted_at or device.last_polled_at
        due = (
            last_poll is None or
            (now - last_poll) >= timedelta(minutes=device.poll_interval_minutes)
        )
        if due:
            pull_config_task.delay(device.id)