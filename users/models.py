from datetime import timedelta
import uuid
import logging
import secrets
from django.contrib.auth.hashers import make_password, check_password
from django.db import models
from django_otp.models import Device
from twilio.rest import Client
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin
)
from django.core.validators import RegexValidator
from users.enums import UserRole


class UserManager(BaseUserManager):
    def create_user(self, email=None, phone=None, password=None, **extra_fields):
        if not email and not phone:
            raise ValueError("A user must have at least an email or phone number.")

        email = self.normalize_email(email) if email else None

        user = self.model(email=email, phone=phone, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email=None, phone=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if not extra_fields["is_staff"]:
            raise ValueError("Superuser must have is_staff=True.")
        if not extra_fields["is_superuser"]:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, phone, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)
    email = models.EmailField(unique=True, null=True, blank=True)
    phone = models.CharField(
        max_length=15,
        unique=True,
        null=False,
        blank=False,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
            )
        ]
    )

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices(),
        default=UserRole.MEMBER.value
    )
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'phone'  # Changed to 'phone' assuming it's more reliable; customize backend for email/phone login
    REQUIRED_FIELDS = ['email']

    objects = UserManager()

    def __str__(self):
        return self.phone or self.email or f"{self.first_name} {self.last_name}".strip()


class Profile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile"
    )
    bio = models.TextField(blank=True)
    avatar = models.ImageField(upload_to="avatars/", null=True, blank=True)

    def __str__(self):
        return f"Profile of {self.user}"

def get_default_expires_at():
    return timezone.now() + timedelta(minutes=10)


class OTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="otps", null=True, blank=True)
    phone = models.CharField(
        max_length=15,
        help_text="Phone number to send SMS to",
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
            )
        ]
    )
    hashed_code = models.CharField(max_length=255, help_text="Hashed OTP code", blank=True)
    verification_attempts = models.PositiveIntegerField(default=0)
    max_attempts = models.PositiveIntegerField(default=3)
    verification_attempts = models.PositiveIntegerField(default=0)
    max_attempts = models.PositiveIntegerField(default=3)
    purpose = models.CharField(
        max_length=20,
        choices=[
            ("login", "Login"),
            ("register", "Register"),
            ("password_reset", "Password Reset"),
            ("phone_verification", "Phone Verification"),
        ],
        default="login"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=get_default_expires_at)
    is_used = models.BooleanField(default=False)

    def __str__(self):
        return f"OTP for {self.phone} - {self.purpose}"

    def is_expired(self):
        return timezone.now() > self.expires_at

    def increment_attempts(self):
        self.verification_attempts += 1
        self.save(update_fields=['verification_attempts'])
        return self.verification_attempts >= self.max_attempts

    def clean(self):
        if self.phone:
            # Normalize phone: strip to digits and add '+' if missing (assuming international format)
            self.phone = ''.join(filter(str.isdigit, self.phone))
            if not self.phone.startswith('+'):
                self.phone = '+' + self.phone
        super().clean()

    def increment_attempts(self):
        self.verification_attempts += 1
        self.save(update_fields=['verification_attempts'])
        return self.verification_attempts >= self.max_attempts

    def clean(self):
        if self.phone:
            # Normalize phone: strip to digits and add '+' if missing (assuming international format)
            self.phone = ''.join(filter(str.isdigit, self.phone))
            if not self.phone.startswith('+'):
                self.phone = '+' + self.phone
        super().clean()

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "OTP"
        verbose_name_plural = "OTPs"
        indexes = [
            models.Index(fields=['phone', 'purpose', 'is_used']),
            models.Index(fields=['phone', 'purpose', 'expires_at']),
            models.Index(fields=['phone', 'is_used', 'expires_at']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['phone', 'purpose'],
                condition=models.Q(is_used=False),
                name='unique_active_otp_per_phone_purpose'
            ),
        ]
        indexes = [
            models.Index(fields=['phone', 'is_used', 'expires_at']),
        ]

class SMSDevice(Device):
    phone_number = models.CharField(
        max_length=15,
        unique=True,
        help_text="Phone number to send SMS to",
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
            )
        ]
    )
    current_token = models.CharField(max_length=255, blank=True)
    token_timestamp = models.DateTimeField(blank=True, null=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._client = None

    @property
    def client(self):
        if self._client is None and all([
            settings.TWILIO_ACCOUNT_SID,
            settings.TWILIO_AUTH_TOKEN,
            settings.TWILIO_PHONE_NUMBER,
        ]):
            self._client = Client(
                settings.TWILIO_ACCOUNT_SID,
                settings.TWILIO_AUTH_TOKEN,
            )
        return self._client

    def generate_challenge(self):
        """Generate a random token for SMS verification"""
        if not self.configured():
            raise ValueError("Device is not configured")
        
        otp_code = f"{secrets.randbelow(1000000):06d}"
        hashed_code = make_password(otp_code)
        self.current_token = hashed_code
        self.token_timestamp = timezone.now()
        self.save()

        return otp_code

    def send_token(self, token=None):
        """Send the token to the user's phone number"""
        
        logger = logging.getLogger(__name__)

        if token is None:
            token = self.generate_challenge()

        if not self.client:
            return False
        
        try:
            self.client.messages.create(
                body=f"Your verification code is: {token}",
                from_=settings.TWILIO_PHONE_NUMBER,
                to=self.phone_number
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send SMS to {self.phone_number}: {e}")
            return False

    def verify_token(self, token):
        """Verify the token against the current token"""
        # Check if token exists and is recent (within 10 minutes)
        if (self.current_token and
            self.token_timestamp and
            (timezone.now() - self.token_timestamp < timedelta(minutes=10))
        ):
            is_valid = check_password(token, self.current_token)
            if is_valid:
                self.current_token = None
                self.token_timestamp = None
                self.save()
            return is_valid
        return False

    def configured(self):
        return bool(self.phone_number and self.client)
    
    class Meta:
        verbose_name = "SMS Device"
        verbose_name_plural = "SMS Devices"

    def __str__(self):
        return f"SMS Device for {self.phone_number}"
            