from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError as DRFValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from .models import (
    ActionDefinition,
    ActionTemplate,
    ActionParameter,
    DevicePermission,
    ChangeRequest,
)
from .serializers import (
    ActionDefinitionSerializer,
    ActionTemplateSerializer,
    DevicePermissionSerializer,
    ChangeRequestSerializer,
)
from .tasks import execute_change_request_task


class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(
            user and user.is_authenticated and
            (user.is_superuser or (getattr(user, "role", None) and user.role.name == "Admin"))
        )

class ActionChoicesView(APIView):
    """Single source of truth for ActionParameter.data_type choices.
    Device types are NOT duplicated here — the frontend should fetch
    those from devices/types/ instead, since SUPPORTED_DEVICE_TYPES
    already lives there."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            "data_types": [
                {"value": value, "label": label}
                for value, label in ActionParameter.DATA_TYPES
            ]
        })

class ActionDefinitionViewSet(viewsets.ModelViewSet):
    queryset = ActionDefinition.objects.prefetch_related("parameters", "templates").all()
    serializer_class = ActionDefinitionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAdmin()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class ActionTemplateViewSet(viewsets.ModelViewSet):
    queryset = ActionTemplate.objects.select_related("action_definition").all()
    serializer_class = ActionTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAdmin()]
        return [permissions.IsAuthenticated()]


class DevicePermissionViewSet(viewsets.ModelViewSet):
    """Admin manages grants; any authenticated user can list/view their
    OWN grants (needed so operators know what they're allowed to run)."""
    serializer_class = DevicePermissionSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [permissions.IsAuthenticated()]
        return [IsAdmin()]

    def get_queryset(self):
        qs = DevicePermission.objects.select_related("user", "device", "action_definition")
        user = self.request.user
        is_admin = user.is_superuser or (getattr(user, "role", None) and user.role.name == "Admin")
        return qs if is_admin else qs.filter(user=user)

    def perform_create(self, serializer):
        serializer.save(granted_by=self.request.user)



class ChangeRequestViewSet(viewsets.ModelViewSet):
    """A submitted ChangeRequest is validated and rendered immediately, but
    NOT executed until a separate /confirm/ call — gives the requester a
    chance to review generated_commands before anything touches the device."""
    serializer_class = ChangeRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        is_admin = user.is_superuser or (getattr(user, "role", None) and user.role.name == "Admin")
        qs = ChangeRequest.objects.select_related("action_definition", "device", "requested_by")
        return qs if is_admin else qs.filter(requested_by=user)

    def perform_create(self, serializer):
        device = serializer.validated_data["device"]
        action_definition = serializer.validated_data["action_definition"]

        has_permission = DevicePermission.objects.filter(
            user=self.request.user,
            device=device,
            action_definition=action_definition,
        ).exists()

        if not has_permission:
            raise PermissionDenied(
                f"Access Denied: You do not possess authorization mapping to run "
                f"'{action_definition.name}' on '{device.name}'."
            )

        try:
            # This validates + renders generated_commands via clean(), but
            # does NOT dispatch execution — that only happens on /confirm/.
            serializer.save(requested_by=self.request.user)
        except DjangoValidationError as e:
            detail = e.message_dict if hasattr(e, "message_dict") else {"detail": e.messages}
            raise DRFValidationError(detail)

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        """Actually queues execution. Only valid while still PENDING —
        get_object() already scopes non-admins to their own requests."""
        change_request = self.get_object()

        if change_request.status != "PENDING":
            return Response(
                {"detail": "This request has already been processed."},
                status=400,
            )

        transaction.on_commit(
            lambda: execute_change_request_task.delay(change_request.id)
        )

        return Response({"detail": "Execution queued."}, status=202)