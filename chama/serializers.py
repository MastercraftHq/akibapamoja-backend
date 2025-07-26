from rest_framework import serializers
from .models  import Chama, Membership

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
    - Handles Chama group information and nested members
    """

    members = MembershipSerializer(many=True, read_only=True)

    class Meta:
        model = Chama
        fields = '__all__'
        read_only_fields = ['join_code', 'created_at', 'updated_at']

