# models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.conf import settings
import uuid

class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150, null=True, blank=True)
    image = models.ImageField(upload_to="profile_images/", null=True, blank=True)
    email = models.EmailField(unique=False)
    referral_code = models.CharField(max_length=20, blank=True, null=True)
    verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # Add these two lines
    groups = models.ManyToManyField(
        'auth.Group', related_name='authapp_user_set', blank=True
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='authapp_user_set',
        blank=True
    )
    ROLE_CHOICES = (
        ('admin', 'admin'),
        ('provider', 'provider'),
        ('receiver', 'receiver'),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    class Meta:
        indexes = [
            models.Index(fields=['email', 'verified']),
            models.Index(fields=['verified']),
        ]

    def __str__(self):
        return self.email

class OTP(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(db_index=True)
    otp_code = models.CharField(max_length=6)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()#self.expires_at just means the expiry time stored in that OTP object in signup serializer
    
    class Meta:
        indexes = [
            models.Index(fields=['email', 'is_used']),
        ]
    
    def is_valid(self):
        return not self.is_used and timezone.now() < self.expires_at
    
    def __str__(self):
        return f"{self.email} - {self.otp_code}"
    
# class ProfileImage(models.Model):
#     user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
#     image = models.ImageField(upload_to="profile_images/", null=True, blank=True)


