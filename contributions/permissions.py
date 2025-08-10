from rest_framework import permissions
from rest_framework.exceptions import NotFound
from chama.models import Chama, Membership


def _to_str_lower(val):
    """Convert enum member or value to lower-case string for safe comparison."""
    if val is None:
        return None
    if hasattr(val, "value"):
        try:
            val = val.value
        except Exception:
            pass
    return str(val).lower()


class IsChamaAdminOrReadOnly(permissions.BasePermission):
    def _get_chama_id(self, request, view):
        chama_id = getattr(view, "kwargs", {}).get("chama_id")
        if not chama_id:
            chama_id = request.query_params.get("chama") or request.data.get("chama")
        return chama_id

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        chama_id = self._get_chama_id(request, view)
        if not chama_id:
            if request.method in permissions.SAFE_METHODS:
                if getattr(request.user, "is_staff", False) or getattr(request.user, "is_superuser", False):
                    return True
                return Membership.objects.filter(user=request.user, status__iexact="active").exists()
            return False

        if not Chama.objects.filter(id=chama_id).exists():
            raise NotFound(detail="Chama not found")

        try:
            membership = Membership.objects.get(user=request.user, chama__id=chama_id)
        except Membership.DoesNotExist:
            return False

        member_status = _to_str_lower(getattr(membership, "status", None))
        member_role = _to_str_lower(getattr(membership, "role", None))

        is_active = (member_status == "active")
        is_admin = (member_role == "admin") or getattr(request.user, "is_staff", False)

        if request.method in permissions.SAFE_METHODS:
            return is_active
        else:
            return is_active and is_admin


class IsChamaMemberOrAdminWrite(permissions.BasePermission):
    """
    Permissions for contributions endpoints.

    - If no chama_id is provided (root /contributions/): platform staff OR
      any chama admin (active role=='admin') can access.
    - If chama_id is provided:
        - active members may GET (list) and POST (create contributions)
        - only active chama admins (role == 'admin') or platform staff can perform unsafe methods beyond POST (PUT/PATCH/DELETE)
    - If chama_id does not exist -> raise NotFound
    """

    def _get_chama_id(self, request, view):
        # contributions use query param '?chama=' by convention; also check path kwargs and request.data
        chama_id = request.query_params.get("chama") or getattr(view, "kwargs", {}).get("chama_id") or request.data.get("chama")
        return chama_id

    def has_permission(self, request, view):
        # Require authentication
        if not request.user or not request.user.is_authenticated:
            return False

        user = request.user
        chama_id = self._get_chama_id(request, view)

        # Helper: is the user an admin in any chama?
        is_admin_in_any_chama = Membership.objects.filter(
            user=user, role__iexact='admin', status__iexact='active'
        ).exists()

        # No chama_id: allow platform staff OR chama-admin-of-any-chama
        if not chama_id:
            if getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
                return True
            return is_admin_in_any_chama

        # If chama_id provided, ensure Chama exists => raise 404 if not found
        if not Chama.objects.filter(id=chama_id).exists():
            raise NotFound(detail="Chama not found")

        try:
            membership = Membership.objects.get(user=user, chama__id=chama_id)
        except Membership.DoesNotExist:
            return False

        member_status = _to_str_lower(getattr(membership, "status", None))
        member_role = _to_str_lower(getattr(membership, "role", None))

        is_active = (member_status == "active")
        is_admin = (member_role == "admin")

        # Staff bypass: platform staff can always act
        if getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
            return True

        # GET/list allowed for active members
        if request.method in permissions.SAFE_METHODS:
            return is_active

        # POST (create contribution) allowed for active members
        if request.method == "POST":
            return is_active

        # Other unsafe methods (PUT/PATCH/DELETE) require active admin
        return is_active and is_admin
