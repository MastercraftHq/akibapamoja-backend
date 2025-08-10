from rest_framework import serializers
from django.utils import timezone
from decimal import Decimal
from django.db import models
from .models import Contribution, ContributionCycle, ContributionSchedule
from chama.models import Membership
from django.contrib.auth import get_user_model

User = get_user_model()


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
    chama = serializers.PrimaryKeyRelatedField(read_only=True)  # not writable

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
        contributions = Contribution.objects.filter(
            schedule=obj,
            is_confirmed=True
        ).aggregate(total=models.Sum('amount'))
        return contributions['total'] or 0.00

    def get_amount_remaining(self, obj):
        amount_paid = obj.contributions.aggregate(total_paid=models.Sum('amount'))['total_paid'] or Decimal('0.00')
        expected = obj.expected_amount or Decimal('0.00')
        return expected - amount_paid


class ContributionCreateSerializer(serializers.ModelSerializer):
    member_id = serializers.UUIDField(required=False)
    schedule_id = serializers.UUIDField(required=False)

    class Meta:
        model = Contribution
        fields = [
            'member_id', 'schedule_id', 'amount', 'method',
            'transaction_date', 'notes', 'reference'
        ]

    def validate_member_id(self, value):
        if value is None:
            return None
        chama = self.context.get('chama')
        try:
            member = chama.members.get(id=value)
        except Membership.DoesNotExist:
            raise serializers.ValidationError("Member does not belong to this chama.")
        return member.id

    def validate_schedule_id(self, value):
        if value is None:  # allow missing schedule
            return None
        chama = self.context.get('chama')
        try:
            schedule = chama.contribution_schedules.get(id=value)
        except ContributionSchedule.DoesNotExist:
            raise serializers.ValidationError("Schedule does not belong to this chama.")
        return schedule.id

    def create(self, validated_data):
        member_id = validated_data.pop('member_id', None)
        schedule_id = validated_data.pop('schedule_id', None)
        chama = self.context.get('chama')

        # If schedule_id is provided, use it; otherwise, create a new schedule
        if schedule_id:
            schedule = chama.contribution_schedules.get(id=schedule_id)
        else:
            schedule = ContributionSchedule.objects.create(
                chama=chama,
                due_date=timezone.now().date(),  # could be calculated
                expected_amount=validated_data['amount'],
                status='PENDING'
            )
        validated_data['schedule'] = schedule

        if member_id:
            # Admin creating contribution for a specific member
            member = chama.members.get(id=member_id)
        else:
            # User creating contribution for themselves
            user = self.context['request'].user
            member = chama.members.get(user=user)

        validated_data['member'] = member
        validated_data['chama'] = chama

        return super().create(validated_data)
