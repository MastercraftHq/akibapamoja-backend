import uuid
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

from chama.models import Chama, Membership

User = get_user_model()


# -----------------------------
# Contribution Cycle (Operational)
# -----------------------------
class ContributionCycle(models.Model):
    """
    Operational cycle for a chama (e.g., Jan 2025 - Mar 2025).
    Includes frequency rules for schedule generation.
    """

    class Frequency(models.TextChoices):
        WEEKLY = "WEEKLY", "Weekly"
        MONTHLY = "MONTHLY", "Monthly"
        QUARTERLY = "QUARTERLY", "Quarterly"
        YEARLY = "YEARLY", "Yearly"
        CUSTOM = "CUSTOM", "Custom"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    chama = models.ForeignKey(Chama, on_delete=models.CASCADE, related_name="contribution_cycles", null=True, blank=True)
    cycle_number = models.PositiveIntegerField(help_text="Sequential cycle number for this chama", null=True, blank=True)
    name = models.CharField(max_length=100, null=True, blank=True)
    frequency = models.CharField(max_length=10, choices=Frequency.choices, null=True, blank=True)
    custom_days = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Required if frequency is CUSTOM (number of days between contributions)"
    )
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'contribution_cycle'
        unique_together = ['chama', 'cycle_number']
        indexes = [
            models.Index(fields=['chama', 'start_date']),
            models.Index(fields=['is_completed']),
        ]
        ordering = ['-start_date']

    def clean(self):
        if self.frequency == self.Frequency.CUSTOM and not self.custom_days:
            raise ValidationError("Custom frequency requires custom_days to be set.")
        if self.frequency != self.Frequency.CUSTOM and self.custom_days:
            raise ValidationError("custom_days should only be set for CUSTOM frequency.")

    @property
    def expected_total(self):
        active_members = self.chama.members.filter(status='active').count()
        amount_per_schedule = self.chama.contribution_amount
        return active_members * amount_per_schedule

    @property
    def collected_total(self):
        return self.contributions.aggregate(total=models.Sum('amount'))['total'] or 0.00

    def __str__(self):
        return f"{self.chama.name} - Cycle {self.cycle_number} ({self.start_date} to {self.end_date})"


# -----------------------------
# Contribution Schedule
# -----------------------------
class ContributionSchedule(models.Model):
    """
    A due date & expected amount for contributions within a cycle.
    Tracks payment status for operational visibility.
    """

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('OVERDUE', 'Overdue'),
        ('PARTIAL', 'Partial Paid'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    chama = models.ForeignKey(Chama, on_delete=models.CASCADE, related_name='schedules')
    cycle = models.ForeignKey(
        ContributionCycle,
        on_delete=models.CASCADE,
        related_name='schedules',
        null=True,
        blank=True,
    )
    due_date = models.DateField()
    expected_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.01)]
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'contribution_schedule'
        unique_together = [('chama', 'due_date')]
        indexes = [
            models.Index(fields=['chama', 'due_date']),
            models.Index(fields=['due_date', 'status']),
        ]

    def __str__(self):
        return f"{self.chama.name} | Due {self.due_date} → {self.expected_amount} ({self.status})"


# -----------------------------
# Contribution
# -----------------------------
class Contribution(models.Model):
    """
    An individual member's payment (manual or M-Pesa).
    Includes audit fields & confirmation.
    """

    class PaymentMethod(models.TextChoices):
        MPESA = "MPESA", "M-Pesa"
        BANK = "BANK", "Bank Transfer"
        CASH = "CASH", "Cash"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    schedule = models.ForeignKey(ContributionSchedule, on_delete=models.CASCADE, related_name='contributions')
    member = models.ForeignKey(Membership, on_delete=models.CASCADE, related_name='contributions')
    chama = models.ForeignKey(Chama, on_delete=models.CASCADE, related_name="contributions", null=True, blank=True)
    cycle = models.ForeignKey(ContributionCycle, on_delete=models.CASCADE, related_name="contributions", null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    method = models.CharField(max_length=10, choices=PaymentMethod.choices, default=PaymentMethod.CASH)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    reference = models.CharField(max_length=100, blank=True, unique=True)
    transaction_date = models.DateTimeField(default=timezone.now)
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="recorded_contributions")
    is_confirmed = models.BooleanField(default=False)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'contribution'
        indexes = [
            models.Index(fields=['schedule', 'transaction_date']),
            models.Index(fields=['member', 'transaction_date']),
        ]
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if (
            self.status == self.Status.APPROVED
            and not self.reference
            and self.method != Contribution.PaymentMethod.CASH
        ):
            raise ValueError("Approved non-cash contributions require a reference.")
        super().save(*args, **kwargs)

    def __str__(self):
        user = self.member.user.username
        return f"{user} → {self.chama.name} | {self.amount} via {self.method}"


# -----------------------------
# Activity Log
# -----------------------------
class ActivityLog(models.Model):
    ACTION_CHOICES = [
        ('CONTRIBUTION', 'Contribution'),
        ('LOAN', 'Loan'),
        ('WITHDRAWAL', 'Withdrawal'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    chama = models.ForeignKey(Chama, on_delete=models.CASCADE, null=True, blank=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    details = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'activity_log'
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.action}] {self.details}"
