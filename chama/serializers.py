from rest_framework import serializers
from .models import Chama, Membership

class ChamaSerializer(serializers.ModelSerializer):
    join_code = serializers.CharField(read_only=True)

    class Meta:
        model = Chama
        fields = [
            'id',
            'name',
            'description',
            'currency',
            'minimum_members',
            'maximum_members',
            'balance',
            'is_active',
            'created_at',
            'updated_at',
            'join_code',
        ]


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
        chama = attrs['join_code']
        user = self.context['request'].user
        if Membership.objects.filter(user=user, chama=chama).exists():
            raise serializers.ValidationError(
                "You are already a member of this Chama."
            )
        return attrs
