from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from unittest.mock import patch
from netmiko.exceptions import ConfigInvalidException

from devices.models import Device
from actions.models import ActionDefinition, ActionParameter, ActionTemplate, ChangeRequest, DevicePermission

User = get_user_model()


class ActionsEngineUnitTests(TestCase):

    def setUp(self):
        # Create users
        self.admin_user = User.objects.create_superuser(username="admin", password="password")
        self.engineer = User.objects.create_user(username="net_eng", password="password")

        # Create a supported router (Cisco XE)
        self.router = Device.objects.create(
            name="Router-Core-01",
            hostname="router01.net.local",
            management_ip="10.0.0.1",
            device_type="cisco_xe",
            username="admin",
        )
        self.router.set_password("securepassword")

        # Create an unsupported device (e.g., a switch lacking templates)
        self.switch = Device.objects.create(
            name="Switch-Access-01",
            hostname="switch01.net.local",
            management_ip="10.0.0.2",
            device_type="cisco_ios_switch",
            username="admin",
        )
        self.switch.set_password("securepassword")

        # Create a brand new, isolated test action definition
        self.action_def = ActionDefinition.objects.create(name="Test Rule Generation")

        # Define parameters required for this test action
        ActionParameter.objects.create(
            action_definition=self.action_def,
            name="rule_name",
            data_type="STRING",
            is_required=True
        )
        ActionParameter.objects.create(
            action_definition=self.action_def,
            name="vlan_id",
            data_type="INTEGER",
            is_required=False,
            default_value="10"
        )

        # Create Template ONLY for cisco_xe
        ActionTemplate.objects.create(
            action_definition=self.action_def,
            device_type="cisco_xe",
            template_text="ip access-list extended {{ rule_name }}\n permit ip any any"
        )

    def test_unsupported_device_type_blocks_execution(self):
        """Ensure actions cannot be executed on device types that lack an ActionTemplate."""
        DevicePermission.objects.create(
            user=self.engineer,
            device=self.switch,
            action_definition=self.action_def
        )

        change_req = ChangeRequest(
            action_definition=self.action_def,
            device=self.switch,
            requested_by=self.engineer,
            params={"rule_name": "TEST_RULE"}
        )

        with self.assertRaises(ValidationError) as ctx:
            change_req.full_clean()
        
        self.assertIn("device", ctx.exception.error_dict)

    def test_valid_change_request_compiles_templates(self):
        """Ensure valid parameters successfully pass validation and render Jinja2 commands."""
        DevicePermission.objects.create(
            user=self.engineer,
            device=self.router,
            action_definition=self.action_def
        )

        change_req = ChangeRequest(
            action_definition=self.action_def,
            device=self.router,
            requested_by=self.engineer,
            params={"rule_name": "SECURITY_FILTER"}
        )

        # Triggers full_clean() validation and Jinja2 rendering logic
        change_req.full_clean()
        change_req.save()

        self.assertIn("ip access-list extended SECURITY_FILTER", change_req.generated_commands)
        self.assertEqual(change_req.status, "PENDING")

    def test_parameter_type_validation_rejects_malformed_input(self):
        """Ensure strict typing rules catch invalid strings supplied to integer fields."""
        DevicePermission.objects.create(
            user=self.engineer,
            device=self.router,
            action_definition=self.action_def
        )

        change_req = ChangeRequest(
            action_definition=self.action_def,
            device=self.router,
            requested_by=self.engineer,
            params={"rule_name": "TEST", "vlan_id": "not-an-integer"}
        )

        with self.assertRaises(ValidationError) as ctx:
            change_req.full_clean()

        self.assertIn("params", ctx.exception.error_dict)


