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

        # Ensure payment method defaults to CASH for manual contributions
        if not validated_data.get("method"):
            validated_data["method"] = Contribution.PaymentMethod.CASH

        validated_data["status"] = Contribution.Status.PENDING

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
            status=Contribution.Status.APPROVED
        ).aggregate(total=models.Sum('amount'))['total']
        return total or 0.00

    def get_amount_remaining(self, obj):
        return (obj.expected_amount or 0.00) - self.get_amount_paid(obj)


class ContributionCreateSerializer(serializers.ModelSerializer):
    schedule = serializers.PrimaryKeyRelatedField(queryset=ContributionSchedule.objects.all())
    method = serializers.ChoiceField(choices=Contribution.PaymentMethod.choices, required=False)

    class Meta:
        model = Contribution
        fields = ['schedule', 'amount', 'method']
        extra_kwargs = {
            'amount': {'required': True},
            'method': {'required': False}
        }

    def validate(self, data):
        if data.get('method') == 'MPESA' and not data.get('reference'):
            raise serializers.ValidationError("Reference is required for MPESA payments")
        return data

    def create(self, validated_data):
        chama = self.context.get('chama')
        user = self.context['request'].user
        member = chama.members.get(user=user)
        method = validated_data.get('method', 'CASH')
        status = 'APPROVED' if method == 'MPESA' else 'PENDING'

        return Contribution.objects.create(
            member=member,
            chama=chama,
            schedule=validated_data['schedule'],
            method=method,
            status=status,
            amount=validated_data['amount'],
            reference=validated_data.get('reference', '')
        )

class ContributionStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contribution
        fields = ['status']

    def validate_status(self, value):
        if value not in ['APPROVED', 'REJECTED']:  # Now matches model
            raise serializers.ValidationError("Invalid status. Must be 'APPROVED' or 'REJECTED'.")
        return value
