from rest_framework import serializers
from .models  import Chama, Membership, ContributionSchedule
from .enums import (
    MembershipRole, 
    MembershipStatus,
    ContributionFrequency,
    ContributionStatus
)
from .validators import validate_contribution_day, validate_future_date
from django.core.validators import MinValueValidator


class ContributionScheduleSerializer(serializers.ModelSerializer):
    """
    Serializer for Contribution Schedule:
    - Represents recurring contribution rules within a Chama.
    """

    class Meta:
        model = ContributionSchedule
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'chama']
        extra_kwargs = {
            'amount': {'min_value': 0.01},
            'due_day': {'min_value': 1, 'max_value': 31}
        }

    def validate(self, data):
        frequency = data.get('frequency')
        due_day = data.get('due_day')
        start_date = data.get('start_date')

        if frequency and due_day is not None:
            validate_contribution_day(due_day, frequency)

        if start_date:
            validate_future_date(start_date)
            
        return data


class MembershipSerializer(serializers.ModelSerializer):
    """
    Serializer for Membership:
    - Captures member details, role in the chama, and payout order.
    """

    class Meta:
        model = Membership
        fields = ['user', 'role', 'status', 'payout_order']
        read_only_fields = ['joined_at', 'status']


class ChamaSerializer(serializers.ModelSerializer):
    """
    Serializer for Chama:
    - Handles Chama group information and nested members & contribution schedules.
    """

    members = MembershipSerializer(many=True, read_only=True)
    contribution_schedules = ContributionScheduleSerializer(many=True, read_only=True)

    class Meta:
        model = Chama
        fields = '__all__'
        read_only_fields = ['join_code', 'created_at', 'updated_at']

