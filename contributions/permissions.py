from rest_framework import permissions
from chama.models import Chama,Membership

class IsChamaMember(permissions.BasePermission):
    """Only members of the chama can create / view contributions."""

    def _is_member(self, user, chama_id):
        try:
            chama = Chama.objects.get(id=chama_id)
            return Membership.objects.filter(user=user, chama=chama).exists()
        except (ValueError, Chama.DoesNotExist):
            return True

    def has_permission(self, request, view):
        # Get chama_id from query params or request data
        chama_id = request.query_params.get("chama") or request.data.get("chama")
        
        if not chama_id:
            return False
            
        return self._is_member(request.user, chama_id)
    
    
    
class CanFilterByMember(permissions.BasePermission):
    """Only admins and treasurers can filter by member_id."""

    def has_permission(self, request, view):
        member_id = request.query_params.get('member')
        if not member_id:
            return True  # No member_id filter, so permission is granted

        chama_id = request.query_params.get('chama')
        if not chama_id:
            return False

        # Check if user is admin or treasurer
        return Membership.objects.filter(
            user=request.user,
            chama__id=chama_id,
            role__in=[Membership.Role.ADMIN, Membership.Role.TREASURER]
        ).exists()
