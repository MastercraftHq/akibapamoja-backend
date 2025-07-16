import uuid
from django.db import models
from django.conf import settings

class Chama(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    contribution_amount = models.DecimalField(max_digits=10, decimal_places=2)
    contribution_frequency = models.CharField(max_length=20)
    contribution_day = models.IntegerField()
    currency = models.CharField(max_length=10)
    late_payment_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    minimum_members = models.IntegerField(default=1)
    maximum_members = models.IntegerField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)
    join_code = models.CharField(max_length=12, unique=True)

    def __str__(self):
        return self.name
    
class Membership(models.Model):
    class Role(models.TextChoices):
        MEMBER = 'member', 'Member'
        ADMIN = 'admin', 'Admin'
        TREASURER = 'treasurer', 'Treasurer'

    class Status(models.TextChoices):
        INVITED = 'invited', 'Invited'
        ACTIVE = 'active', 'Active'
        REMOVED = 'removed', 'Removed'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='memberships')
    chama = models.ForeignKey('Chama', on_delete=models.CASCADE, related_name='members')
    
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.MEMBER
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )

    joined_at = models.DateTimeField(auto_now_add=True)
    payout_order = models.IntegerField(null=True, blank=True)

    class Meta:
        unique_together = ['user', 'chama']

    def __str__(self):
        return f"{self.user} in {self.chama} as {self.role}"
