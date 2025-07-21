from rest_framework import permissions
from chama.models import Chama

class IsChamaMember(permissions.BasePermission):
    """Only members of the chama can create/view contributions."""

    def _is_member(self, user, chama_id):
        return Chama.objects.filter(
            id=chama_id,
            members__user=user
        ).exists()

    def has_permission(self, request, view):
        if request.user.is_staff:
            return True
            
        chama_id = request.query_params.get("chama") or request.data.get("chama")
        if not chama_id:
            return False
            
        return self._is_member(request.user, chama_id)