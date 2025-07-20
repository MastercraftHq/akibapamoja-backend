import uuid
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin
)
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

    def create_superuser(self, email, phone, password=None, **extra_fields):
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
        phone = models.CharField(max_length=15, unique=True, null=True, blank=True)
        
        is_active = models.BooleanField(default=True)
        is_staff = models.BooleanField(default=False)
        role = models.CharField(
            max_length=20,
            choices=UserRole.choices(),
            default=UserRole.MEMBER.value
        )
        created_at = models.DateTimeField(auto_now_add=True)

        USERNAME_FIELD = 'email'
        REQUIRED_FIELDS = []
        
        objects = UserManager()
        
        def __str__(self):
            return self.email or self.phone or self.name
        
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