from rest_framework import permissions
from django.shortcuts import get_object_or_404
from chama.models import Chama

class IsChamaMember(permissions.BasePermission):
    """Only members of the chama can create / view contributions."""

    def _is_member(self, user, chama_id):
        return Chama.objects.filter(
            id=chama_id,
            members__user=user
        ).exists()

    def has_permission(self, request, view):
        # Get chama_id from query params or request data
        chama_id = request.query_params.get("chama") or request.data.get("chama")
        
        if not chama_id:
            return False
            
        return self._is_member(request.user, chama_id)
    
class IsChamaAdminOrReadOnly(permissions.BasePermission):
    """
    - Safe methods (GET, HEAD, OPTIONS) are allowed for any ACTIVE Chama member.
    - Non-safe methods (POST, PUT, PATCH, DELETE) are only allowed for Chama admins (is_staff=True).
    """

    def has_permission(self, request, view):
        chama_id = view.kwargs.get('chama_id')
        if not chama_id:
            return False
        
        # 404 if chama does not exist
        chama = get_object_or_404(Chama, id=chama_id)

        # Must be a member
        if not chama.members.filter(user=request.user).exists():
            return False
        
        # Read-only for members
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write only for admins
        return request.user.is_staff
    
    def has_object_permission(self, request, view, obj):
        # Ensure the requesting user is in the same chama
        if not obj.chama.members.filter(user=request.user).exists():
            return False
        
        if request.method in permissions.SAFE_METHODS:
            return True
        
        return request.user.is_staff