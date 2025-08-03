from rest_framework import permissions
from chama.models import Chama, Membership

class IsChamaMember(permissions.BasePermission):
    """Only members of the chama can create / view contributions."""

    def _is_member(self, user, chama_id):
        return Chama.objects.filter(
            id=chama_id,
            members__user=user
        ).exists()

    def has_permission(self, request, view):
        chama_id = view.kwargs.get('chama_id') or request.data.get('chama_id')
        
        if not chama_id:
            return False
        
        return Membership.objects.filter(
            user=request.user,
            chama_id=chama_id,
            status=Membership.Status.ACTIVE
        ).exists()

