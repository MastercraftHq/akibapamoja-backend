from django.db import models
from django.utils.text import slugify
from django.contrib.auth import get_user_model
from .enums import MembershipRole, MembershipStatus
import secrets

User = get_user_model()


class Group(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    contribution_amount = models.DecimalField(max_digits=10, decimal_places=2)
    contribution_interval = models.CharField(max_length=50)
    admin = models.ForeignKey(User, on_delete=models.CASCADE, related_name="admin_groups")
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Group.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.slug})"


class Membership(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField(
        max_length=50,
        choices=MembershipRole.choices(),
        default=MembershipRole.MEMBER
    )
    status = models.CharField(
        max_length=20,
        choices=MembershipStatus.choices(),
        default=MembershipStatus.JOINED
    )
    invite_code = models.CharField(max_length=64, unique=True, blank=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("group", "user")
        
    def save(self, *args, **kwargs):
        if not self.invite_code:
            self.invite_code = secrets.token_urlsafe(16)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.email} in {self.group.slug} as {self.role}"
