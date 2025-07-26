# permissions.py
from rest_framework.permissions import BasePermission
from .models import Membership
from .enums import MembershipRole

class IsChamaAdmin(BasePermission):
    def has_permission(self, request, view):
        chama = view.get_object()
        try:
            membership = Membership.objects.get(user=request.user, chama=chama)
            return membership.role == MembershipRole.ADMIN.value
        except Membership.DoesNotExist:
            return False

class IsChamaMember(BasePermission):
    def has_permission(self, request, view):
        chama = view.get_object()
        return Membership.objects.filter(user=request.user, chama=chama).exists()
