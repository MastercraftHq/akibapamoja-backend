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

class MembershipSerializer(serializers.ModelSerializer):
    class Meta:
        model = Membership
        fields = '__all__'
        
        
class JoinChamaSerializer(serializers.Serializer):
    join_code = serializers.CharField(max_length=12, required=True)

    def validate_join_code(self, value):
        try:
            chama = Chama.objects.get(join_code=value)
        except Chama.DoesNotExist:
            raise serializers.ValidationError("Invalid join code.")
        return chama

    def validate(self, attrs):
        chama = attrs['join_code']  # This is the Chama object from validate_join_code
        user = self.context['request'].user
        if Membership.objects.filter(user=user, chama=chama).exists():
            raise serializers.ValidationError("You are already a member of this Chama.")
        return attrs