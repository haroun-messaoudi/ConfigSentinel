# devices/migrations/0009_fix_concept_patterns.py
from django.db import migrations

# (name, new_pattern) — only concepts whose regex had a real bug or
# blind spot are listed here; everything else in 0008 is left untouched.
PATTERN_FIXES = [
    (
        "Routing Protocol Disabled",
        r"^-router (ospf|bgp|eigrp|rip)\b",
        # Old pattern searched for literal "no router X" — but
        # show running-config never contains the command that was
        # typed, only the resulting state. Disabling a protocol makes
        # its whole block disappear, which shows up as a removed line
        # ("-router ospf 1") in the unified diff — that's what this
        # matches instead.
    ),
    (
        "Interface Shutdown",
        r"^\+\s*shutdown\s*$",
        # Old pattern (`^\+.*\bshutdown\b`) could also match an added
        # "no shutdown" line (word boundary doesn't see the "no"
        # prefix), which would misreport an interface being brought UP
        # as being shut down. High-severity concept, so a tight match
        # matters more here than most.
    ),
    (
        "VLAN Change",
        r"\bvlan \d+\b|encapsulation dot1[qQ] \d+|switchport (access vlan|trunk (native|allowed) vlan) \d+",
        # Old pattern only caught classic VLAN database / switchport
        # syntax. Router-on-a-stick subinterface trunking
        # ("encapsulation dot1Q 200") is a different, common way VLAN
        # config appears on routers and was previously invisible.
    ),
    (
        "OSPF Area Change",
        r"network \S+ \S+ area \d+",
        # Old pattern's "router ospf" alternative made this fire on
        # ANY OSPF-related diff (e.g. the protocol being newly
        # enabled), not specifically an area reassignment — which
        # defeats the point of having this as a distinct concept from
        # "Routing Protocol Disabled"/enabled.
    ),
    (
        "Static Route Change",
        r"ip route|ipv6 route",
        # Old pattern was IPv4-only; IPv6 static routes use a
        # completely separate keyword and were silently missed.
    ),
    (
        "Interface IP Change",
        r"ip address \d+\.\d+\.\d+\.\d+|ipv6 address \S+",
        # Same IPv4-only blind spot as Static Route Change.
    ),
    (
        "HSRP Change",
        r"standby \d+ (priority|ip|preempt|track|authentication)",
        # Added track/authentication — legitimate HSRP config changes
        # that weren't covered by the original keyword set.
    ),
]


def fix_patterns(apps, schema_editor):
    TrackedConcept = apps.get_model("devices", "TrackedConcept")
    for name, new_pattern in PATTERN_FIXES:
        TrackedConcept.objects.filter(name=name, source="BUILTIN").update(pattern=new_pattern)


def reverse_fix(apps, schema_editor):
    # Restore the exact old patterns from 0008 so `migrate devices 0008`
    # leaves the DB byte-for-byte where that migration left it.
    TrackedConcept = apps.get_model("devices", "TrackedConcept")
    old_patterns = {
        "Routing Protocol Disabled": r"no router (ospf|bgp|eigrp|rip)",
        "Interface Shutdown": r"^\+.*\bshutdown\b",
        "VLAN Change": r"vlan \d+",
        "OSPF Area Change": r"router ospf|network .* area",
        "Static Route Change": r"ip route",
        "Interface IP Change": r"ip address \d+\.\d+\.\d+\.\d+",
        "HSRP Change": r"standby \d+ (priority|ip|preempt)",
    }
    for name, old_pattern in old_patterns.items():
        TrackedConcept.objects.filter(name=name, source="BUILTIN").update(pattern=old_pattern)


class Migration(migrations.Migration):

    dependencies = [
    ("devices", "0011_device_consecutive_failures"),
    ]

    operations = [
        migrations.RunPython(fix_patterns, reverse_fix),
    ]