from rest_framework import serializers
from .models import DeviceToken, Notification


class DeviceTokenSerializer(serializers.ModelSerializer):
    device_type = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = DeviceToken
        fields = ["token", "device_type"]


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "notification_type", "title", "body", "data", "is_read", "created_at"]
