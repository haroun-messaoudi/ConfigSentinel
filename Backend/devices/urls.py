from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import (
    DeviceViewSet, SnapshotViewSet, ConfigChangeViewSet, AlertViewSet,
    SeverityClassViewSet, TrackedConceptViewSet, DetectionProfileViewSet,
    device_types,
)

router = DefaultRouter()
router.register(r"devices", DeviceViewSet, basename="device")
router.register(r"snapshots", SnapshotViewSet, basename="snapshot")
router.register(r"changes", ConfigChangeViewSet, basename="change")
router.register(r"alerts", AlertViewSet, basename="alert")
router.register(r"severity-classes", SeverityClassViewSet, basename="severity-class")
router.register(r"tracked-concepts", TrackedConceptViewSet, basename="tracked-concept")
router.register(r"detection-profiles", DetectionProfileViewSet, basename="detection-profile")

urlpatterns = [
    path("devices/types/", device_types, name="device-types"),
] + router.urls