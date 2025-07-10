from rest_framework import serializers
from .models import CustomUser, UserProfile 


#Serializer for the CustomUser model
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'password', 'first_name', 
             'last_name', 'phone_number', 'role']
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        user = CustomUser.objects.create_user(**validated_data)
        return user

# Updated: Serializer for UserProfile model
class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['bio', 'avatar']

# Serializer specifically for updating user + nested profile
class UserUpdateSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(required=False)

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'first_name', 'last_name', 'phone_number', 'role', 'profile']
        extra_kwargs = {
            'email': {'required': False},
            'username': {'required': False},
            'role': {'read_only': True},
        }

    def update(self, instance, validated_data):
        request = self.context.get('request')
        is_admin = request and request.user.is_staff

        profile_data = validated_data.pop('profile', None)
        role = validated_data.get('role')

        # Only allow role change if admin
        if role and is_admin:
            instance.role = role
        elif role:
            validated_data.pop('role')

        # Update CustomUser fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # UpProfile if provided
        if profile_data:
            profile = instance.profile
            for attr, value in profile_data.items():
                setattr(profile, attr, value)
            profile.save()

        return instance