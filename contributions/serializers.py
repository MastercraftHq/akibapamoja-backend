from rest_framework import serializers
from django.utils import timezone
from django.db import models
from .models import Contribution, ContributionSchedule
from chama.models import Membership

class ContributionSerializer(serializers.ModelSerializer):
    member = serializers.ReadOnlyField(source="member.id")
    user = serializers.ReadOnlyField(source="member.user.id")
    status = serializers.ReadOnlyField()

    class Meta:
        model = Contribution
        fields = [
            "id", "member", "user", "chama", "schedule", "amount", "method",
            "reference", "status", "notes", "created_at"
        ]
        read_only_fields = ["id", "member", "user", "status", "created_at"]

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than 0")
        return value

    def validate_member_id(self, value):
        chama = self.context.get('chama')
        if not Membership.objects.filter(chama=chama, id=value).exists():
            raise serializers.ValidationError("Member does not belong to this chama.")
        return value

    def create(self, validated_data):
        validated_data["chama"] = self.context["chama"]
        validated_data["member"] = self.context["member"]
        return super().create(validated_data)


class ContributionScheduleSerializer(serializers.ModelSerializer):
    is_overdue = serializers.SerializerMethodField()
    amount_paid = serializers.SerializerMethodField()
    amount_remaining = serializers.SerializerMethodField()

    class Meta:
        model = ContributionSchedule
        fields = [
            'id', 'due_date', 'expected_amount',
            'status', 'chama', 'is_overdue', 'amount_paid',
            'amount_remaining', 'created_at'
        ]

    def get_is_overdue(self, obj):
        return obj.due_date < timezone.now().date() and obj.status in ['PENDING', 'PARTIAL']

    def get_amount_paid(self, obj):
        total = Contribution.objects.filter(
            schedule=obj,
            is_confirmed=True
        ).aggregate(total=models.Sum('amount'))['total']
        return total or 0.00

    def get_amount_remaining(self, obj):
        return (obj.expected_amount or 0.00) - self.get_amount_paid(obj)


class ContributionCreateSerializer(serializers.ModelSerializer):
    member_id = serializers.UUIDField(required=False)
    schedule_id = serializers.UUIDField(required=True)

    class Meta:
        model = Contribution
        fields = [
            'member_id', 'schedule_id', 'amount', 'method', 'transaction_date',
            'notes', 'reference'
        ]

    def validate_member_id(self, value):
        if value is None:
            return None
        chama = self.context.get('chama')
        if not chama.members.filter(id=value).exists():
            raise serializers.ValidationError("Member does not belong to this chama.")
        return value

    def validate_schedule_id(self, value):
        chama = self.context.get('chama')
        if not chama.contribution_schedules.filter(id=value).exists():
            raise serializers.ValidationError("Schedule does not belong to this chama.")
        return value

    def create(self, validated_data):
        member_id = validated_data.pop('member_id', None)
        schedule_id = validated_data.pop('schedule_id')
        chama = self.context.get('chama')

        # Get related schedule
        schedule = chama.contribution_schedules.get(id=schedule_id)
        validated_data['schedule'] = schedule

        # Resolve member
        if member_id:
            member = chama.members.get(id=member_id)
        else:
            user = self.context['request'].user
            member = chama.members.get(user=user)

        validated_data['member'] = member
        validated_data['chama'] = chama

        return Contribution.objects.create(**validated_data)


class ContributionStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contribution
        fields = ['status']
        extra_kwargs = {
            'status': {'required': True}
        }

    def validate_status(self, value):
        valid_statuses = dict(Contribution.Status.choices)
        if value not in valid_statuses:
            raise serializers.ValidationError(
                f"Invalid status. Allowed values: {', '.join(valid_statuses.keys())}"
            )
        return value
