# models.py
import uuid
import random
import string

from django.db import models
from django.conf import settings


class Chama(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for the Chama"
    )

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    currency = models.CharField(max_length=10)
    minimum_members = models.IntegerField(default=1)
    maximum_members = models.IntegerField()
    balance = models.DecimalField(
        max_digits=15, decimal_places=2, default=0
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)

    join_code = models.CharField(
        max_length=12,
        unique=True,
        blank=True,
        default='',
        help_text="Auto-generated code for users to join"
    )

    def save(self, *args, **kwargs):
        if not self.join_code:
            self.join_code = self._generate_unique_code()
        super().save(*args, **kwargs)

    def _generate_unique_code(self):
        while True:
            code = ''.join(
                random.choices(string.ascii_uppercase + string.digits, k=8)
            )
            if not Chama.objects.filter(join_code=code).exists():
                return code

    def __str__(self):
        return self.name


class Membership(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for the membership record"
    )

    class Role(models.TextChoices):
        MEMBER = 'member', 'Member'
        ADMIN = 'admin', 'Admin'
        TREASURER = 'treasurer', 'Treasurer'

    class Status(models.TextChoices):
        INVITED = 'invited', 'Invited'
        PENDING = 'pending', 'Pending'
        ACTIVE = 'active', 'Active'
        REMOVED = 'removed', 'Removed'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='memberships'
    )
    chama = models.ForeignKey(
        Chama,
        on_delete=models.CASCADE,
        related_name='members'
    )

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.MEMBER
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    payout_order = models.IntegerField(null=True, blank=True)

    class Meta:
        unique_together = ['user', 'chama']

    def __str__(self):
        return f"{self.user} in {self.chama} as {self.role}"
