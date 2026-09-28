from rest_framework.routers import DefaultRouter
from django.urls import path, include

from .views import (
    ActionDefinitionViewSet,
    ActionTemplateViewSet,
    ChangeRequestViewSet,
    DevicePermissionViewSet,
    ActionChoicesView,
)

router = DefaultRouter()
router.register(r"action-definitions", ActionDefinitionViewSet, basename="action-definition")
router.register(r"action-templates", ActionTemplateViewSet, basename="action-template")
router.register(r"change-requests", ChangeRequestViewSet, basename="change-request")
router.register(r"device-permissions", DevicePermissionViewSet, basename="device-permission")

urlpatterns = [
    path('action-choices/', ActionChoicesView.as_view(), name='action-choices'),
    path('', include(router.urls)),
]