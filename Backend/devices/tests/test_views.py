from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from devices.models import Device, Snapshot, ConfigChange, SeverityClass


class ConfigChangeAcknowledgeTests(TestCase):

    def setUp(self):
        self.client = APIClient()

        self.device = Device.objects.create(
            name="Test-Router-3",
            hostname="test-router-3",
            management_ip="10.0.0.97",
            device_type="linux",
            username="root",
        )
        self.device.set_password("fake-password")
        self.device.save()

        self.old_snapshot = Snapshot.objects.create(
            device=self.device, raw_text="hostname r1\n!", config_hash="abc123",
        )
        self.new_snapshot = Snapshot.objects.create(
            device=self.device, raw_text="hostname r1-new\n!", config_hash="def456",
        )
        self.high, _ = SeverityClass.objects.get_or_create(name="High", rank=30)

        self.change = ConfigChange.objects.create(
            device=self.device,
            old_snapshot=self.old_snapshot,
            new_snapshot=self.new_snapshot,
            diff_text="+hostname r1-new",
            severity_class=self.high,
            status="FLAGGED",
        )

    def test_acknowledge_sets_status_and_timestamp(self):
        self.assertIsNone(self.change.acknowledged_at)  # sanity check before

        url = f"/api/changes/{self.change.id}/acknowledge/"
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.change.refresh_from_db()
        self.assertEqual(self.change.status, "ACKNOWLEDGED")
        self.assertIsNotNone(self.change.acknowledged_at)

    def test_cannot_acknowledge_nonexistent_change(self):
        response = self.client.post("/api/changes/99999/acknowledge/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class DevicePauseResumeTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.device = Device.objects.create(
            name="Test-Router-4",
            hostname="test-router-4",
            management_ip="10.0.0.96",
            device_type="linux",
            username="root",
            is_active=True,
        )
        self.device.set_password("fake-password")
        self.device.save()

    def test_pause_sets_is_active_false(self):
        response = self.client.post(f"/api/devices/{self.device.id}/pause/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.device.refresh_from_db()
        self.assertFalse(self.device.is_active)

    def test_resume_sets_is_active_true(self):
        self.device.is_active = False
        self.device.save()

        response = self.client.post(f"/api/devices/{self.device.id}/resume/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.device.refresh_from_db()
        self.assertTrue(self.device.is_active)


class SnapshotBaselineTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.device = Device.objects.create(
            name="Test-Router-5",
            hostname="test-router-5",
            management_ip="10.0.0.95",
            device_type="linux",
            username="root",
        )
        self.device.set_password("fake-password")
        self.device.save()

        self.snap1 = Snapshot.objects.create(
            device=self.device, raw_text="v1", config_hash="hash1", is_baseline=True,
        )
        self.snap2 = Snapshot.objects.create(
            device=self.device, raw_text="v2", config_hash="hash2", is_baseline=False,
        )

    def test_promoting_new_baseline_demotes_old_one(self):
        url = f"/api/snapshots/{self.snap2.id}/set_baseline/"
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.snap1.refresh_from_db()
        self.snap2.refresh_from_db()

        # Exactly one baseline must exist, and it must be the new one
        self.assertFalse(self.snap1.is_baseline)
        self.assertTrue(self.snap2.is_baseline)

from unittest.mock import patch


class CheckNowTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.device = Device.objects.create(
            name="Test-Router-6",
            hostname="test-router-6",
            management_ip="10.0.0.94",
            device_type="linux",
            username="root",
        )
        self.device.set_password("fake-password")
        self.device.save()

    @patch("devices.views.pull_config_task.delay")
    def test_check_now_queues_correct_device_and_returns_202(self, mock_delay):
        response = self.client.post(f"/api/devices/{self.device.id}/check_now/")

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data["status"], "queued")
        mock_delay.assert_called_once_with(str(self.device.id))

class DeviceDuplicateTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.existing = Device.objects.create(
            name="Duplicate-Test-Router",
            hostname="duplicate-test.local",
            management_ip="10.0.0.93",
            device_type="linux",
            username="root",
        )
        self.existing.set_password("fake-password")
        self.existing.save()

    def test_duplicate_name_returns_400_not_500(self):
        response = self.client.post("/api/devices/", {
            "name": "Duplicate-Test-Router",  # same name
            "hostname": "different-hostname.local",
            "management_ip": "10.0.0.92",
            "port": 22,
            "device_type": "linux",
            "username": "root",
            "password": "somepassword",
            "poll_interval_minutes": 30,
        })
        self.assertEqual(response.status_code, 400)

def test_duplicate_hostname_returns_400_not_500(self):
        response = self.client.post("/api/devices/", {
            "name": "Different-Name-Router",
            "hostname": "duplicate-test.local",  # same hostname as self.existing
            "management_ip": "10.0.0.92",
            "port": 22,
            "device_type": "linux",
            "username": "root",
            "password": "somepassword",
            "poll_interval_minutes": 30,
        })
        self.assertEqual(response.status_code, 400)

def test_duplicate_management_ip_returns_400_not_500(self):
        response = self.client.post("/api/devices/", {
            "name": "Another-Different-Router",
            "hostname": "another-different.local",
            "management_ip": "10.0.0.93",  # same IP as self.existing
            "port": 22,
            "device_type": "linux",
            "username": "root",
            "password": "somepassword",
            "poll_interval_minutes": 30,
        })
        self.assertEqual(response.status_code, 400)