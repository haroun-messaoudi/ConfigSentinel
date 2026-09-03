import difflib
from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoAuthenticationException, NetmikoTimeoutException


class DeviceConnectionError(Exception):
    """Raised when we can't reach or authenticate to a device — carries a
    human-readable reason so it can be surfaced in Device.last_poll_error."""


def pull_config(device) -> str:
    """SSH into the device and return its running config as text."""
    conn_params = {
        "device_type": device.device_type,
        "host": device.management_ip,
        "port": device.port,
        "username": device.username,
        "password": device.get_password(),
    }

    if device.device_type != "linux":
        enable_secret = device.get_enable_secret()
        # Netmiko's enable() reads its secret from the connection itself
        # (set here at connect time), not from an argument passed to
        # enable() later. If no enable_secret is configured, fall back to
        # the login password as a best-effort guess.
        conn_params["secret"] = enable_secret or device.get_password()

    try:
        with ConnectHandler(**conn_params) as conn:
            if device.device_type == "linux":
                return conn.send_command('vtysh -c "show running-config"')

            try:
                already_privileged = conn.check_enable_mode()
            except (NotImplementedError, AttributeError):
                already_privileged = True

            if not already_privileged:
                try:
                    conn.enable()
                except ValueError as e:
                    raise DeviceConnectionError(
                        f"Could not enter privileged mode: {e}. "
                        f"This device may require a distinct enable secret — "
                        f"set one on the device record."
                    ) from e

            return conn.send_command("show running-config")

    except NetmikoAuthenticationException as e:
        raise DeviceConnectionError(f"SSH authentication failed: {e}") from e
    except NetmikoTimeoutException as e:
        raise DeviceConnectionError(f"Connection timed out: {e}") from e


# Exact-match lines to drop entirely — fixed strings, no variable content.
_IGNORED_LINES = {
    "Building configuration...",
    "end",
}

# Prefix-match lines to drop — these contain variable content (byte counts,
# timestamps, usernames) that changes on every poll regardless of whether
# the actual device config changed, so they'd otherwise show up as
# permanent false-positive diff noise on every single check.
#   - "Current configuration" covers both:
#       FRR/vtysh:  "Current configuration:"
#       Cisco IOS:  "Current configuration : 7333 bytes"
#   - "! Last configuration change" is Cisco-only IOS metadata
#     (FRR doesn't emit this line, so it's a no-op there — safe either way).
_IGNORED_PREFIXES = (
    "Current configuration",
    "! Last configuration change",
)


def parse_blocks(config_text: str) -> dict:
    """
    Splits a Cisco/FRR-style running-config into structural blocks, keyed
    by their header line (e.g. 'interface eth0', 'router ospf').

    Blocks are delimited by '!' — the real FRR/Cisco structural separator.
    Blank lines are ignored, not treated as terminators, so multi-line
    content (e.g. a banner) doesn't get incorrectly fragmented.

    Known vtysh/IOS preamble/postamble lines (see _IGNORED_LINES and
    _IGNORED_PREFIXES) are filtered out — they're artifacts of the CLI
    tool itself or volatile metadata, not real device configuration, and
    would otherwise register as false-positive "blocks" on every poll.
    """
    blocks = {}
    header = None
    lines = []

    def flush():
        if header is not None:
            blocks[header] = "\n".join(lines)

    for line in config_text.splitlines():
        stripped = line.strip()

        if stripped in _IGNORED_LINES or stripped.startswith(_IGNORED_PREFIXES):
            continue

        if stripped == "":
            continue

        if stripped == "!":
            flush()
            header, lines = None, []
            continue

        if not line.startswith((" ", "\t")):
            flush()
            header = stripped
            lines = [line]
        else:
            lines.append(line)

    flush()
    return blocks


def diff_configs(old_text: str, new_text: str) -> str:
    """
    Block-aware diff: compares config by structural section (interface,
    router ospf, access-list, etc.) instead of raw line order. Blocks that
    were only reordered (no real content change) produce no diff. Blocks
    that were added, removed, or actually modified each get their own
    unified-diff section.

    Known limitation: this parser assumes Cisco/FRR-style syntax (indented
    children, '!'-delimited blocks). A device with a fundamentally
    different config format (e.g. Juniper's brace-delimited style) would
    need a separate parser.
    """
    old_blocks = parse_blocks(old_text)
    new_blocks = parse_blocks(new_text)

    sections = []
    for header in sorted(set(old_blocks) | set(new_blocks)):
        old_block = old_blocks.get(header, "")
        new_block = new_blocks.get(header, "")
        if old_block == new_block:
            continue
        block_diff = difflib.unified_diff(
            old_block.splitlines(),
            new_block.splitlines(),
            fromfile=f"old: {header}" if old_block else "(absent)",
            tofile=f"new: {header}" if new_block else "(removed)",
            lineterm="",
        )
        sections.append("\n".join(block_diff))

    return "\n\n".join(sections)