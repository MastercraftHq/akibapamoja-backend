from rest_framework.permissions import BasePermission
from contributions.models import Contribution
from chama.models import Membership


class IsChamaAdmin(BasePermission):
    """
    Allows access only to Chama admins with active status.
    """

    def has_permission(self, request, view):
        # Try resolving chama_id from query, data, or view kwargs
        chama_id = (
            request.query_params.get("chama") or
            request.data.get("chama") or
            view.kwargs.get("groupId") or
            view.kwargs.get("pk")
        )

        # If not found, try resolving from the object
        if not chama_id and hasattr(view, 'get_object'):
            try:
                obj = view.get_object()
                if isinstance(obj, Contribution):
                    chama_id = obj.chama_id
                elif hasattr(obj, 'chama_id'):
                    chama_id = obj.chama_id
            except Exception:
                return False

        if not chama_id:
            return False

        return Membership.objects.filter(
            user=request.user,
            chama_id=chama_id,
            role=Membership.Role.ADMIN,
            status=Membership.Status.ACTIVE
        ).exists()


class IsChamaMember(BasePermission):
    """
    Allows access only to active members of the Chama.
    """

    def has_permission(self, request, view):
        chama_id = (
            request.query_params.get("chama") or
            request.data.get("chama") or
            view.kwargs.get("groupId") or
            view.kwargs.get("pk")
        )

        if not chama_id and hasattr(view, 'get_object'):
            try:
                obj = view.get_object()
                chama_id = getattr(obj, 'chama_id', None)
            except Exception:
                return False

        if not chama_id:
            return False

        return Membership.objects.filter(
            user=request.user,
            chama_id=chama_id,
            status=Membership.Status.ACTIVE
        ).exists()
