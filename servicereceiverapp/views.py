from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from .models import ReceiverProfile
from .serializers import ReceiverProfileSerializer
from rest_framework.exceptions import ValidationError

# Create your views here.

class StandardPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class StandardResponseMixin:
    """Mixin for consistent API responses"""

    def success_response(self, data, message="Success", status_code=200):
        return Response({
            "success": True,
            "statusCode": status_code,
            "message": message,
            "data": data,
            # "timestamp": timezone.now().isoformat()
        }, status=status_code)

    def error_response(self, message, status_code=400, data=None):
        detail = self._extract_error_detail(data)
        if detail and detail not in message:
            message = f"{message}: {detail}"
        return Response({
            "success": False,
            "statusCode": status_code,
            "message": message,
            "data": data,
            # "timestamp": timezone.now().isoformat()
        }, status=status_code)

    def _extract_error_detail(self, data):
        if not data:
            return None
        if isinstance(data, str):
            return data
        if isinstance(data, list) and data:
            return self._extract_error_detail(data[0])
        if isinstance(data, dict):
            if "non_field_errors" in data:
                return self._extract_error_detail(data["non_field_errors"])
            for value in data.values():
                detail = self._extract_error_detail(value)
                if detail:
                    return detail
        return None


class ReceiverProfileViewSet(StandardResponseMixin,viewsets.ModelViewSet):
    """Simple ViewSet for ReceiverProfile.
    Why: One-to-one with User; create on signup."""
    queryset = ReceiverProfile.objects.select_related('user')
    serializer_class = ReceiverProfileSerializer
    pagination_class = StandardPagination
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        if ReceiverProfile.objects.filter(user=self.request.user).exists():
            raise ValidationError({
                "receiver_profile": "Receiver profile already exists for this user."
        })
        serializer.save(user=self.request.user)



