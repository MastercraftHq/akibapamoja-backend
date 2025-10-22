from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import MinValueValidator
from chama.models import Chama
from decimal import Decimal
import uuid

User = get_user_model()

class ContributionSchedule(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('OVERDUE', 'Overdue'),
        ('PARTIAL', 'Partial Paid'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    chama = models.ForeignKey(Chama, on_delete=models.CASCADE, related_name="contribution_schedules")
    due_date = models.DateField()
    expected_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'contribution_schedule'
        unique_together = ['chama', 'due_date']
        indexes = [
            models.Index(fields=['due_date', 'status']),
            models.Index(fields=['chama', 'due_date']),
        ]
        
    def __str__(self):
        return f"{self.chama.name} - {self.due_date} - {self.expected_amount} ({self.status})"

class Contribution(models.Model):
    class PaymentMethod(models.TextChoices):
        MPESA = "MPESA", "M‑Pesa"
        BANK  = "BANK",  "Bank Transfer"
        CASH  = "CASH",  "Cash"
    
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SUCCESS = "APPROVED", "Approved"
        FAILED = "DECLINED", "Declined"
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member    = models.ForeignKey('chama.Membership', on_delete=models.CASCADE, related_name="contributions", null=True)
    chama     = models.ForeignKey(Chama, on_delete=models.CASCADE, related_name="contributions")
    schedule  = models.ForeignKey(ContributionSchedule, on_delete=models.CASCADE, related_name="contributions", null=True)
    contribution_cycle = models.ForeignKey('ContributionCycle', on_delete=models.SET_NULL, null=True, blank=True, related_name="contributions")
    amount    = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    method    = models.CharField(max_length=10, choices=PaymentMethod.choices, default=PaymentMethod.MPESA)
    status    = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    transaction_date = models.DateTimeField(default=timezone.now)
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="recorded_contributions")
    is_confirmed = models.BooleanField(default=False)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    reference = models.CharField(max_length=60, blank=True)
    notes     = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'contribution'
        indexes = [
            models.Index(fields=['chama', 'transaction_date']),
            models.Index(fields=['member', 'transaction_date']),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        member_name = self.member.user.username if self.member else "Unknown"
        return f"{member_name} - {self.chama.name} - {self.amount} ({self.method}) on {self.transaction_date}"

class ActivityLog(models.Model):
    ACTION_CHOICES = [
        ('CONTRIBUTION', 'Contribution'),
        ('LOAN', 'Loan'),
        ('WITHDRAWAL', 'Withdrawal'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user       = models.ForeignKey(User, on_delete=models.CASCADE)
    chama      = models.ForeignKey(Chama, on_delete=models.CASCADE)
    action     = models.CharField(max_length=20, choices=ACTION_CHOICES)
    details    = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.action}] {self.details}"
    
class ContributionCycle(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    chama = models.ForeignKey(Chama, on_delete=models.CASCADE, related_name="contribution_cycles")
    cycle_number = models.PositiveIntegerField()
    start_date = models.DateField()
    end_date = models.DateField()
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
