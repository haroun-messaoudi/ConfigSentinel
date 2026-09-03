from unittest.mock import patch
from django.test import TestCase
from django.utils import timezone

from devices.models import Device, Snapshot, ConfigChange, Alert, SeverityClass, TrackedConcept, DetectionProfile
from devices.tasks import pull_config_task


class PullConfigTaskTests(TestCase):

    def setUp(self):
        self.high, _ = SeverityClass.objects.get_or_create(name="High", rank=30)

        self.acl_concept = TrackedConcept.objects.create(
            name="ACL Change Test",
            pattern=r"access-list",
            severity_class=self.high,
            source="CUSTOM",
        )
        self.profile = DetectionProfile.objects.create(name="Task Test Profile")
        self.profile.tracked_concepts.set([self.acl_concept])

        self.device = Device.objects.create(
            name="Test-Router",
            hostname="test-router",
            management_ip="10.0.0.99",
            device_type="linux",
            username="root",
            detection_profile=self.profile,
        )
        self.device.set_password("fake-password")
        self.device.save()

    @patch("devices.tasks.pull_config")
    def test_first_poll_creates_baseline_snapshot_only(self, mock_pull_config):
        mock_pull_config.return_value = "hostname r1\n!"

        pull_config_task(self.device.id)

        snapshots = Snapshot.objects.filter(device=self.device)
        self.assertEqual(snapshots.count(), 1)
        self.assertTrue(snapshots.first().is_baseline)
        # First poll ever — nothing to diff against, so no ConfigChange yet
        self.assertEqual(ConfigChange.objects.filter(device=self.device).count(), 0)

    @patch("devices.tasks.pull_config")
    def test_identical_second_poll_creates_no_new_snapshot(self, mock_pull_config):
        mock_pull_config.return_value = "hostname r1\n!"
        pull_config_task(self.device.id)   # first poll — creates baseline

        mock_pull_config.return_value = "hostname r1\n!"  # unchanged
        pull_config_task(self.device.id)   # second poll — same config

        # Config hash matched — task should bail out before creating a duplicate
        self.assertEqual(Snapshot.objects.filter(device=self.device).count(), 1)

    @patch("devices.tasks.pull_config")
    def test_real_change_creates_snapshot_change_and_alert(self, mock_pull_config):
        mock_pull_config.return_value = "hostname r1\n!"
        pull_config_task(self.device.id)   # baseline

        mock_pull_config.return_value = "hostname r1\n!\naccess-list 10 permit any\n!"
        pull_config_task(self.device.id)   # real change this time

        self.assertEqual(Snapshot.objects.filter(device=self.device).count(), 2)

        change = ConfigChange.objects.get(device=self.device)
        self.assertEqual(change.status, "FLAGGED")
        self.assertEqual(change.severity_class, self.high)
        self.assertIn(self.acl_concept, change.matched_concepts.all())

        self.assertEqual(Alert.objects.filter(change=change).count(), 1)

    @patch("devices.tasks.pull_config")
    def test_updates_device_poll_status_on_success(self, mock_pull_config):
        mock_pull_config.return_value = "hostname r1\n!"

        pull_config_task(self.device.id)

        self.device.refresh_from_db()
        self.assertEqual(self.device.last_poll_status, "OK")
        self.assertEqual(self.device.last_poll_error, "")
        self.assertIsNotNone(self.device.last_polled_at)

from netmiko import NetmikoAuthenticationException, NetmikoTimeoutException


class PullConfigTaskFailureTests(TestCase):

    def setUp(self):
        self.device = Device.objects.create(
            name="Test-Router-2",
            hostname="test-router-2",
            management_ip="10.0.0.98",
            device_type="linux",
            username="root",
        )
        self.device.set_password("fake-password")
        self.device.save()

    @patch("devices.tasks.pull_config")
    def test_auth_failure_marks_device_error_with_correct_message(self, mock_pull_config):
        mock_pull_config.side_effect = NetmikoAuthenticationException("bad creds")

        pull_config_task(self.device.id)

        self.device.refresh_from_db()
        self.assertEqual(self.device.last_poll_status, "ERROR")
        self.assertIn("Authentication failed", self.device.last_poll_error)
        # A failed poll must NOT create a snapshot
        self.assertEqual(Snapshot.objects.filter(device=self.device).count(), 0)

    @patch("devices.tasks.pull_config")
    def test_timeout_marks_device_error_with_correct_message(self, mock_pull_config):
        mock_pull_config.side_effect = NetmikoTimeoutException("no response")

        pull_config_task(self.device.id)

        self.device.refresh_from_db()
        self.assertEqual(self.device.last_poll_status, "ERROR")
        self.assertIn("timed out", self.device.last_poll_error)
        self.assertEqual(Snapshot.objects.filter(device=self.device).count(), 0)

    @patch("devices.tasks.pull_config")
    def test_unexpected_exception_is_caught_not_raised(self, mock_pull_config):
        mock_pull_config.side_effect = ValueError("something weird")

        # This must NOT raise — pull_config_task's generic except block
        # should catch it and record the error, not crash the worker.
        pull_config_task(self.device.id)

        self.device.refresh_from_db()
        self.assertEqual(self.device.last_poll_status, "ERROR")
        self.assertIn("Unexpected error", self.device.last_poll_error)


