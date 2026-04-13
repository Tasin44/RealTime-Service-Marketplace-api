from django.db import models
from django.contrib.auth.models import User

from django.conf import settings
# RECEIVER PROFILES
# ===========================
class ReceiverProfile(models.Model):
    receiver_id = models.AutoField(primary_key=True)
    user = models.OneToOneField(settings.AUTH_USER_MODEL
                                , on_delete=models.CASCADE)
    receiver_stripe_account_id = models.CharField(max_length=255, null=True, blank=True)#It'll come dynamically after receiver complete his stripe onboarding

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

