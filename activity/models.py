from django.db import models
from django.contrib.auth import get_user_model
from chama.models import Chama
User = get_user_model()

class ActivityLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activity_activity_logs')
    chama = models.ForeignKey(Chama, on_delete=models.CASCADE, related_name='activity_activity_logs')
   # action = models.TextField()
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.message[:50]}"
