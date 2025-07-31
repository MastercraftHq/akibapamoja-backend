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

    def _check_permissions(self, contribution):
        # Check if user has permission to update/delete a contribution
        try:
            membership = Membership.objects.get(user=self.request.user, chama=contribution.chama)
        except Membership.DoesNotExist:
            raise PermissionDenied("You are not a member of this Chama.")
        
        if membership.status != Membership.Status.ACTIVE:
            raise PermissionDenied("Only users with ACTIVE membership can perform this action.")
        
        return membership.role == Membership.Role.ADMIN, membership
    
    def partial_update_permission(self, request, contribution):
        # Memebrs can only delete their own PENDING or FAILED contributions
        if contribution.member.user != request.user:
            raise PermissionDenied("You can only delete your own contributions.")
        
        if contribution.status not in [Contribution.Status.PENDING, Contribution.Status.FAILED]:
            raise PermissionDenied("Only pending or rejected contributions can be deleted.")
        
        return True
