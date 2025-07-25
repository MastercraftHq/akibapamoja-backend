from rest_framework import serializers
from .models import Contribution, ContributionSchedule, ContributionCycle
from chama.models import Membership
from django.utils import timezone

class ContributionScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContributionSchedule
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "status"]

class ContributionCreateSerializer(serializers.ModelSerializer):
    schedule = serializers.PrimaryKeyRelatedField(queryset=ContributionSchedule.objects.all())

    class Meta:
        model = Contribution
        fields = ['schedule', 'amount', 'method', 'reference']
        extra_kwargs = {
            'method': {'required': False},
            'reference': {'required': False}
        }

    def create(self, validated_data):
        member_id = validated_data.pop('member_id', None)
        schedule = validated_data.pop('schedule')
        chama = self.context.get['chama']

        # Resolve member
        if member_id:
            member = chama.members.get(id=member_id)
        else:
            user = self.context['request'].user
            member = chama.members.get(user=user)

        method = validated_data.get('method', 'CASH')

        return Contribution.objects.create(
            member=member,
            chama=chama,
            schedule=schedule,
            #method=method,
            #status='PENDING',
            **validated_data
        )


class ContributionCycleSerializer(serializers.ModelSerializer):
    expected_total = serializers.DecimalField(source='expected_total', max_digits=10, decimal_places=2, read_only=True)
    collected_total = serializers.DecimalField(source='collected_total', max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = ContributionCycle
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "is_completed", "completed_at"]


class ContributionSerializer(serializers.ModelSerializer):
    member = serializers.PrimaryKeyRelatedField(queryset=Membership.objects.all())
    chama = serializers.UUIDField(source='chama.id', read_only=True)
    recorded_by = serializers.HiddenField(default=serializers.CurrentUserDefault())
    user = serializers.IntegerField(source="member.user.id", read_only=True)

    class Meta:
        model = Contribution
        fields = [
            "id",
            "member",
            "chama",
            "contribution_cycle",
            "schedule",
            "amount",
            "method",
            "status",
            "transaction_date",
            "recorded_by",
            "reference",
            "notes",
            "is_confirmed",
            "confirmed_at",
            "created_at",
            "updated_at",
            "user",
        ]
        read_only_fields = [
            "id", "chama", "status", "is_confirmed", "confirmed_at",
            "created_at", "updated_at"
        ]

    def create(self, validated_data):
        method = validated_data.get("method", Contribution.PaymentMethod.CASH)
        if method == Contribution.PaymentMethod.MPESA:
            validated_data["status"] = Contribution.Status.COMPLETED
            validated_data["confirmed_at"] = timezone.now()
        else:
            validated_data["status"] = Contribution.Status.PENDING
        return super().create(validated_data)


class ContributionStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contribution
        fields = ["status"]

    def validate_status(self, value):
        valid_statuses = [Contribution.Status.APPROVED, Contribution.Status.REJECTED]
        if value not in valid_statuses:
            raise serializers.ValidationError(f"Invalid status update. Must be one of {valid_statuses}")
        return value