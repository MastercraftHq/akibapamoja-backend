from rest_framework import serializers
from .models  import Chama, Membership

class ChamaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chama
        fields = '__all__'

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