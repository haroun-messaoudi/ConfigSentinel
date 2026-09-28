import re
import jinja2
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models

# Import the Device model from your separate 'devices' app
from devices.models import Device


class ActionDefinition(models.Model):
    """Defines an available network automation action (e.g., 'Add ACL Entry')."""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(get_user_model(), null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class ActionParameter(models.Model):
    """Parameters required by an ActionDefinition with type rules and optional validation."""
    DATA_TYPES = [
        ("STRING", "String"),
        ("INTEGER", "Integer"),
        ("IP_ADDRESS", "IP Address"),
        ("BOOLEAN", "Boolean"),
    ]

    action_definition = models.ForeignKey(ActionDefinition, on_delete=models.CASCADE, related_name="parameters")
    name = models.CharField(max_length=50)  # e.g., 'acl_name'
    label = models.CharField(max_length=100)  # e.g., 'ACL Name or Number'
    data_type = models.CharField(max_length=20, choices=DATA_TYPES, default="STRING")
    is_required = models.BooleanField(default=True)
    default_value = models.CharField(max_length=255, blank=True, default="")
    validation_regex = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        unique_together = ("action_definition", "name")

    def __str__(self):
        return f"{self.action_definition.name} -> {self.name}"


class ActionTemplate(models.Model):
    """Jinja2 template snippet mapped per device type for a specific ActionDefinition."""
    action_definition = models.ForeignKey(ActionDefinition, on_delete=models.CASCADE, related_name="templates")
    device_type = models.CharField(max_length=50)  # e.g., 'cisco_xe', 'linux'
    template_text = models.TextField()

    class Meta:
        unique_together = ("action_definition", "device_type")

    def __str__(self):
        return f"{self.action_definition.name} [{self.device_type}]"


class DevicePermission(models.Model):
    """Fine-grained permission map: which users can run which actions on which devices."""
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name="device_permissions")
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="allowed_permissions")
    action_definition = models.ForeignKey(ActionDefinition, on_delete=models.CASCADE, related_name="allowed_permissions")
    granted_by = models.ForeignKey(get_user_model(), null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    granted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "device", "action_definition")

    def __str__(self):
        return f"{self.user.username} -> {self.action_definition.name} on {self.device.name}"


class ChangeRequest(models.Model):
    """An immutable, audited change request submitted by a user."""
    STATUS_CHOICES = [
        ("PENDING", "Pending Execution"),
        ("SUCCESS", "Success"),
        ("FAILED", "Failed"),
    ]

    action_definition = models.ForeignKey(ActionDefinition, on_delete=models.PROTECT, related_name="change_requests")
    device = models.ForeignKey(Device, on_delete=models.PROTECT, related_name="change_requests")
    requested_by = models.ForeignKey(get_user_model(), on_delete=models.PROTECT, related_name="change_requests")

    params = models.JSONField(default=dict)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    generated_commands = models.TextField(blank=True, default="")

    requested_at = models.DateTimeField(auto_now_add=True)
    applied_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-requested_at"]

    def __str__(self):
        return f"CR #{self.id}: {self.action_definition.name} on {self.device.name} ({self.status})"

    def clean(self):
        super().clean()
        errors = {}

        # 1. Validate that a template exists for this device's type
        try:
            template_obj = ActionTemplate.objects.get(
                action_definition=self.action_definition,
                device_type=self.device.device_type
            )
        except ActionTemplate.DoesNotExist:
            errors["device"] = f"Device type '{self.device.device_type}' does not support action '{self.action_definition.name}'."
            raise ValidationError(errors)

        # 2. Validate parameters against ActionParameter constraints
        allowed_params = {p.name: p for p in self.action_definition.parameters.all()}
        provided_params = self.params or {}

        validated_params = {}
        param_error_messages = []

        for param_name, param_def in allowed_params.items():
            val = provided_params.get(param_name)

            if val is None or val == "":
                if param_def.is_required:
                    if param_def.default_value:
                        validated_params[param_name] = param_def.default_value
                    else:
                        param_error_messages.append(f"Parameter '{param_name}' is required.")
                continue

            # Reject embedded newlines/carriage returns before anything else —
            # a multi-line string value could inject extra commands beyond
            # what the template intended, once generated_commands is split
            # line-by-line and sent to the device.
            if isinstance(val, str) and ("\n" in val or "\r" in val):
                param_error_messages.append(f"Parameter '{param_name}' cannot contain line breaks.")
                continue

            # Type Validation & Conversion
            if param_def.data_type == "INTEGER":
                try:
                    val = int(val)
                except (ValueError, TypeError):
                    param_error_messages.append(f"Parameter '{param_name}' must be a valid integer.")
            elif param_def.data_type == "BOOLEAN":
                if isinstance(val, str):
                    val = val.lower() in ("true", "1", "yes")
                val = bool(val)
            elif param_def.data_type == "IP_ADDRESS":
                ip_regex = r"^(\d{1,3}\.){3}\d{1,3}$"
                if val != "any" and not re.match(ip_regex, str(val)):
                    param_error_messages.append(f"Parameter '{param_name}' must be a valid IPv4 address or 'any'.")

            # Regex Custom Pattern Validation
            if param_def.validation_regex and isinstance(val, str):
                try:
                    if not re.match(param_def.validation_regex, val):
                        param_error_messages.append(f"Parameter '{param_name}' failed pattern validation.")
                except re.error:
                    param_error_messages.append(f"Invalid regex rule configured for parameter '{param_name}'.")

            validated_params[param_name] = val

        if param_error_messages:
            errors["params"] = param_error_messages

        if errors:
            raise ValidationError(errors)

        # 3. Render Jinja2 Template safely
        try:
            template = jinja2.Template(template_obj.template_text)
            self.generated_commands = template.render(**validated_params)
        except Exception as e:
            raise ValidationError({"params": [f"Failed to compile configuration template: {str(e)}"]})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)