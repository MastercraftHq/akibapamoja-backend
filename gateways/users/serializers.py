from rest_framework import serializers
from django.contrib.auth import authenticate
from gateways.users.models import User, Profile
from gateways.users.enums import UserRole

class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ["bio", "avatar"]
        
class UserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(required=False)

    class Meta:
        model = User
        fields = [
            "id", "name", "email", "phone", "role",
            "created_at", "profile"
        ]
        read_only_fields = ["id", "role", "created_at"]
        
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["name", "email", "phone", "password"]

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        Profile.objects.create(user=user)  # auto-create profile
        return user

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    phone = serializers.CharField(required=False)
    password = serializers.CharField()

    def validate(self, attrs):
        email = attrs.get("email")
        phone = attrs.get("phone")
        password = attrs.get("password")

        if not email and not phone:
            raise serializers.ValidationError("Email or phone is required.")

        user = authenticate(request=self.context.get("request"), email=email, phone=phone, password=password)

        if not user:
            raise serializers.ValidationError("Invalid credentials.")

        attrs["user"] = user
        return attrs

class UpdateUserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(required=False)

    class Meta:
        model = User
        fields = ["name", "email", "phone", "role", "profile"]
        extra_kwargs = {
            "email": {"required": False},
            "phone": {"required": False},
            "name": {"required": False},
            "role": {"read_only": True},
        }

    def update(self, instance, validated_data):
        request = self.context.get("request")
        is_admin = request and request.user and request.user.is_staff

        # Extract profile data if present
        profile_data = validated_data.pop("profile", None)

        # Allow admins to update role
        if is_admin and "role" in self.initial_data:
            role_value = self.initial_data.get("role")
            if role_value in UserRole.values:
                instance.role = role_value

        # Update user fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update profile if provided
        if profile_data:
            profile, _ = Profile.objects.get_or_create(user=instance)
            for attr, value in profile_data.items():
                setattr(profile, attr, value)
            profile.save()

        return instance