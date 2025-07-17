from rest_framework import permissions
from chama.models import Chama
from chama.models import Membership
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

class ContributionFilterPermission(permissions.BasePermission):
    """
    Permission for contributions listing endpoint:
    - Allows chama_id filtering for active chama members.
    - Allows member_id filtering only for admins/treasurers.
    - Ensures authenticated access.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        # Handle chama_id filtering
        if 'chama_id' in request.query_params:
            chama_id = request.query_params.get('chama_id')
            try:
                # Reuse IsChamaMember logic, but ensure active status
                return Membership.objects.filter(
                    user=request.user,
                    chama__id=chama_id,
                    status=Membership.Status.ACTIVE
                ).exists()
            except ValueError:
                return False  # Invalid chama_id

        # Handle member_id filtering (requires admin/treasurer role)
        if 'member_id' in request.query_params:
            chama_id = request.query_params.get('chama_id')
            if not chama_id:
                return False  # member_id requires chama_id
            try:
                return Membership.objects.filter(
                    user=request.user,
                    chama__id=chama_id,
                    role__in=[Membership.Role.ADMIN, Membership.Role.TREASURER],
                    status=Membership.Status.ACTIVE
                ).exists()
            except ValueError:
                return False  # Invalid chama_id

        # Allow access to own contributions if no filters are provided
        return True