# permissions.py
from rest_framework.permissions import BasePermission
from .models import Membership

class IsChamaAdmin(BasePermission):
    """
    Grants access if the requesting user has an ACTIVE admin
    membership on the target Chama.
    """

    def has_permission(self, request, view):
        # Some views (e.g. Create) don’t have get_object; fall back to kwargs or data
        group_id = (
            view.kwargs.get('groupId') or
            view.kwargs.get('pk') or
            request.data.get('groupId')
        )
        if not group_id:
            return False

        return Membership.objects.filter(
            user=request.user,
            chama_id=group_id,
            role=Membership.Role.ADMIN,
            status=Membership.Status.ACTIVE
        ).exists()

    def has_object_permission(self, request, view, obj):
        # For RetrieveAPIView/UpdateAPIView with .get_object() => obj is a Chama
        try:
            membership = Membership.objects.get(
                user=request.user,
                chama=obj
            )
        except Membership.DoesNotExist:
            return False

        return (
            membership.role   == Membership.Role.ADMIN and
            membership.status == Membership.Status.ACTIVE
        )


class IsChamaMember(BasePermission):
    """
    Grants access if the requesting user has any ACTIVE membership
    on the target Chama.
    """

    def has_permission(self, request, view):
        group_id = (
            view.kwargs.get('groupId') or
            view.kwargs.get('pk') or
            request.data.get('groupId')
        )
        if not group_id:
            return False

        return Membership.objects.filter(
            user=request.user,
            chama_id=group_id,
            status=Membership.Status.ACTIVE
        ).exists()

    def has_object_permission(self, request, view, obj):
        return Membership.objects.filter(
            user=request.user,
            chama=obj,
            status=Membership.Status.ACTIVE
        ).exists()
