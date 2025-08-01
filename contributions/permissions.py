from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied
from chama.models import Chama, Membership
from .models import Contribution

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
    
    def _get_membership(self, request, contribution):
        try:
            return Membership.objects.get(user=request.user, chama=contribution.chama)
        except Membership.DoesNotExist:
            raise PermissionDenied("You are not a member of this chama.")
        
    def has_object_permission(self, request, view, obj):
        # Handle update (PATCH/PUT) permissions
        # Only admins can update contributions
        if request.method in ['PATCH', 'PUT']:
            membership = self._get_membership(request=request, contribution=obj)
            if membership.role != Membership.Role.ADMIN.value:
                raise PermissionDenied("Only admins can update contributions.")
            return True
        
        # Handle delete permissions
        # Users can only delete their own contributions that are pending or failed
        if request.method == "DELETE":
            if obj.member.user != request.user:
                raise PermissionDenied("You can only delete your own contributions.")
            if obj.status not in [Contribution.Status.PENDING, Contribution.Status.FAILED]:
                raise PermissionDenied("You can only delete PENDING or FAILED contributions.")
            return True
        return False