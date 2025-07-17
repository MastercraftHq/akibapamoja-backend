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