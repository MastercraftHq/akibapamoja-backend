from django.db import models
from django.contrib.auth.models import AbstractUser


# Custom user model (replaces Django's default User)
class CustomUser(AbstractUser):

    ADMIN = 'Admin'
    USER = 'User'

    ROLE_CHOICES = [
        (ADMIN, 'Admin'),
        (USER, 'user'),
    ]

    phone_number = models.CharField(max_length=13, blank=True)
    #national_id = models.CharField(max_length=12, blank=True)
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default='user',
    )

    def __str__(self):
        return f"{self.username} ({self.role})"
    
class UserProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"


