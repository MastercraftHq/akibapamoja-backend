from django.db import models
from django.contrib.auth import get_user_model
from chama.models import Chama

User = get_user_model()

class Contribution(models.Model):
    class PaymentMethod(models.TextChoices):
        MPESA = "MPESA", "M‑Pesa"
        BANK  = "BANK",  "Bank Transfer"
        CASH  = "CASH",  "Cash"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SUCCESS = "SUCCESS", "Success"
        FAILED  = "FAILED",  "Failed"

    user      = models.ForeignKey(User, on_delete=models.CASCADE, related_name="contributions")
    chama     = models.ForeignKey(Chama, on_delete=models.CASCADE, related_name="contributions")
    amount    = models.DecimalField(max_digits=10, decimal_places=2)
    method    = models.CharField(max_length=10, choices=PaymentMethod.choices, default=PaymentMethod.MPESA)
    reference = models.CharField(max_length=60, blank=True)
    status    = models.CharField(max_length=10, choices=Status.choices, default=Status.SUCCESS)
    notes     = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.chama.name}: {self.user} → {self.amount}"

class ActivityLog(models.Model):
    ACTION_CHOICES = [
        ('CONTRIBUTION', 'Contribution'),
        ('LOAN', 'Loan'),
        ('WITHDRAWAL', 'Withdrawal'),
    ]
    user       = models.ForeignKey(User, on_delete=models.CASCADE)
    chama      = models.ForeignKey(Chama, on_delete=models.CASCADE)
    action     = models.CharField(max_length=20, choices=ACTION_CHOICES)
    details    = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.action}] {self.details}"