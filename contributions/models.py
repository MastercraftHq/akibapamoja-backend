import uuid
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError

from chama.models import Membership

class ContributionCycle(models.Model):
    """
    Defines the frequency of contributions (e.g., weekly, monthly).
    """
    class Frequency(models.TextChoices):
        WEEKLY = "WEEKLY", "Weekly"
        MONTHLY = "MONTHLY", "Monthly"
        QUARTERLY = "QUARTERLY", "Quarterly"
        YEARLY = "YEARLY", "Yearly"
        CUSTOM = "CUSTOM", "Custom"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    frequency = models.CharField(max_length=10, choices=Frequency.choices)
    custom_days = models.PositiveIntegerField(
        null=True, 
        blank=True,
        help_text="Required if frequency is CUSTOM (number of days between contributions)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'contribution_cycle'
        ordering = ['name']

    def clean(self):
        if self.frequency == self.Frequency.CUSTOM and not self.custom_days:
            raise ValidationError("Custom frequency requires custom_days to be set.")
        if self.frequency != self.Frequency.CUSTOM and self.custom_days:
            raise ValidationError("custom_days should only be set for CUSTOM frequency.")

    def __str__(self):
        return f"{self.name} ({self.get_frequency_display()})"



class ContributionSchedule(models.Model):
    """
    Defines when and how much members should pay each period.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    chama = models.ForeignKey('chama.Chama', on_delete=models.CASCADE, related_name='schedules')
    cycle = models.ForeignKey(
        'ContributionCycle',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='schedules'
    )
    due_date = models.DateField()
    expected_amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'contribution_schedule'
        unique_together = [('chama', 'due_date')]
        indexes = [
            models.Index(fields=['chama', 'due_date']),
            models.Index(fields=['due_date']),
        ]

    def __str__(self):
        return f"{self.chama.name} due {self.due_date} → {self.expected_amount}"


class Contribution(models.Model):
    """
    Records an individual member's payment (manual or M-Pesa).
    """
    class PaymentMethod(models.TextChoices):
        MPESA = "MPESA", "M-Pesa"
        BANK  = "BANK",  "Bank Transfer"
        CASH  = "CASH",  "Cash"

    class Status(models.TextChoices):
        PENDING  = "PENDING",  "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    id               = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    schedule         = models.ForeignKey(ContributionSchedule, on_delete=models.CASCADE, related_name='contributions')
    member           = models.ForeignKey(Membership, on_delete=models.CASCADE, related_name='contributions')
    amount           = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    method           = models.CharField(max_length=10, choices=PaymentMethod.choices, default=PaymentMethod.CASH)
    status           = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    reference        = models.CharField(max_length=100, blank=True, unique=True)
    transaction_date = models.DateTimeField(default=timezone.now)
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'contribution'
        indexes  = [
            models.Index(fields=['schedule', 'transaction_date']),
            models.Index(fields=['member',   'transaction_date']),
        ]
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        # auto-confirm on APPROVED if reference exists
        # only require a reference on APPROVED for non-manual payments
        if (
            self.status == self.Status.APPROVED
            and not self.reference
            and self.method != Contribution.PaymentMethod.CASH
        ):
            raise ValueError("Approved contributions require a reference.")
        super().save(*args, **kwargs)

    def __str__(self):
        user  = self.member.user.username
        name  = self.schedule.chama.name
        return f"{user} → {name} | {self.amount} via {self.method}"
