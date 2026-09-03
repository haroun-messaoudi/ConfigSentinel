import re
from rest_framework import serializers
from .models import (
    Device, 
    Snapshot, 
    ConfigChange, 
    Alert, 
    TrackedConcept, 
    SeverityClass, 
    DetectionProfile
)

SUPPORTED_DEVICE_TYPES = {"linux", "cisco_xe"}  # extend as you add real device types


class DeviceSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
    enable_secret = serializers.CharField(write_only=True, required=False, allow_blank=True)

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        enable_secret = validated_data.pop("enable_secret", None)

        device = Device(**validated_data)
        if password:
            device.set_password(password)
        if enable_secret is not None:
            device.set_enable_secret(enable_secret)
        device.save()

        return device

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        enable_secret = validated_data.pop("enable_secret", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)
        if enable_secret is not None:
            instance.set_enable_secret(enable_secret)

        instance.save()

        return instance

    class Meta:
        model = Device
        fields = [
            "id", "name", "hostname", "management_ip", "port", "device_type",
            "username", "password", "enable_secret", "poll_interval_minutes",
            "detection_profile", "is_active",
            "last_poll_status", "last_poll_error", "last_polled_at",
            "consecutive_failures"
        ]
        read_only_fields = [
            "last_poll_status", "last_poll_error", "last_polled_at", "consecutive_failures"
        ]

    def validate_name(self, value):
        value = value.strip()

        if len(value) < 3:
            raise serializers.ValidationError(
                "Device name must contain at least 3 characters."
            )

        return value

    def validate_hostname(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Hostname cannot be empty."
            )

        hostname_regex = (
            r"^(?=.{1,253}$)"
            r"(?!-)"
            r"[A-Za-z0-9-]{1,63}"
            r"(?<!-)"
            r"(\.[A-Za-z0-9-]{1,63})*$"
        )

        if not re.match(hostname_regex, value):
            raise serializers.ValidationError(
                "Enter a valid hostname."
            )

        return value

    def validate_port(self, value):
        if not (1 <= value <= 65535):
            raise serializers.ValidationError(
                "Port must be between 1 and 65535."
            )

        return value

    def validate_poll_interval_minutes(self, value):
        if value < 1:
            raise serializers.ValidationError(
                "Polling interval must be at least 1 minute."
            )

        return value

    def validate_device_type(self, value):
        if value not in SUPPORTED_DEVICE_TYPES:
            raise serializers.ValidationError(
                f"Unsupported device_type '{value}'. Supported: {', '.join(sorted(SUPPORTED_DEVICE_TYPES))}."
            )

        return value


class SnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = Snapshot
        fields = ["id", "device", "taken_at", "raw_text", "config_hash", "is_baseline"]
        # Snapshots are only ever created by the Celery worker, never through
        # the API — every field here is read-only from DRF's point of view.
        read_only_fields = fields


class ConfigChangeSerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(source="device.name", read_only=True)
    severity_name = serializers.CharField(source="severity_class.name", read_only=True, default=None)
    matched_concept_names = serializers.SerializerMethodField()
    acknowledged_by_username = serializers.CharField(source="acknowledged_by.username", read_only=True, default=None)

    class Meta:
        model = ConfigChange
        fields = [
            "id", "device", "device_name", "old_snapshot", "new_snapshot",
            "diff_text", "severity_class", "severity_name",
            "matched_concepts", "matched_concept_names",
            "detected_at", "status", "acknowledged_at",
            "acknowledged_by", "acknowledged_by_username",
        ]
        read_only_fields = [
            "id", "device", "old_snapshot", "new_snapshot", "diff_text",
            "severity_class", "matched_concepts", "detected_at", "acknowledged_at",
            "acknowledged_by",
        ]

    def get_matched_concept_names(self, obj):
        return [c.name for c in obj.matched_concepts.all()]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        user = getattr(request, "user", None)
        is_admin = user and (user.is_superuser or (getattr(user, "role", None) and user.role.name == "Admin"))
        if not is_admin:
            data.pop("acknowledged_by", None)
            data.pop("acknowledged_by_username", None)
        return data


class AlertSerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(source="change.device.name", read_only=True)
    severity = serializers.CharField(source="change.severity_class.name", read_only=True)

    class Meta:
        model = Alert
        fields = ["id", "change", "device_name", "severity", "created_at", "delivered"]
        read_only_fields = ["id", "change", "created_at"]


class SeverityClassSerializer(serializers.ModelSerializer):
    class Meta:
        model = SeverityClass
        fields = ["id", "name", "rank"]


class TrackedConceptSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrackedConcept
        fields = ["id", "name", "description", "pattern", "severity_class", "source", "created_by"]
        read_only_fields = ["source", "created_by"]

    def validate(self, attrs):
        # Protect built-in concepts from being edited via API
        if self.instance and self.instance.source == "BUILTIN":
            raise serializers.ValidationError("Built-in tracked concepts cannot be modified.")
        return attrs


class DetectionProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetectionProfile
        fields = ["id", "name", "tracked_concepts"]