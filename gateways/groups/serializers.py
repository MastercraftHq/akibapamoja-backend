from rest_framework import serializers
from .models import Group, Membership
from .enums import MembershipRole, MembershipStatus
from gateways.groups.utils import get_display_name
from django.contrib.auth import get_user_model

User = get_user_model()


class GroupCreateSerializer(serializers.ModelSerializer):
    admin_user_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Group
        fields = [
            'id', 'name', 'slug',
            'contribution_amount', 'contribution_interval',
            'admin_user_id', 'created_at'
        ]
        read_only_fields = ['id', 'slug', 'created_at']

    def create(self, validated_data):
        admin_user_id = validated_data.pop('admin_user_id')
        group = Group.objects.create(admin_id=admin_user_id, **validated_data)

        Membership.objects.create(
            user_id=admin_user_id,
            group=group,
            role=MembershipRole.ADMIN,
            status=MembershipStatus.JOINED
        )
        return group


class GroupDetailSerializer(serializers.ModelSerializer):
    members = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = [
            'name', 'slug',
            'contribution_amount', 'contribution_interval',
            'created_at', 'members'
        ]

    def get_members(self, group):
        return [
            {
                "userId": member.user.id,
                "name": get_display_name(member.user),
                "role": member.role,
                "status": member.status
            }
            for member in group.memberships.select_related('user')
        ]


class MemberInviteSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.ChoiceField(
        choices=MembershipRole.choices(),
        default=MembershipRole.MEMBER,
        required=False
    )

    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("No user with this email exists.")
        return value

    def validate_role(self, value):
        if value not in MembershipRole.values():
            raise serializers.ValidationError("Invalid role.")
        return value
