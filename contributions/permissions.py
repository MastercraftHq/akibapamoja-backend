from rest_framework import permissions
from .models import Membership

class IsChamaMember(permissions.BasePermission):
    """
    Allows access if the authenticated user is a member of the specified chama
    (or is staff, for listing purposes).
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # update_status action uses its own permissions
        if view.action == "update_status":
            return True

        chama_id = request.query_params.get("chama")
        if not chama_id:
            return False

        is_member = Membership.objects.filter(
            user=request.user, chama_id=chama_id
        ).exists()
        return is_member or request.user.is_staff


class IsAdminChamaMember(permissions.BasePermission):
    """
    Allows only staff users—but we’ll also check chama membership
    inside the action method itself.
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)
