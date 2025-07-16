from rest_framework.permissions import BasePermission
from .models import Membership


class IsChamaAdmin(BasePermission):
    """
    Allows access only to Chama admins.
    """
    def has_permission(self, request, view):
        group_id = view.kwargs.get('groupId') or view.kwargs.get('pk') or request.data.get('groupId')
        if not group_id:
            return False

        try:
            membership = Membership.objects.get(user=request.user, chama_id=group_id)
            return membership.role == Membership.Role.ADMIN and membership.status == Membership.Status.ACTIVE
        except Membership.DoesNotExist:
            return False


class IsChamaMember(BasePermission):
    """
    Allows access only to Chama members.
    """
    def has_permission(self, request, view):
        group_id = view.kwargs.get('groupId') or view.kwargs.get('pk') or request.data.get('groupId')
        if not group_id:
            return False

        return Membership.objects.filter(
            user=request.user,
            chama_id=group_id,
            status=Membership.Status.ACTIVE
        ).exists()
