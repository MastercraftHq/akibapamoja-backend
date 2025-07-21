import re
from rest_framework import serializers
from users.models import User

EMAIL_PATTERN = r"[^@]+@[^@]+\.[^@]+"
PHONE_PATTERN = r"^\d{10,15}$"

def validate_unique_email(value):
    if User.objects.filter(email=value).exists():
        raise serializers.ValidationError("A user with this email already exists.")
    return value


def validate_unique_phone(value):
    if User.objects.filter(phone=value).exists():
        raise serializers.ValidationError("A user with this phone number already exists.")
    return value

def validate_required_email_and_phone(attrs):
    email = attrs.get("email")
    phone = attrs.get("phone")

    if not email and not phone:
        raise serializers.ValidationError("Either email or phone number is required.")

    return attrs

def validate_identifier(identifier: str) -> bool:
    return bool(re.match(EMAIL_PATTERN, identifier)) or bool(re.match(PHONE_PATTERN, identifier))

def is_email(identifier: str) -> bool:
    return bool(re.match(EMAIL_PATTERN, identifier))

def is_phone(identifier: str) -> bool:
    return bool(re.match(PHONE_PATTERN, identifier))

def check_duplicate_user(identifier: str):
    if is_email(identifier):
        if User.objects.filter(email=identifier).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return True
    elif is_phone(identifier):
        if User.objects.filter(phone=identifier).exists():
            raise serializers.ValidationError("A user with this phone number already exists.")
        return False
    else:
        raise serializers.ValidationError("Identifier must be a valid email or phone number.")