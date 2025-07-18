from rest_framework import serializers
from django.contrib.auth import authenticate
from gateways.users.models import User, Profile
from gateways.users.enums import UserRole
from gateways.users.validators import is_email, validate_unique_email, validate_unique_phone, validate_required_email_and_phone

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
        
    def validate(self, attrs):
        return validate_required_email_and_phone(attrs)
    
    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User.objects.create_user(password=password, **validated_data)
        Profile.objects.create(user=user)
        return user

class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    password = serializers.CharField()

    def validate(self, attrs):
        identifier = attrs.get("identifier")
        password = attrs.get("password")

        if not identifier:
            raise serializers.ValidationError("Identifier (email or phone) is required.")
        
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

class UpdateUserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(required=False)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "phone", "role", "profile"]
        extra_kwargs = {
            "email": {"required": False},
            "phone": {"required": False},
            "first_name": {"required": False},
            "last_name": {"required": False},
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