class ChangeRequestExecutionTests(TestCase):

    def setUp(self):
        self.engineer = User.objects.create_user(username="change_operator", password="password")
        self.device = Device.objects.create(
            name="Execution-Router-01",
            hostname="execution-router-01.net.local",
            management_ip="10.0.0.11",
            device_type="cisco_xe",
            username="admin",
        )
        self.device.set_password("securepassword")
        self.device.save()
        self.action = ActionDefinition.objects.create(name="Apply Test Configuration")
        ActionTemplate.objects.create(
            action_definition=self.action,
            device_type="cisco_xe",
            template_text="interface Loopback10\n description verified-change",
        )
        DevicePermission.objects.create(
            user=self.engineer,
            device=self.device,
            action_definition=self.action,
        )

    def create_request(self):
        return ChangeRequest.objects.create(
            action_definition=self.action,
            device=self.device,
            requested_by=self.engineer,
            params={},
        )

    @patch("actions.tasks.pull_config_task.delay")
    @patch("actions.tasks.ConnectHandler")
    def test_device_cli_error_is_saved_on_failed_request(self, mock_connect, _mock_pull):
        request = self.create_request()
        connection = mock_connect.return_value.__enter__.return_value
        connection.send_config_set.side_effect = ConfigInvalidException("% Invalid input detected")

        from actions.tasks import execute_change_request_task
        execute_change_request_task(request.id)

        request.refresh_from_db()
        self.assertEqual(request.status, "FAILED")
        self.assertIn("Device rejected the configuration", request.error_message)
        self.assertIn("% Invalid input detected", request.error_message)

    @patch("actions.tasks.pull_config_task.delay")
    @patch("actions.tasks.ConnectHandler")
    def test_request_stays_pending_until_readback_verification(self, mock_connect, mock_pull):
        request = self.create_request()

        from actions.tasks import execute_change_request_task
        execute_change_request_task(request.id)

        request.refresh_from_db()
        self.assertEqual(request.status, "PENDING")
        self.assertIsNone(request.applied_at)
        self.assertEqual(request.error_message, "")
        mock_connect.return_value.__enter__.return_value.send_config_set.assert_called_once()
        mock_pull.assert_called_once_with(self.device.id, triggered_by_change_request_id=request.id)

    @patch("actions.tasks.pull_config_task.delay", side_effect=RuntimeError("poll queue unavailable"))
    @patch("actions.tasks.ConnectHandler")
    def test_follow_up_poll_queue_error_fails_request_with_reason(self, mock_connect, _mock_pull):
        request = self.create_request()

        from actions.tasks import execute_change_request_task
        execute_change_request_task(request.id)

        request.refresh_from_db()
        self.assertEqual(request.status, "FAILED")
        self.assertIsNone(request.applied_at)
        self.assertIn("read-back verification could not be queued", request.error_message)
        self.assertIn("poll queue unavailable", request.error_message)


class ChangeRequestReadbackVerificationTests(TestCase):

    def setUp(self):
        self.engineer = User.objects.create_user(username="readback_operator", password="password")
        self.device = Device.objects.create(
            name="Readback-Router-01",
            hostname="readback-router-01.net.local",
            management_ip="10.0.0.12",
            device_type="cisco_xe",
            username="admin",
        )
        self.device.set_password("securepassword")
        self.device.save()
        self.action = ActionDefinition.objects.create(name="Apply Readback Configuration")
        ActionTemplate.objects.create(
            action_definition=self.action,
            device_type="cisco_xe",
            template_text="interface Loopback10\n description verified-change",
        )
        DevicePermission.objects.create(
            user=self.engineer,
            device=self.device,
            action_definition=self.action,
        )

    def create_request(self):
        return ChangeRequest.objects.create(
            action_definition=self.action,
            device=self.device,
            requested_by=self.engineer,
            params={"test_value": "readback"},
        )

    def test_matching_running_config_marks_request_successful(self):
        request = self.create_request()

        from devices.signals import change_request_poll_result
        change_request_poll_result.send(
            sender=self.__class__,
            change_request_id=request.id,
            raw_config="interface Loopback10\n description verified-change\n!\n",
        )

        request.refresh_from_db()
        self.assertEqual(request.status, "SUCCESS")
        self.assertIsNotNone(request.applied_at)
        self.assertEqual(request.error_message, "")

    def test_numbered_acl_entry_matches_requested_command(self):
        self.action.templates.filter(device_type="cisco_xe").update(
            template_text=(
                "ip access-list extended 100\n"
                " permit ip 192.168.2.0 0.0.0.255 any"
            )
        )
        request = self.create_request()

        from devices.signals import change_request_poll_result
        change_request_poll_result.send(
            sender=self.__class__,
            change_request_id=request.id,
            raw_config=(
                "ip access-list extended 100\n"
                " 20 permit ip 192.168.2.0 0.0.0.255 any\n"
                "!\n"
            ),
        )

        request.refresh_from_db()
        self.assertEqual(request.status, "SUCCESS")
        self.assertEqual(request.error_message, "")

    def test_missing_requested_config_is_saved_as_verification_failure(self):
        request = self.create_request()

        from devices.signals import change_request_poll_result
        change_request_poll_result.send(
            sender=self.__class__,
            change_request_id=request.id,
            raw_config="interface Loopback99\n description verified-change\n!\n",
        )

        request.refresh_from_db()
        self.assertEqual(request.status, "FAILED")
        self.assertIsNone(request.applied_at)
        self.assertIn("Read-back verification failed", request.error_message)
        self.assertIn("interface loopback10", request.error_message)

    def test_readback_poll_error_is_saved_on_request(self):
        request = self.create_request()

        from devices.signals import change_request_poll_result
        change_request_poll_result.send(
            sender=self.__class__,
            change_request_id=request.id,
            error_message="Connection timed out",
        )

        request.refresh_from_db()
        self.assertEqual(request.status, "FAILED")
        self.assertIn("Connection timed out", request.error_message)