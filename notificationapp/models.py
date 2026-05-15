from django.db import models
from django.conf import settings


class DeviceToken(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="device_tokens")
    token = models.CharField(max_length=255, unique=True)
    device_type = models.CharField(max_length=10, choices=[("ios", "iOS"), ("android", "Android")], blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["user", "token"]


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ("conversation_accepted", "Conversation Accepted"),
        ("conversation_declined", "Conversation Declined"),
        ("quotation_accepted", "Quotation Accepted"),
        ("quotation_declined", "Quotation Declined"),
        ("order_paid", "Order Paid"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=255)
    body = models.TextField()
    data = models.JSONField(default=dict)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]



