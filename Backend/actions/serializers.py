from rest_framework import serializers
from django.db import transaction
from .models import (
    ActionDefinition,
    ActionParameter,
    ActionTemplate,
    DevicePermission,
    ChangeRequest,
)


class ActionParameterSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActionParameter
        fields = [
            "id", "name", "label", "data_type",
            "is_required", "default_value", "validation_regex"
        ]


class ActionTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActionTemplate
        fields = ["id", "device_type", "template_text"]


class ActionDefinitionSerializer(serializers.ModelSerializer):
    parameters = ActionParameterSerializer(many=True, required=False)
    templates = ActionTemplateSerializer(many=True, required=False)

    class Meta:
        model = ActionDefinition
        fields = [
            "id", "name", "description", "created_by",
            "created_at", "parameters", "templates"
        ]
        read_only_fields = ["created_by", "created_at"]

    def create(self, validated_data):
        parameters_data = validated_data.pop("parameters", [])
        templates_data = validated_data.pop("templates", [])

        with transaction.atomic():
            # 1. Create the base Action Definition
            action_definition = ActionDefinition.objects.create(**validated_data)

            # 2. Create the Parameters
            for param in parameters_data:
                ActionParameter.objects.create(action_definition=action_definition, **param)

            # 3. Create the Action Templates
            for tmpl in templates_data:
                ActionTemplate.objects.create(action_definition=action_definition, **tmpl)

        return action_definition


class DevicePermissionSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source="user.username", read_only=True)
    device_name = serializers.CharField(source="device.name", read_only=True)
    action_name = serializers.CharField(source="action_definition.name", read_only=True)

    class Meta:
        model = DevicePermission
        fields = [
            "id", "user", "user_username", "device",
            "device_name", "action_definition", "action_name",
            "granted_by", "granted_at"
        ]
        read_only_fields = ["granted_by", "granted_at"]


class ChangeRequestSerializer(serializers.ModelSerializer):
    action_name = serializers.CharField(source="action_definition.name", read_only=True)
    device_name = serializers.CharField(source="device.name", read_only=True)
    requested_by_username = serializers.CharField(source="requested_by.username", read_only=True)

    class Meta:
        model = ChangeRequest
        fields = [
            "id", "action_definition", "action_name", "device", "device_name",
            "requested_by", "requested_by_username", "params", "status",
            "generated_commands", "requested_at", "applied_at", "error_message"
        ]
        read_only_fields = [
            "id", "requested_by", "status", "generated_commands",
            "requested_at", "applied_at", "error_message"
        ]