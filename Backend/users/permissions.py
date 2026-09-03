from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsAdmin(BasePermission):
    """Full access — role must be exactly 'Admin' (or Django superuser)."""

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        return user.role is not None and user.role.name == "Admin"


class IsOperatorOrAbove(BasePermission):
    """Admin or Operator — can act (acknowledge, poll, pause/resume), not just view."""

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        return user.role is not None and user.role.name in ("Admin", "Operator")


class IsViewerOrAbove(BasePermission):
    """Any authenticated user with a role — the baseline read access."""

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        return user.role is not None and user.role.name in ("Admin", "Operator", "Viewer")


class ReadOnlyOrOperatorAbove(BasePermission):
    """
    Mixin-style class for ViewSets: GET/HEAD/OPTIONS need only Viewer-level
    access; anything that changes data (POST/PUT/PATCH/DELETE) needs
    Operator or above.
    """

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        if user.role is None:
            return False
        if request.method in SAFE_METHODS:
            return user.role.name in ("Admin", "Operator", "Viewer")
        return user.role.name in ("Admin", "Operator")