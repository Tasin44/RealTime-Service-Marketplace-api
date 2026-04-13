from django.db import models

from serviceproviderapp .models import ProviderProfile
from servicereceiverapp .models import ReceiverProfile
from django.conf import settings

# Create your models here.
# ===========================
# CONVERSATIONS
# ===========================
class Conversation(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('expired', 'Expired'),
    ]

    conversation_id = models.AutoField(primary_key=True)
    receiver = models.ForeignKey(ReceiverProfile, on_delete=models.CASCADE)
    provider = models.ForeignKey(ProviderProfile, on_delete=models.CASCADE)

    conversation_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    expires_at = models.DateTimeField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('receiver', 'provider')

# ===========================
# MESSAGES
# ===========================
class Message(models.Model):
    message_id = models.AutoField(primary_key=True)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    message_text = models.TextField(null=True, blank=True)
    # message_image = models.CharField(max_length=255, null=True, blank=True)
    # message_file = models.CharField(max_length=255, null=True, blank=True)
    message_image = models.ImageField(upload_to="messages/images/", null=True, blank=True)
    message_file = models.FileField(upload_to="messages/files/", null=True, blank=True)
    message_voice = models.CharField(max_length=255, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
        ]





