from django.db import models
from users.models import CustomUser
import uuid

# Create your models here.
class Notifications(models.Model):
    TYPE_CHOICES = [
        ('CONTRIBUTION_DUE', 'Contribution Due'),
        ('CONTRIBUTION_RECEIVED', 'Contribution Received'),
        ('PAYOUT_RECEIVED', 'Payout Received'),
        ('GOAL_PROGRESS', 'Goal Progress'),
        ('GOAL_COMPLETED', 'Goal Completed'),
        ('MEMBERSHIP_UPDATE', 'Membership Update'),
    ]
    
    CHANNEL_CHOICES = [
        ('EMAIL', 'Email'),
        ('SMS', 'SMS'),
        ('PUSH_NOTIFICATION', 'Push Notification'),
        ('IN_APP', 'In-App Notification'),
    ]
    
    id = models.AutoField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    is_sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)