from rest_framework import viewsets, mixins, serializers
from rest_framework.decorators import api_view, action, permission_classes
from rest_framework.permissions import SAFE_METHODS, IsAuthenticated
from rest_framework.response import Response
from users.permissions import IsAdmin, ReadOnlyOrOperatorAbove,IsViewerOrAbove
from django.utils import timezone


from .models import (
    Device,
    Snapshot,
    ConfigChange,
    Alert,
    SeverityClass,
    TrackedConcept,
    DetectionProfile,
)

from .serializers import (
    DeviceSerializer,
    SnapshotSerializer,
    ConfigChangeSerializer,
    AlertSerializer,
    SeverityClassSerializer,
    TrackedConceptSerializer,
    DetectionProfileSerializer,
    SUPPORTED_DEVICE_TYPES
)

from .tasks import pull_config_task

from users.permissions import IsAdmin, ReadOnlyOrOperatorAbove


_DEVICE_TYPE_LABELS = {
    "linux": "Linux (FRR)",
    "cisco_xe": "Cisco IOS-XE",
}

def _scope_to_operator_devices(queryset, user, relation):
    role = getattr(user, "role", None)
    if user.is_superuser or (role is not None and role.name == "Admin"):
        return queryset
    if role is not None and role.name == "Operator":
        return queryset.filter(**{f"{relation}__user": user}).distinct()
    return queryset


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def device_types(request):
    return Response([
        {"value": dt, "label": _DEVICE_TYPE_LABELS.get(dt, dt)}
        for dt in sorted(SUPPORTED_DEVICE_TYPES)
    ])

class DeviceViewSet(viewsets.ModelViewSet):
    """
    Full CRUD for the device registry, plus three read/trigger actions.

    Viewers:
        - Can read devices, snapshots, and changes.

    Operators:
        - Can trigger checks.

    Admins:
        - Can create, update, delete, pause, and resume devices.
    """
    queryset = Device.objects.all()
    serializer_class = DeviceSerializer

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy", "pause", "resume"):
            return [IsAdmin()]
        return [ReadOnlyOrOperatorAbove()]

    def get_queryset(self):
        return _scope_to_operator_devices(
            Device.objects.all(), self.request.user, "allowed_permissions"
        )

    @action(detail=True, methods=["get"])
    def snapshots(self, request, pk=None):
        snapshots = Snapshot.objects.filter(
            device=self.get_object()
        ).order_by("-taken_at")

        return Response(
            SnapshotSerializer(snapshots, many=True).data
        )

    @action(detail=True, methods=["get"])
    def changes(self, request, pk=None):
        changes = ConfigChange.objects.filter(
            device=self.get_object()
        ).order_by("-detected_at")

        return Response(
            ConfigChangeSerializer(changes, many=True).data
        )

    @action(detail=True, methods=["post"])
    def check_now(self, request, pk=None):
        """
        Only enqueues the job — the actual SSH/Netmiko work happens
        in the Celery worker, not inside this request.
        """
        device = self.get_object()
        pull_config_task.delay(device.pk)

        return Response(
            {"status": "queued"},
            status=202
        )

    @action(detail=True, methods=["post"])
    def pause(self, request, pk=None):
        device = self.get_object()

        device.is_active = False
        device.save(update_fields=["is_active"])

        return Response(
            DeviceSerializer(device).data
        )

    @action(detail=True, methods=["post"])
    def resume(self, request, pk=None):
        device = self.get_object()

        device.is_active = True
        device.save(update_fields=["is_active"])

        return Response(
            DeviceSerializer(device).data
        )


class SnapshotViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    Read-only for everyone with a role. set_baseline is Admin-only.
    """
    serializer_class = SnapshotSerializer

    def get_permissions(self):
        if self.action == "set_baseline":
            return [IsAdmin()]
        return [ReadOnlyOrOperatorAbove()]

    def get_queryset(self):
        qs = Snapshot.objects.all().order_by("-taken_at")
        qs = _scope_to_operator_devices(qs, self.request.user, "device__allowed_permissions")

        device_id = self.request.query_params.get("device")

        if device_id:
            qs = qs.filter(device_id=device_id)

        return qs

    @action(detail=True, methods=["post"])
    def set_baseline(self, request, pk=None):
        snapshot = self.get_object()

        if not snapshot.is_baseline:
            snapshot.promote_to_baseline()

        return Response(
            SnapshotSerializer(snapshot).data
        )

class ConfigChangeViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    Read-only for the change log itself (Viewer+). Acknowledging a change
    is Admin-only — operators can act on devices, but the final call on
    whether a detected change is reviewed/closed belongs to an admin.
    """
    serializer_class = ConfigChangeSerializer

    def get_permissions(self):
        if self.action == "acknowledge":
            return [IsAdmin()]
        return [ReadOnlyOrOperatorAbove()]

    def get_queryset(self):
        qs = (
            ConfigChange.objects.all()
            .select_related(
                "device",
                "severity_class",
                "acknowledged_by",
                "change_request__requested_by",  # Prefetches the ChangeRequest and the user who requested it
            )
            .prefetch_related("matched_concepts")
            .order_by("-detected_at")
        )
        qs = _scope_to_operator_devices(qs, self.request.user, "device__allowed_permissions")

        device_id = self.request.query_params.get("device")

        if device_id:
            qs = qs.filter(device_id=device_id)

        severity = self.request.query_params.get("severity")

        if severity:
            if severity.isdigit():
                qs = qs.filter(severity_class_id=severity)
            else:
                qs = qs.filter(severity_class__name__iexact=severity)

        status_param = self.request.query_params.get("status")

        if status_param:
            qs = qs.filter(status=status_param)

        return qs

    @action(detail=True, methods=["post"])
    def acknowledge(self, request, pk=None):
        change = self.get_object()
        change.status = "ACKNOWLEDGED"
        change.acknowledged_at = timezone.now()
        change.acknowledged_by = request.user
        change.save(update_fields=["status", "acknowledged_at", "acknowledged_by"])
        return Response(ConfigChangeSerializer(change, context={"request": request}).data)


class AlertViewSet(
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    Read-only list for the bell-icon feed,
    plus mark_delivered.
    """
    serializer_class = AlertSerializer
    permission_classes = [ReadOnlyOrOperatorAbove]

    def get_queryset(self):
        qs = Alert.objects.all().order_by("-created_at")
        qs = _scope_to_operator_devices(qs, self.request.user, "change__device__allowed_permissions")

        delivered = self.request.query_params.get("delivered")

        if delivered is not None:
            qs = qs.filter(
                delivered=delivered.lower() == "true"
            )

        return qs

    @action(detail=True, methods=["post"])
    def mark_delivered(self, request, pk=None):
        alert = self.get_object()

        alert.delivered = True
        alert.save()

        return Response(
            AlertSerializer(alert).data
        )


class SeverityClassViewSet(viewsets.ModelViewSet):
    """
    Only Admins can manage severity tiers.
    """
    queryset = SeverityClass.objects.all()
    serializer_class = SeverityClassSerializer
    permission_classes = [IsAdmin]


class TrackedConceptViewSet(viewsets.ModelViewSet):
    """
    Only Admins can manage detection rules.
    """
    queryset = TrackedConcept.objects.all()
    serializer_class = TrackedConceptSerializer
    permission_classes = [IsAdmin]

    def perform_destroy(self, instance):
        if instance.source == "BUILTIN":
            raise serializers.ValidationError(
                "Built-in tracked concepts cannot be deleted."
            )

        instance.delete()


class DetectionProfileViewSet(viewsets.ModelViewSet):
    """
    Anyone with a role (Viewer+) can list/view detection profiles so they can
    be selected when updating devices. Only Admins can build, edit, or delete profiles.
    """
    queryset = DetectionProfile.objects.all()
    serializer_class = DetectionProfileSerializer

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [IsViewerOrAbove()]
        return [IsAdmin()]