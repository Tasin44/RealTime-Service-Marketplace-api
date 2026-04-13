from rest_framework import serializers
from .models import ReceiverProfile
from serviceproviderapp.serializers import UserSerializer


class ReceiverProfileSerializer(serializers.ModelSerializer):
    """Serializer for ReceiverProfile. Simple, as most fields from User."""
    user = UserSerializer(read_only=True)

    class Meta:
        model = ReceiverProfile
        fields = ['receiver_id', 'user', 'receiver_stripe_account_id', 'created_at', 'updated_at']
        read_only_fields = ['receiver_id', 'user', 'created_at', 'updated_at']




        