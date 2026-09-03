from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from users.models import User, Role
from devices.models import Device


class DevicePermissionTests(TestCase):

    def setUp(self):
        self.admin_role = Role.objects.get(name="Admin")
        self.operator_role = Role.objects.get(name="Operator")
        self.viewer_role = Role.objects.get(name="Viewer")

        self.admin = User.objects.create_user(username="admin1", password="pass", role=self.admin_role)
        self.operator = User.objects.create_user(username="operator1", password="pass", role=self.operator_role)
        self.viewer = User.objects.create_user(username="viewer1", password="pass", role=self.viewer_role)

        self.device = Device.objects.create(
            name="Perm-Test-Router", hostname="perm-test-router",
            management_ip="10.0.0.80", device_type="linux", username="root",
        )
        self.device.set_password("fake-password")
        self.device.save()

    def auth_client(self, user):
        client = APIClient()
        token = RefreshToken.for_user(user).access_token
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return client

    def valid_device_payload(self):
        return {
            "name": "New-Router", "hostname": "new-router.local",
            "management_ip": "10.0.0.81", "port": 22,
            "device_type": "linux", "username": "root",
            "password": "somepassword", "poll_interval_minutes": 30,
        }

    # --- Viewer ---

    def test_viewer_can_list_devices(self):
        client = self.auth_client(self.viewer)
        response = client.get("/api/devices/")
        self.assertEqual(response.status_code, 200)

    def test_viewer_cannot_create_device(self):
        client = self.auth_client(self.viewer)
        response = client.post("/api/devices/", self.valid_device_payload())
        self.assertEqual(response.status_code, 403)

    def test_viewer_cannot_pause_device(self):
        client = self.auth_client(self.viewer)
        response = client.post(f"/api/devices/{self.device.id}/pause/")
        self.assertEqual(response.status_code, 403)

    # --- Operator ---

    def test_operator_can_pause_device(self):
        client = self.auth_client(self.operator)
        response = client.post(f"/api/devices/{self.device.id}/pause/")
        self.assertEqual(response.status_code, 200)

    def test_operator_cannot_create_device(self):
        client = self.auth_client(self.operator)
        response = client.post("/api/devices/", self.valid_device_payload())
        self.assertEqual(response.status_code, 403)

    def test_operator_cannot_delete_device(self):
        client = self.auth_client(self.operator)
        response = client.delete(f"/api/devices/{self.device.id}/")
        self.assertEqual(response.status_code, 403)

    # --- Admin ---

    def test_admin_can_create_device(self):
        client = self.auth_client(self.admin)
        response = client.post("/api/devices/", self.valid_device_payload())
        self.assertEqual(response.status_code, 201)

    def test_admin_can_delete_device(self):
        client = self.auth_client(self.admin)
        response = client.delete(f"/api/devices/{self.device.id}/")
        self.assertEqual(response.status_code, 204)

    # --- Unauthenticated ---

    def test_unauthenticated_request_is_rejected(self):
        client = APIClient()  # no token attached
        response = client.get("/api/devices/")
        self.assertEqual(response.status_code, 401)