from django.db import models
from users.models import CustomUser
import uuid

# Create your models here.
class Notifications(models.Model):
    """
Represents a notification sent to a user via various channels.

Stores notification type, content, delivery channel, language, status, and metadata.
Ensures uniqueness per user, type, channel, language, and sent time.
"""
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
    
    LANGUAGES = [
        ('en', 'English'),
        ('sw', 'Swahili'),
    ]
    
    id = models.AutoField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=25, choices=TYPE_CHOICES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    channel = models.CharField(max_length=25, choices=CHANNEL_CHOICES)
    is_sent = models.BooleanField(default=False)
    language = models.CharField(max_length=5, choices=LANGUAGES, default='en')
    sent_at = models.DateTimeField(null=True, blank=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'notification_type', 'channel', 'language', 'sent_at']
        
    def __str__(self):
        return f"{self.user.username} - {self.notification_type} - {self.channel} - {self.language}"
    
class NotificationPreference(models.Model):
    """
Represents a user's notification preferences for a specific event type, including delivery channels, frequency, quiet hours, and timezone settings. Ensures each user-event_type pair is unique.
"""
    FREQUENCY_CHOICES = [
        ('IMMEDIATE', 'Immediate'),
        ('DAILY', 'Daily'),
        ('WEEKLY', 'Weekly'),
        ('MONTHLY', 'Monthly'),
        ('NEVER', 'Never'),
    ]
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='notification_preferences')
    event_type = models.CharField(max_length=50,)
    sms_enabled = models.BooleanField(default=False)
    email_enabled = models.BooleanField(default=False)
    push_notification_enabled = models.BooleanField(default=False)
    in_app_notification_enabled = models.BooleanField(default=False)
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES, default='IMMEDIATE')
    quiet_hours_start = models.TimeField(null=True, blank=True)
    quiet_hours_end = models.TimeField(null=True, blank=True)
    timezone = models.CharField(max_length=50, default='EAT')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'event_type']
        
    def __str__(self):
        return f"{self.user.username} - {self.event_type} Preferences"
    
class NotificationSchedule(models.Model):
    """
Represents a scheduled notification event, including its recipients, context data, status, scheduling and sending times, retry logic, and error tracking.
"""

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('SENT', 'Sent'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    id = models.AutoField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type = models.CharField(max_length=50)
    recipients = models.JSONField(default=list, blank=True)
    context_data = models.JSONField(default=dict)
    scheduled_at = models.DateTimeField()
    sent_at = models.DateTimeField(null=True, blank=True)
    retry_count = models.PositiveIntegerField(default=0)
    max_retries = models.PositiveIntegerField(default=3)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default='PENDING')
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-scheduled_at']
    
    def __str__(self):
        return f"{self.event_type} - {self.status} - {self.scheduled_at.strftime('%Y-%m-%d %H:%M:%S')}"
    
class NotificationDelivery(models.Model):
    """
Tracks the delivery status and metadata of notifications sent via various channels and providers.

Includes fields for delivery status, provider details, timestamps for delivery events, error messages, and retry count.
Ensures uniqueness per notification, channel, provider, and provider message ID.
"""
    STATUS_CHOICES = [
        ('QUEUED', 'Queued'),
        ('SENDING', 'Sending'),
        ('DELIVERED', 'Delivered'),
        ('FAILED', 'Failed'),
        ('BOUNCED', 'Bounced'),
        ('CLICKED', 'Clicked'),
        ('OPENED', 'Opened'),
        ('UNSUBSCRIBED', 'Unsubscribed'),
    ]
    
    id = models.AutoField(primary_key=True, default=uuid.uuid4, editable=False)
    notification = models.ForeignKey(Notifications, on_delete=models.CASCADE, related_name='deliveries')
    channel = models.CharField(max_length=10)
    provider = models.CharField(max_length=50) # e.g., 'Africas_Talking', 'SendGrid'
    provider_message_id = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default='QUEUED')
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    opened_at = models.DateTimeField(null=True, blank=True)
    clicked_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    retry_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['notification', 'channel', 'provider', 'provider_message_id']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.notification.user.username} - {self.channel} - {self.status} - {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}"