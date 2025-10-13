from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.db import transaction
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from users.models import User, Profile
from users.enums import UserRole
from users.validators import (
    is_email,
    validate_unique_email,
    validate_unique_phone,
    validate_required_email_and_phone,
)


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ["bio", "avatar"]


class UserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(required=False)

    class Meta:
        model = User
        fields = [
            "id", "first_name", "last_name", "email", "phone", "role",
            "created_at", "profile"
        ]
        read_only_fields = ["id", "role", "created_at"]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    email = serializers.EmailField(validators=[validate_unique_email])
    phone = serializers.CharField(validators=[validate_unique_phone])

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "phone", "password"]
        extra_kwargs = {"password": {"write_only": True, "required": True}, "email": {"required": True}, "phone": {"required": True}}

    def validate(self, attrs):
        return validate_required_email_and_phone(attrs)

    @transaction.atomic
    def create(self, validated_data):
        email = validated_data.pop("email")
        password = validated_data.pop("password")
        phone = validated_data.pop("phone")
        user = User.objects.create_user(password=password, phone=phone, email=email, **validated_data)
        Profile.objects.create(user=user)
        return user

class LoginObtainPairSerializer(TokenObtainPairSerializer):
    """Custom serializer for token obtain pair."""
    
    def validate(self, attrs):
        data = super().validate(attrs)
        data["message"] = "Token obtained successfully."
        return data

class LoginRefreshSerializer(TokenRefreshSerializer):
    """Custom serializer for token refresh."""
    
    def validate(self, attrs):
        data = super().validate(attrs)
        data["message"] = "Token refreshed successfully."
        return data

class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField(
        required=True,
        allow_blank=False,
        error_messages={
            "blank": "Identifier (email or phone) is required.",
            "required": "Identifier (email or phone) is required."
        }
    )
    password = serializers.CharField()

    def validate(self, attrs):
        identifier = attrs.get("identifier")
        password = attrs.get("password")

        user = authenticate(
            request=self.context.get("request"),
            email=identifier if is_email(identifier) else None,
            phone=identifier if not is_email(identifier) else None,
            password=password
        )

        if not user:
            raise serializers.ValidationError("Invalid credentials.")

        attrs["user"] = user
        return attrs

class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(required=True, help_text="Refresh token to blacklist")

from rest_framework_simplejwt.exceptions import TokenError

class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(required=True, help_text="Refresh token to blacklist")

    def validate_refresh(self, value):
        """ Validate refresh token is valid before blacklisting """
        # The underlying library will handle already blacklisted tokens gracefully.
        try:
            RefreshToken(value)
        except TokenError:
            raise serializers.ValidationError("Invalid or malformed refresh token.")
        return value


class UpdateUserSerializer(serializers.ModelSerializer):
    bio = serializers.CharField(required=False, allow_blank=True)
    avatar = serializers.ImageField(required=False)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "phone", "role", "bio", "avatar"]
        extra_kwargs = {
            "email": {"required": False},
            "phone": {"required": False},
            "first_name": {"required": False},
            "last_name": {"required": False},
            "bio": {"required": False},
            "avatar": {"required": False},
            "role": {"read_only": True},
        }

    @transaction.atomic
    def update(self, instance, validated_data):
        request = self.context.get("request")
        is_admin = request and request.user and request.user.is_staff

        # Allow admins to update role
        if is_admin and "role" in self.initial_data:
            role_value = self.initial_data.get("role")
            if role_value in UserRole.values:
                instance.role = role_value

        # Update user fields
        for attr in ["first_name", "last_name", "email", "phone"]:
            if attr in validated_data:
                setattr(instance, attr, validated_data[attr])
        instance.save()

        # Update or create profile
        profile, _ = Profile.objects.get_or_create(user=instance)
        for attr in ["bio", "avatar"]:
            if attr in validated_data:
                setattr(profile, attr, validated_data[attr])
        profile.save()

        return instance
