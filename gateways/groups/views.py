from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from drf_yasg.utils import swagger_auto_schema
from django.contrib.auth import get_user_model

from gateways.groups.serializers import (
    GroupCreateSerializer,
    GroupDetailSerializer,
    MemberInviteSerializer,
)
from gateways.groups.models import Group, Membership
from gateways.groups.enums import MembershipRole, MembershipStatus
from gateways.groups.exceptions import (
    AlreadyMemberError,
    UserNotFoundError,
    PermissionDeniedError,
    CannotLeaveAsOnlyAdminError,
    MembershipNotFoundError,
)
from gateways.groups.utils import (
    get_group_or_404,
    is_member,
    is_admin,
    get_display_name,
)

User = get_user_model()

class GroupViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(request_body=GroupCreateSerializer)
    def create(self, request):
        serializer = GroupCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        group = serializer.save(admin_user_id=request.data.get("admin_user_id"))
        return Response(
            {"groupId": group.slug, "message": "Group created."},
            status=status.HTTP_201_CREATED
        )

    def retrieve(self, request, pk=None):
        group = get_group_or_404(pk)

        if not is_member(request.user, group):
            raise PermissionDeniedError()

        serializer = GroupDetailSerializer(group)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(request_body=MemberInviteSerializer)
    @action(detail=True, methods=["post"], url_path="add-member")
    def add_member(self, request, pk=None):
        group = get_group_or_404(pk)

        if not is_admin(request.user, group):
            raise PermissionDeniedError()

        serializer = MemberInviteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data.get("email")
        role = serializer.validated_data.get("role", MembershipRole.MEMBER.value)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise UserNotFoundError()

        if Membership.objects.filter(group=group, user=user).exists():
            raise AlreadyMemberError()

        member = Membership.objects.create(
            group=group,
            user=user,
            role=role,
            status=MembershipStatus.INVITED.value
        )
        return Response(
            {
                "memberId": member.id,
                "status": member.status,
                "inviteCode": member.invite_code
            },
            status=status.HTTP_201_CREATED
        )

    @action(detail=False, methods=["post"], url_path="join-by-code")
    def join_by_code(self, request):
        code = request.data.get("invite_code")
        if not code:
            return Response({"detail": "Invite code is required."}, status=400)

        try:
            membership = Membership.objects.get(invite_code=code, user=request.user)
        except Membership.DoesNotExist:
            raise PermissionDeniedError("No valid invite found for this code.")

        if membership.status != MembershipStatus.INVITED.value:
            return Response({"message": "You are already a member."}, status=400)

        membership.status = MembershipStatus.JOINED.value
        membership.save()

        return Response({"message": "Successfully joined the group."}, status=200)

    @action(detail=True, methods=["get"], url_path="members")
    def list_members(self, request, pk=None):
        group = get_group_or_404(pk)

        if not is_member(request.user, group):
            raise PermissionDeniedError()

        members = Membership.objects.filter(group=group).select_related("user")
        data = [
            {
                "userId": m.user.id,
                "name": get_display_name(m.user),
                "role": m.role,
                "status": m.status,
            }
            for m in members
        ]
        return Response({"members": data}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="join")
    def accept_invite(self, request, pk=None):
        group = get_group_or_404(pk)

        try:
            membership = Membership.objects.get(group=group, user=request.user)
        except Membership.DoesNotExist:
            raise PermissionDeniedError("You were not invited to this group.")

        if membership.status != MembershipStatus.INVITED.value:
            return Response(
                {"message": "You are already a member."},
                status=status.HTTP_400_BAD_REQUEST
            )

        membership.status = MembershipStatus.JOINED.value
        membership.save()

        return Response({"message": "You have successfully joined the group."}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="leave")
    def leave_group(self, request, pk=None):
        group = get_group_or_404(pk)

        try:
            membership = Membership.objects.get(group=group, user=request.user)
        except Membership.DoesNotExist:
            raise PermissionDeniedError()

        if membership.role == MembershipRole.ADMIN.value:
            other_admins = Membership.objects.filter(group=group, role=MembershipRole.ADMIN.value).exclude(user=request.user)
            if not other_admins.exists():
                raise CannotLeaveAsOnlyAdminError()

        membership.delete()
        return Response({"message": "You have left the group."}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="remove-member/(?P<user_id>[^/.]+)")
    def remove_member(self, request, pk=None, user_id=None):
        group = get_group_or_404(pk)

        if not is_admin(request.user, group):
            raise PermissionDeniedError()

        try:
            membership = Membership.objects.get(group=group, user_id=user_id)
        except Membership.DoesNotExist:
            raise MembershipNotFoundError()

        if membership.user == group.admin:
            return Response({"detail": "Cannot remove the group admin."}, status=status.HTTP_400_BAD_REQUEST)

        membership.delete()
        return Response({"message": "Member removed."}, status=status.HTTP_204_NO_CONTENT)
