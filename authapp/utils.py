# utils.py
from django.core.exceptions import ValidationError
from .models import OTP

def validate_and_get_otp(email, otp_code):
    try:
        otp = OTP.objects.filter(email=email, is_used=False).latest('created_at')
    except OTP.DoesNotExist:
        raise ValidationError("No valid OTP found for this email.")

    if not otp.is_valid():
        raise ValidationError("OTP has expired.")
    if otp.otp_code != otp_code:
        raise ValidationError("Invalid OTP code.")
    return otp