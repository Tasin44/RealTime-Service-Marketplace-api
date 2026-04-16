# serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta
import random
import string
import resend
from .models import OTP
from .utils import validate_and_get_otp
from servicereceiverapp.models import ReceiverProfile
from django.conf import settings

resend.api_key = settings.RESEND_API_KEY

User = get_user_model()

print(settings.RESEND_API_KEY)
class SignupSerializer(serializers.Serializer):
    email = serializers.EmailField()
    # name = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, min_length=8)
    name = serializers.CharField(required=True)
    referral_code = serializers.CharField(max_length=20, required=False, allow_blank=True)
    
    def validate_email(self, value):
        value = value.lower().strip()#makes email lowercase and removes spaces.
        verified_user = User.objects.filter(email=value, verified=True).exists()#.filter() returns a QuerySet, not a True/False value.
        #.exists() is used to check if any record matches (returns True or False).

        if verified_user:
            raise serializers.ValidationError("This email is already registered.")
        return value
    
    
    def create(self, validated_data):
        email = validated_data['email']
        name = validated_data.get("name", "").strip()
        # It removes old unverified accounts with the same email before creating a new one.
        User.objects.filter(email=email, verified=False).delete()
        
        # Create new user
        user = User.objects.create_user(
            # username=email,
            username=email,  # previously it was email
            email=email,
            # first_name=validated_data['name'],
            password=validated_data['password'],
            referral_code=validated_data.get('referral_code') or None,
            verified=False,
            name=name
        )
        
        # Generate and send OTP
        otp_code = ''.join(random.choices(string.digits, k=6))
        '''
        Generates a 6-digit random OTP made of numbers.
        string.digits = '0123456789'
        random.choices(..., k=6) → picks 6 random digits.
        .join(...) → combines them into a single string like '483920'.
        '''
        expires_at = timezone.now() + timedelta(minutes=10)

        #Deletes any previous unused OTPs for that email before sending a new on
        OTP.objects.filter(email=email, is_used=False).delete()
        OTP.objects.create(
            email=email,
            otp_code=otp_code,
            expires_at=expires_at
        )
        
        self.send_otp_email(email, otp_code)
        user.role = "receiver"
        user.save(update_fields=["role"])

        ReceiverProfile.objects.create(user=user)
        return user

    '''
    @staticmethod
    def send_otp_email(email, otp_code):
        subject = "Your OTP Code for Verification in Chiripa"
        message = f"Your OTP code is: {otp_code}\nValid for 10 minutes."
        send_mail(subject, message, 'noreply@yourdomain.com', [email])
    '''

    @staticmethod
    def send_otp_email(email, otp_code):
        try:
            resend.Emails.send({
                "from": "onboarding@resend.dev",  # must be verified domain in Resend
                "to": [email],
                "subject": "Your OTP Code for Verification in Chiripa",
                "html": f"""
                    <div style="font-family: Arial; padding: 20px;">
                        <h2>OTP Verification</h2>
                        <p>Your OTP code is:</p>
                        <h1 style="letter-spacing: 5px;">{otp_code}</h1>
                        <p>This code is valid for 10 minutes.</p>
                    </div>
                """
            })
        except Exception as e:
            print("Resend email error:", str(e))

class VerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp_code = serializers.CharField(max_length=6)
    
    def validate(self, data):
        email = data['email'].lower().strip()
        otp_code = data['otp_code'].strip()
        

        otp = validate_and_get_otp(email, otp_code) 

        data['otp'] = otp
        return data


class ResendOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    
    def validate_email(self, value):
        value = value.lower().strip()
        user = User.objects.filter(email=value, verified=False).exists()
        if not user:
            raise serializers.ValidationError("No pending verification for this email.")
        return value


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, data):
        email = data['email'].lower().strip()
        password = data['password']
        
        try:
            user = User.objects.get(email=email, verified=True)
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid email")
        
        if not user.check_password(password):#if the password enterd by the user is not correct 
            raise serializers.ValidationError("Invalid password.")
        
        data['user'] = user
        return data


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    
    def validate_email(self, value):
        value = value.lower().strip()
        user = User.objects.filter(email=value, verified=True).exists()
        if not user:
            raise serializers.ValidationError("Email not found or not verified.")
        return value


class ResetPasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True, min_length=8)
    


class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["name", "image"]


class ConfirmDeleteUserSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True)

    def validate_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Incorrect password.")
        return value



class MeSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "name", "image", "role", "verified"]

    def get_image(self, obj):
        if not obj.image:
            return None
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.image.url)
        return f"{settings.BASE_URL.rstrip('/')}{obj.image.url}"
