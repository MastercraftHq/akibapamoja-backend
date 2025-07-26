import uuid
import random
import string
from django.db import models
from django.conf import settings
from .enums import (
    MembershipRole,
    MembershipStatus,
    ContributionStatus,
    ContributionFrequency,
)
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError


class Chama(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    currency = models.CharField(max_length=10)
    late_payment_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    minimum_members = models.IntegerField(default=1)
    maximum_members = models.IntegerField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)
    join_code = models.CharField(max_length=12, unique=True, null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.join_code:
            self.join_code = self.generate_unique_code()
        super().save(*args, **kwargs)

    def generate_unique_code(self):
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            if not Chama.objects.filter(join_code=code).exists():
                return code

    def __str__(self):
        return self.name


class Membership(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
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
        choices=MembershipRole.choices(),
        default=MembershipRole.MEMBER.value
    )

    status = models.CharField(
        max_length=20,
        choices=MembershipStatus.choices(),
        default=MembershipStatus.ACTIVE.value
    )

    joined_at = models.DateTimeField(auto_now_add=True)
    payout_order = models.IntegerField(null=True, blank=True)

    class Meta:
        unique_together = ['user', 'chama']
        verbose_name_plural = 'memberships'

    def __str__(self):
        return f"{self.user} in {self.chama} as {self.role}"


class ContributionSchedule(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    chama = models.ForeignKey(
        Chama,
        on_delete=models.CASCADE,
        related_name="chama_contribution_schedules"  # fixed related_name to avoid clash
    )
    name = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])

    frequency = models.CharField(
        max_length=20,
        choices=ContributionFrequency.choices(),
        default=ContributionFrequency.MONTHLY.value
    )

    due_day = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(31)],
        help_text="Day of the period when due (1–31 for monthly, 1–7 for weekly)"
    )

    status = models.CharField(
        max_length=10,
        choices=ContributionStatus.choices(),
        default=ContributionStatus.PENDING.value
    )

    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['chama', 'name']
        ordering = ['start_date']

    def clean(self):
        super().clean()
        if self.frequency == ContributionFrequency.WEEKLY.value and not (1 <= self.due_day <= 7):
            raise ValidationError("Due day must be between 1 and 7 for weekly contributions.")
        if self.frequency == ContributionFrequency.MONTHLY.value and not (1 <= self.due_day <= 31):
            raise ValidationError("Due day must be between 1 and 31 for monthly contributions.")



    def __str__(self):
        return f"{self.chama.name} - {self.name} ({self.frequency} {self.amount})"