@patch("devices.tasks.pull_config")
def test_change_matching_no_concept_is_informational(self, mock_pull_config):
    mock_pull_config.return_value = "hostname r1\n!"
    pull_config_task(self.device.id)   # baseline

    # This change doesn't match "ACL Change Test" (the only concept in
    # the profile from setUp) — nothing relevant to the admin's profile.
    mock_pull_config.return_value = "hostname r1\n!\ndescription updated\n!"
    pull_config_task(self.device.id)

    change = ConfigChange.objects.get(device=self.device)
    self.assertEqual(change.status, "INFORMATIONAL")
    self.assertIsNone(change.severity_class)
    # Below/no match — must NOT create an Alert
    self.assertEqual(Alert.objects.filter(change=change).count(), 0)

from devices.tasks import poll_due_devices


class PollDueDevicesTests(TestCase):

    def setUp(self):
        self.active_device = Device.objects.create(
            name="Active-Router", hostname="active-router",
            management_ip="10.0.0.90", device_type="linux",
            username="root", is_active=True, poll_interval_minutes=30,
        )
        self.active_device.set_password("fake-password")
        self.active_device.save()

        self.paused_device = Device.objects.create(
            name="Paused-Router", hostname="paused-router",
            management_ip="10.0.0.91", device_type="linux",
            username="root", is_active=False, poll_interval_minutes=30,
        )
        self.paused_device.set_password("fake-password")
        self.paused_device.save()

    @patch("devices.tasks.pull_config_task.delay")
    def test_paused_device_is_never_queued(self, mock_delay):
        poll_due_devices()

        queued_ids = [call.args[0] for call in mock_delay.call_args_list]
        self.assertNotIn(self.paused_device.id, queued_ids)

    @patch("devices.tasks.pull_config_task.delay")
    def test_active_due_device_is_queued(self, mock_delay):
        # last_polled_at is None — brand new device, so it's immediately "due"
        poll_due_devices()

        queued_ids = [call.args[0] for call in mock_delay.call_args_list]
        self.assertIn(self.active_device.id, queued_ids)

    @patch("devices.tasks.pull_config_task.delay")
    def test_active_device_not_yet_due_is_skipped(self, mock_delay):
        self.active_device.last_polled_at = timezone.now()  # just polled seconds ago
        self.active_device.save()

        poll_due_devices()

        queued_ids = [call.args[0] for call in mock_delay.call_args_list]
        self.assertNotIn(self.active_device.id, queued_ids)

@patch("devices.tasks.pull_config")
def test_device_with_no_profile_still_polls_and_saves_history(self, mock_pull_config):
        no_profile_device = Device.objects.create(
            name="No-Profile-Router",
            hostname="no-profile-router",
            management_ip="10.0.0.89",
            device_type="linux",
            username="root",
            detection_profile=None,  # explicit — this is the case we're testing
        )
        no_profile_device.set_password("fake-password")
        no_profile_device.save()

        mock_pull_config.return_value = "hostname r1\n!"
        pull_config_task(no_profile_device.id)   # baseline

        mock_pull_config.return_value = "hostname r1\n!\naccess-list 10 permit any\n!"
        pull_config_task(no_profile_device.id)   # real change, but no profile to check it against

        # The poll itself must succeed regardless of missing profile
        no_profile_device.refresh_from_db()
        self.assertEqual(no_profile_device.last_poll_status, "OK")

        # History must still be recorded — this is the actual requirement
        self.assertEqual(Snapshot.objects.filter(device=no_profile_device).count(), 2)

        change = ConfigChange.objects.get(device=no_profile_device)
        self.assertEqual(change.status, "INFORMATIONAL")
        self.assertIsNone(change.severity_class)
        self.assertEqual(change.matched_concepts.count(), 0)

        # No profile means nothing can be flagged as dangerous — correctly no Alert
        self.assertEqual(Alert.objects.filter(change=change).count(), 0)