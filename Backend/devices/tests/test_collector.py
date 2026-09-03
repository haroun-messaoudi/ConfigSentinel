from django.test import SimpleTestCase
from devices.collector import parse_blocks, diff_configs


class ParseBlocksTests(SimpleTestCase):
    """
    SimpleTestCase instead of TestCase: this logic never touches the
    database, so we use the lighter base class — it skips Django's
    per-test database setup/teardown, making these tests run faster.
    """

    def test_ignores_vtysh_preamble_and_postamble(self):
        raw = (
            "Building configuration...\n"
            "\n"
            "Current configuration:\n"
            "!\n"
            "hostname r1\n"
            "!\n"
            "end"
        )
        blocks = parse_blocks(raw)

        # The preamble/postamble lines must NOT show up as blocks
        self.assertNotIn("Building configuration...", blocks)
        self.assertNotIn("Current configuration:", blocks)
        self.assertNotIn("end", blocks)

        # But the real config line must be captured
        self.assertIn("hostname r1", blocks)

    def test_blank_lines_do_not_split_a_block(self):
        raw = (
            "banner motd\n"
            "  Welcome\n"
            "\n"
            "  Authorized access only\n"
            "!"
        )
        blocks = parse_blocks(raw)

        self.assertIn("banner motd", blocks)
        # The blank line must NOT have cut the banner into two blocks
        self.assertIn("Welcome", blocks["banner motd"])
        self.assertIn("Authorized access only", blocks["banner motd"])

    def test_interface_block_captures_its_children(self):
        raw = (
            "interface eth0\n"
            "  ip address 10.0.0.1/24\n"
            "  no shutdown\n"
            "!"
        )
        blocks = parse_blocks(raw)

        self.assertIn("interface eth0", blocks)
        self.assertIn("ip address 10.0.0.1/24", blocks["interface eth0"])
        self.assertIn("no shutdown", blocks["interface eth0"])


class DiffConfigsTests(SimpleTestCase):

    def test_no_diff_when_configs_are_identical(self):
        config = "hostname r1\n!\nno ipv6 forwarding\n!"
        result = diff_configs(config, config)
        self.assertEqual(result, "")

    def test_reordered_blocks_produce_no_diff(self):
        old = "interface eth0\n  no shutdown\n!\ninterface eth1\n  no shutdown\n!"
        new = "interface eth1\n  no shutdown\n!\ninterface eth0\n  no shutdown\n!"
        result = diff_configs(old, new)
        # Same blocks, just reordered — this is the exact false-positive
        # we fixed yesterday. Must be empty.
        self.assertEqual(result, "")

    def test_actual_content_change_is_detected(self):
        old = "access-list 10 permit 192.168.1.0/24\n!"
        new = "access-list 10 permit 192.168.2.0/24\n!"
        result = diff_configs(old, new)
        self.assertNotEqual(result, "")
        self.assertIn("192.168.2.0/24", result)