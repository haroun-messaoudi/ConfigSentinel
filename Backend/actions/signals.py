from django.dispatch import receiver
from django.utils import timezone

from devices.collector import parse_blocks
from devices.signals import change_request_poll_result
from .models import ChangeRequest


def _normalize_config_line(line):
    return " ".join(line.strip().split()).casefold()


@receiver(change_request_poll_result)
def verify_change_request_after_poll(sender, change_request_id, raw_config=None, error_message=None, **kwargs):
    """Finalize execution only after the device's running config is read back."""
    request = ChangeRequest.objects.filter(pk=change_request_id, status="PENDING").first()
    if request is None:
        return

    if error_message:
        request.status = "FAILED"
        request.error_message = f"Netmiko accepted the commands, but read-back polling failed: {error_message}"
    elif raw_config is None:
        request.status = "FAILED"
        request.error_message = "Netmiko accepted the commands, but no running configuration was returned for verification."
    else:
        expected_blocks = {
            _normalize_config_line(header): content
            for header, content in parse_blocks(request.generated_commands).items()
        }
        actual_blocks = {
            _normalize_config_line(header): content
            for header, content in parse_blocks(raw_config).items()
        }
        missing = []
        remaining = []
        ignored_commands = {"configure terminal", "conf t", "end", "exit"}

        for header, expected_content in expected_blocks.items():
            if header in ignored_commands:
                continue

            if header.startswith("no "):
                target = header[3:].strip()
                if target in actual_blocks:
                    remaining.append(f"section '{target}'")
                continue

            actual_content = actual_blocks.get(header)
            if actual_content is None:
                missing.append(f"section '{header}'")
                continue

            actual_lines = {_normalize_config_line(line) for line in actual_content.splitlines()[1:]}
            for raw_line in expected_content.splitlines()[1:]:
                command = _normalize_config_line(raw_line)
                if not command or command in ignored_commands:
                    continue
                if command.startswith("no "):
                    target = command[3:].strip()
                    if target in actual_lines:
                        remaining.append(f"'{target}' in section '{header}'")
                elif command not in actual_lines:
                    missing.append(f"'{command}' in section '{header}'")

        problems = []
        if not expected_blocks:
            problems.append("no verifiable configuration commands were generated")
        if missing:
            problems.append("not present: " + "; ".join(missing))
        if remaining:
            problems.append("still present after removal: " + "; ".join(remaining))

        if problems:
            request.status = "FAILED"
            request.error_message = "Read-back verification failed; " + ". ".join(problems)
        else:
            request.status = "SUCCESS"
            request.applied_at = timezone.now()
            request.error_message = ""

    request.save(update_fields=["status", "applied_at", "error_message"])