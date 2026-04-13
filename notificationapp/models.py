from django.db import models
from django.contrib.auth.models import User

# Create your models here.

# ===========================
# NOTIFICATIONS
# ===========================
class Notification(models.Model):
    notification_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    notification_type = models.CharField(max_length=50)
    title = models.CharField(max_length=255)
    message = models.TextField()

    is_read = models.BooleanField(default=False)
    reference_id = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)



