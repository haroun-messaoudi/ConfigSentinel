import logging

from celery import shared_task
from django.db import transaction
from django.utils import timezone
from netmiko import ConnectHandler
from netmiko.exceptions import (
    NetmikoAuthenticationException,
    NetmikoTimeoutException,
    ConfigInvalidException,
)

# Import tasks, models, and permissions from applications
from devices.tasks import pull_config_task
from actions.models import ChangeRequest, DevicePermission

# Matches the standard Cisco/FRR CLI rejection prefixes. Passed to Netmiko's
# send_config_set() so a rejected command aborts the push immediately instead
# of being silently treated as applied.
CLI_ERROR_PATTERN = r"% (Invalid|Incomplete|Ambiguous|Unrecognized|Unknown) "
logger = logging.getLogger(__name__)


@shared_task
def execute_change_request_task(change_request_id):
    """Asynchronously pushes validated configuration changes to network gear via Netmiko."""

    with transaction.atomic():
        try:
            change_request = ChangeRequest.objects.select_for_update().select_related("device", "action_definition", "requested_by").get(pk=change_request_id)
        except ChangeRequest.DoesNotExist:
            return

        if change_request.status != "PENDING":
            return

        device = change_request.device

        if not device.is_active:
            change_request.status = "FAILED"
            change_request.error_message = "Execution aborted: Target device is inactive/disabled."
            change_request.save(update_fields=["status", "error_message"])
            return

        has_permission = DevicePermission.objects.filter(
            user=change_request.requested_by,
            device=device,
            action_definition=change_request.action_definition
        ).exists()

        if not has_permission:
            change_request.status = "FAILED"
            change_request.error_message = f"Permission Denied: User '{change_request.requested_by.username}' lacks execution rights for action '{change_request.action_definition.name}' on device '{device.name}'."
            change_request.save(update_fields=["status", "error_message"])
            return

    try:
        commands_text = change_request.generated_commands
        commands_list = [
            line.strip() for line in commands_text.splitlines()
            if line.strip() and not line.strip().startswith("!")
        ]

        if not commands_list:
            raise Exception("No valid configuration lines generated to push.")

        conn_params = {
            "device_type": device.device_type,
            "host": device.management_ip,
            "port": device.port,
            "username": device.username,
            "password": device.get_password(),
        }

        if device.device_type != "linux":
            enable_secret = device.get_enable_secret()
            conn_params["secret"] = enable_secret or device.get_password()

        with ConnectHandler(**conn_params) as conn:
            if device.device_type != "linux":
                try:
                    already_privileged = conn.check_enable_mode()
                except (NotImplementedError, AttributeError):
                    already_privileged = True

                if not already_privileged:
                    conn.enable()

            # Push the batch config set and let Netmiko itself abort on a
            # device-side rejection (error_pattern), instead of trusting the
            # absence of a Python exception to mean the device accepted it.
            conn.send_config_set(commands_list, error_pattern=CLI_ERROR_PATTERN)

        try:
            pull_config_task.delay(device.id, triggered_by_change_request_id=change_request.id)
        except Exception as exc:
            logger.exception("Could not queue post-execution config poll for request %s", change_request.id)
            change_request.status = "FAILED"
            change_request.error_message = (
                "Netmiko accepted the commands, but the read-back verification "
                f"could not be queued: {exc}"
            )
            change_request.save(update_fields=["status", "error_message"])

    except ConfigInvalidException as e:
        change_request.status = "FAILED"
        change_request.error_message = f"Device rejected the configuration: {str(e)}"
        change_request.save(update_fields=["status", "error_message"])
    except (NetmikoAuthenticationException, NetmikoTimeoutException) as e:
        change_request.status = "FAILED"
        change_request.error_message = f"Network Connection Error: {str(e)}"
        change_request.save(update_fields=["status", "error_message"])
    except Exception as exc:
        change_request.status = "FAILED"
        change_request.error_message = f"Execution Failure: {str(exc)}"
        change_request.save(update_fields=["status", "error_message"])