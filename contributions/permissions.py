from rest_framework import permissions
from chama.models import Chama

class IsChamaMember(permissions.BasePermission):
    """Only members of the chama can create / view contributions."""

    def _is_member(self, user, chama_id):
        return Chama.objects.filter(
            id=chama_id,
            membership_set__user=user
        ).exists()

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        chama_id = request.data.get("chama") or request.query_params.get("chama")
        return chama_id and self._is_member(request.user, chama_id)
