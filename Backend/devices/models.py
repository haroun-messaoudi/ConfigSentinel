from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth import get_user_model
from cryptography.fernet import Fernet
from django.conf import settings
from django.db import models

POLL_STATUS_CHOICES = [
    ("OK", "OK"),
    ("ERROR", "Error"),
]


class SeverityClass(models.Model):
    """Admin-defined severity tier. Higher rank = more severe."""
    name = models.CharField(max_length=50, unique=True)
    rank = models.IntegerField(unique=True)

    class Meta:
        ordering = ["-rank"]

    def __str__(self):
        return self.name


class TrackedConcept(models.Model):
    """One detectable pattern in a config diff (e.g. 'ACL Change', 'HSRP Change')."""
    SOURCE_CHOICES = [
        ("BUILTIN", "Built-in"),
        ("CUSTOM", "Custom"),
    ]

    name = models.CharField(max_length=100)
    description = models.CharField(max_length=255, blank=True)
    pattern = models.CharField(max_length=255)
    severity_class = models.ForeignKey(SeverityClass, on_delete=models.PROTECT, related_name="concepts")
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default="CUSTOM")
    created_by = models.ForeignKey(get_user_model(), null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return self.name


class DetectionProfile(models.Model):
    """A named, reusable set of tracked concepts — assign the same profile to many devices."""
    name = models.CharField(max_length=100, unique=True)
    tracked_concepts = models.ManyToManyField(TrackedConcept, related_name="profiles", blank=True)

    def __str__(self):
        return self.name


class Device(models.Model):
    """A network device being watched. One row per router/switch."""

    name = models.CharField(max_length=100, unique=True)
    hostname = models.CharField(max_length=255, unique=True)
    management_ip = models.GenericIPAddressField(protocol="IPv4", unique=True)
    port = models.IntegerField(
        default=22,
        validators=[MinValueValidator(1), MaxValueValidator(65535)],
    )
    device_type = models.CharField(max_length=50)
    username = models.CharField(max_length=100)
    password = models.CharField(max_length=200)
    enable_secret = models.CharField(max_length=200, blank=True, default="")
    poll_interval_minutes = models.IntegerField(default=30, validators=[MinValueValidator(1)])
    detection_profile = models.ForeignKey(DetectionProfile, null=True, blank=True, on_delete=models.SET_NULL, related_name="devices")
    is_active = models.BooleanField(default=True)

    last_poll_status = models.CharField(max_length=10, choices=POLL_STATUS_CHOICES, null=True, blank=True)
    last_poll_error = models.TextField(blank=True, default="")
    last_polled_at = models.DateTimeField(null=True, blank=True)
    last_poll_duration_ms = models.PositiveIntegerField(null=True, blank=True)

    consecutive_failures = models.PositiveIntegerField(default=0)

    
    def __str__(self):
        return self.name

    
    def set_password(self, raw_password):
        cipher = Fernet(settings.FERNET_KEY.encode())
        self.password = cipher.encrypt(raw_password.encode()).decode()

    def get_password(self):
        cipher = Fernet(settings.FERNET_KEY.encode())
        return cipher.decrypt(self.password.encode()).decode()

    def set_enable_secret(self, raw_secret):
        if not raw_secret:
            self.enable_secret = ""
            return
        cipher = Fernet(settings.FERNET_KEY.encode())
        self.enable_secret = cipher.encrypt(raw_secret.encode()).decode()

    def get_enable_secret(self):
        if not self.enable_secret:
            return None
        cipher = Fernet(settings.FERNET_KEY.encode())
        return cipher.decrypt(self.enable_secret.encode()).decode()


class Snapshot(models.Model):
    """One point-in-time capture of a device's configuration."""

    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="snapshots")
    taken_at = models.DateTimeField(auto_now_add=True)
    raw_text = models.TextField()
    config_hash = models.CharField(max_length=64)
    is_baseline = models.BooleanField(default=False)

    def promote_to_baseline(self):
        Snapshot.objects.filter(device=self.device, is_baseline=True).update(is_baseline=False)
        self.is_baseline = True
        self.save(update_fields=["is_baseline"])

    class Meta:
        ordering = ["-taken_at"]


class ConfigChange(models.Model):
    STATUS_CHOICES = [
        ("FLAGGED", "Flagged"),
        ("ACKNOWLEDGED", "Acknowledged"),
        ("INFORMATIONAL", "Informational"),
    ]

    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="changes")
    old_snapshot = models.ForeignKey(Snapshot, on_delete=models.CASCADE, related_name="+")
    new_snapshot = models.ForeignKey(Snapshot, on_delete=models.CASCADE, related_name="+")
    diff_text = models.TextField()
    severity_class = models.ForeignKey(SeverityClass, null=True, on_delete=models.SET_NULL, related_name="changes")
    matched_concepts = models.ManyToManyField(TrackedConcept, blank=True, related_name="matched_changes")
    detected_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="FLAGGED")
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    acknowledged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="acknowledged_changes",
    )
    class Meta:
        ordering = ["-detected_at"]

class Alert(models.Model):
    """Notification generated when a change exceeds the configured threshold."""

    change = models.ForeignKey(ConfigChange, on_delete=models.CASCADE, related_name="alerts")
    created_at = models.DateTimeField(auto_now_add=True)
    delivered = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]