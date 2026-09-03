from django.test import TestCase
from devices.serializers import DeviceSerializer
from devices.models import Device


class DeviceSerializerValidationTests(TestCase):

    def valid_payload(self, **overrides):
        payload = {
            "name": "Router-Test",
            "hostname": "router-test.local",
            "management_ip": "10.0.0.50",
            "port": 22,
            "device_type": "linux",
            "username": "root",
            "password": "somepassword",
            "poll_interval_minutes": 30,
        }
        payload.update(overrides)
        return payload

    def test_valid_payload_is_accepted(self):
        serializer = DeviceSerializer(data=self.valid_payload())
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_name_too_short_is_rejected(self):
        serializer = DeviceSerializer(data=self.valid_payload(name="ab"))
        self.assertFalse(serializer.is_valid())
        self.assertIn("name", serializer.errors)

    def test_unsupported_device_type_is_rejected(self):
        serializer = DeviceSerializer(data=self.valid_payload(device_type="cisco_ios_xr"))
        self.assertFalse(serializer.is_valid())
        self.assertIn("device_type", serializer.errors)

    def test_port_out_of_range_is_rejected(self):
        serializer = DeviceSerializer(data=self.valid_payload(port=70000))
        self.assertFalse(serializer.is_valid())
        self.assertIn("port", serializer.errors)

    def test_invalid_hostname_is_rejected(self):
        serializer = DeviceSerializer(data=self.valid_payload(hostname="not valid!!"))
        self.assertFalse(serializer.is_valid())
        self.assertIn("hostname", serializer.errors)

    def test_password_is_encrypted_on_save_not_stored_plaintext(self):
        serializer = DeviceSerializer(data=self.valid_payload(password="supersecret123"))
        self.assertTrue(serializer.is_valid(), serializer.errors)
        device = serializer.save()

        # The raw DB field must NOT contain the plaintext password
        self.assertNotEqual(device.password, "supersecret123")
        # But decrypting it must give back the original
        self.assertEqual(device.get_password(), "supersecret123")

    def test_password_is_write_only_never_returned(self):
        serializer = DeviceSerializer(data=self.valid_payload())
        serializer.is_valid()
        serializer.save()

        # Serializing back out must never expose the password field
        self.assertNotIn("password", serializer.data)

from devices.serializers import DeviceSerializer, TrackedConceptSerializer
from devices.models import Device, SeverityClass, TrackedConcept


class TrackedConceptSerializerTests(TestCase):

    def setUp(self):
        self.high, _ = SeverityClass.objects.get_or_create(name="High", rank=30)

        self.builtin_concept = TrackedConcept.objects.create(
            name="Builtin Test Concept",
            pattern=r"access-list",
            severity_class=self.high,
            source="BUILTIN",
        )
        self.custom_concept = TrackedConcept.objects.create(
            name="Custom Test Concept",
            pattern=r"vlan",
            severity_class=self.high,
            source="CUSTOM",
        )

    def test_editing_a_builtin_concept_is_rejected(self):
        serializer = TrackedConceptSerializer(
            self.builtin_concept,
            data={"name": "Renamed", "pattern": "changed", "severity_class": self.high.id},
        )
        self.assertFalse(serializer.is_valid())

    def test_editing_a_custom_concept_is_accepted(self):
        serializer = TrackedConceptSerializer(
            self.custom_concept,
            data={"name": "Renamed Custom", "pattern": "vlan|vtp", "severity_class": self.high.id},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_creating_a_new_concept_is_unaffected_by_builtin_check(self):
        # self.instance is None on create — the BUILTIN check must not
        # accidentally block brand new concepts.
        serializer = TrackedConceptSerializer(
            data={"name": "New Concept", "pattern": "ospf", "severity_class": self.high.id}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
class DeviceSerializerUpdateTests(TestCase):

    def setUp(self):
        self.device = Device.objects.create(
            name="Update-Test-Router",
            hostname="update-test.local",
            management_ip="10.0.0.60",
            device_type="linux",
            username="root",
        )
        self.device.set_password("original-password")
        self.device.save()

    def test_update_without_password_keeps_existing_password(self):
        serializer = DeviceSerializer(
            self.device,
            data={"poll_interval_minutes": 45},
            partial=True,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated_device = serializer.save()

        self.assertEqual(updated_device.get_password(), "original-password")
        self.assertEqual(updated_device.poll_interval_minutes, 45)

    def test_update_with_new_password_replaces_it(self):
        serializer = DeviceSerializer(
            self.device,
            data={"password": "new-password"},
            partial=True,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated_device = serializer.save()

        self.assertEqual(updated_device.get_password(), "new-password")
