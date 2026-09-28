from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from users.models import Role

from actions.models import ActionDefinition, DevicePermission
from devices.models import Alert, Device, Snapshot, ConfigChange, SeverityClass


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
        self.admin = get_user_model().objects.create_superuser(username="device_admin", password="password")
        self.operator = get_user_model().objects.create_user(
            username="device_operator",
            password="password",
            role=Role.objects.get(name="Operator"),
        )
        self.client.force_authenticate(user=self.admin)
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

    def test_operator_cannot_pause_device(self):
        self.client.force_authenticate(user=self.operator)

        response = self.client.post(f"/api/devices/{self.device.id}/pause/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.device.refresh_from_db()
        self.assertTrue(self.device.is_active)

    def test_resume_sets_is_active_true(self):
        self.device.is_active = False
        self.device.save()

        response = self.client.post(f"/api/devices/{self.device.id}/resume/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.device.refresh_from_db()
        self.assertTrue(self.device.is_active)

    def test_operator_cannot_resume_device(self):
        self.device.is_active = False
        self.device.save()
        self.client.force_authenticate(user=self.operator)

        response = self.client.post(f"/api/devices/{self.device.id}/resume/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.device.refresh_from_db()
        self.assertFalse(self.device.is_active)

    def test_operator_cannot_update_device(self):
        self.client.force_authenticate(user=self.operator)

        response = self.client.patch(
            f"/api/devices/{self.device.id}/",
            {"name": "Operator-Renamed-Device"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.device.refresh_from_db()
        self.assertEqual(self.device.name, "Test-Router-4")

    def test_admin_can_update_device(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(
            f"/api/devices/{self.device.id}/",
            {"name": "Admin-Renamed-Device"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.device.refresh_from_db()
        self.assertEqual(self.device.name, "Admin-Renamed-Device")


class OperatorDeviceReadScopeTests(TestCase):

    def setUp(self):
        self.operator = get_user_model().objects.create_user(
            username="scoped_operator",
            password="password",
            role=Role.objects.get(name="Operator"),
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.operator)
        self.action = ActionDefinition.objects.create(name="Scoped Test Action")
        self.assigned_device = self.create_device("Assigned-Router", "10.0.0.111")
        self.other_device = self.create_device("Other-Router", "10.0.0.112")
        DevicePermission.objects.create(
            user=self.operator,
            device=self.assigned_device,
            action_definition=self.action,
        )
        self.severity, _ = SeverityClass.objects.get_or_create(name="Scope Test", rank=87)
        self.assigned_change = self.create_change(self.assigned_device, "assigned")
        self.other_change = self.create_change(self.other_device, "other")
        self.assigned_alert = Alert.objects.create(change=self.assigned_change)
        self.other_alert = Alert.objects.create(change=self.other_change)

    def create_device(self, name, address):
        return Device.objects.create(
            name=name,
            hostname=f"{name.lower()}.local",
            management_ip=address,
            device_type="linux",
            username="root",
        )

    def create_change(self, device, suffix):
        old_snapshot = Snapshot.objects.create(
            device=device,
            raw_text=f"hostname {suffix}",
            config_hash=f"{suffix}-old",
        )
        new_snapshot = Snapshot.objects.create(
            device=device,
            raw_text=f"hostname {suffix}-updated",
            config_hash=f"{suffix}-new",
        )
        return ConfigChange.objects.create(
            device=device,
            old_snapshot=old_snapshot,
            new_snapshot=new_snapshot,
            diff_text=f"+hostname {suffix}-updated",
            severity_class=self.severity,
            status="FLAGGED",
        )

    @staticmethod
    def response_rows(response):
        data = response.data
        return data["results"] if isinstance(data, dict) and "results" in data else data

    @patch("devices.views.pull_config_task.delay")
    def test_operator_device_list_and_check_now_are_scoped(self, mock_delay):
        response = self.client.get("/api/devices/")
        self.assertEqual([row["id"] for row in self.response_rows(response)], [self.assigned_device.id])

        response = self.client.get(f"/api/devices/{self.other_device.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        response = self.client.post(f"/api/devices/{self.other_device.id}/check_now/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        mock_delay.assert_not_called()

    def test_operator_snapshot_list_and_detail_are_scoped(self):
        response = self.client.get("/api/snapshots/")
        rows = self.response_rows(response)
        self.assertTrue(rows)
        self.assertEqual({row["device"] for row in rows}, {self.assigned_device.id})

        other_snapshot = self.other_change.old_snapshot
        response = self.client.get(f"/api/snapshots/{other_snapshot.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        response = self.client.get(f"/api/devices/{self.other_device.id}/snapshots/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_operator_changes_and_alerts_are_scoped(self):
        response = self.client.get("/api/changes/")
        rows = self.response_rows(response)
        self.assertEqual({row["device"] for row in rows}, {self.assigned_device.id})

        response = self.client.get(f"/api/changes/{self.other_change.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        response = self.client.get(f"/api/devices/{self.other_device.id}/changes/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        response = self.client.get("/api/alerts/")
        rows = self.response_rows(response)
        self.assertEqual([row["id"] for row in rows], [self.assigned_alert.id])


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
        operator = get_user_model().objects.create_user(
            username="check_operator",
            password="password",
            role=Role.objects.get(name="Operator"),
        )
        self.client.force_authenticate(user=operator)
        self.device = Device.objects.create(
            name="Test-Router-6",
            hostname="test-router-6",
            management_ip="10.0.0.94",
            device_type="linux",
            username="root",
        )
        self.device.set_password("fake-password")
        self.device.save()
        action = ActionDefinition.objects.create(name="Check Now Scope Test")
        DevicePermission.objects.create(
            user=operator,
            device=self.device,
            action_definition=action,
        )

    @patch("devices.views.pull_config_task.delay")
    def test_check_now_queues_correct_device_and_returns_202(self, mock_delay):
        response = self.client.post(f"/api/devices/{self.device.id}/check_now/")

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data["status"], "queued")
        mock_delay.assert_called_once_with(self.device.pk)

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