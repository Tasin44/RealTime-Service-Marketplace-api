# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import random
import string
from .serializers import (
    SignupSerializer, VerifyOTPSerializer, ResendOTPSerializer,
    LoginSerializer, ForgotPasswordSerializer, ResetPasswordSerializer,ProfileUpdateSerializer,ConfirmDeleteUserSerializer,MeSerializer
)
from .models import OTP
from rest_framework.parsers import MultiPartParser, FormParser

User = get_user_model()
from rest_framework import status

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


class SignupView(StandardResponseMixin, APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            
            return self.success_response(
                data={
                    "email": user.email,
                    "name": user.name,
                },
                message="User created. OTP sent to email.",
                status_code=201
            )
        return self.error_response(
            "Signup failed",
            status_code=400,
            data=serializer.errors
        )


class VerifyOTPView(StandardResponseMixin, APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        if serializer.is_valid():
            otp = serializer.validated_data['otp']
            user = User.objects.get(email=otp.email)
            
            user.verified = True
            user.save(update_fields=['verified', 'updated_at'])
            
            otp.is_used = True
            otp.save(update_fields=['is_used'])
            
            refresh = RefreshToken.for_user(user)
            return self.success_response(
                {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                    "user": {
                        "id": str(user.id),
                        "email": user.email,
                        "name": user.name
                    }
                },
                message="Email verified successfully.",
                status_code=200
            )
        return self.error_response(
            "Verification failed",
            status_code=400,
            data=serializer.errors
        )


class ResendOTPView(StandardResponseMixin, APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = ResendOTPSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            
            otp_code = ''.join(random.choices(string.digits, k=6))
            expires_at = timezone.now() + timedelta(minutes=10)
            
            OTP.objects.filter(email=email, is_used=False).delete()
            OTP.objects.create(
                email=email,
                otp_code=otp_code,
                expires_at=expires_at
            )
            
            SignupSerializer.send_otp_email(email, otp_code)
            
            return self.success_response(
                {"email": email},
                message="OTP sent to email.",
                status_code=200
            )
        return self.error_response(
            "Resend OTP failed",
            status_code=400,
            data=serializer.errors
        )


class LoginView(StandardResponseMixin, APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            refresh = RefreshToken.for_user(user)
            
            return self.success_response(
                {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                    "user": {
                        "id": str(user.id),
                        "email": user.email,
                        "name": user.name
                    }
                },
                message="Login successful.",
                status_code=200
            )
        return self.error_response(
            "Login failed",
            status_code=401,
            data=serializer.errors
        )


class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            print("Request data:", request.data)
            if not refresh_token:
                return Response(
                    {f"detail": "Refresh token is required.{refresh_token}"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            token = RefreshToken(refresh_token)
            token.blacklist()

            return Response({"message": "Logout successful."}, status=status.HTTP_200_OK)
        except TokenError:
            return Response({"detail": "Invalid or expired token."}, status=status.HTTP_400_BAD_REQUEST)


class ForgotPasswordView(StandardResponseMixin, APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            
            otp_code = ''.join(random.choices(string.digits, k=6))
            expires_at = timezone.now() + timedelta(minutes=10)
            
            OTP.objects.filter(email=email, is_used=False).delete()
            OTP.objects.create(
                email=email,
                otp_code=otp_code,
                expires_at=expires_at
            )
            
            SignupSerializer.send_otp_email(email, otp_code)
            
            return self.success_response(
                {"email": email},
                message="OTP sent to email for password reset.",
                status_code=200
            )
        return self.error_response(
            "Forgot password failed",
            status_code=400,
            data=serializer.errors
        )


class ResetPasswordView(StandardResponseMixin, APIView):
    permission_classes = [IsAuthenticated]  # user must be logged in via OTP verify token
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user  # authenticated via token from VerifyOTPView
            new_password = serializer.validated_data['new_password']

            user.set_password(new_password)
            user.save(update_fields=['password', 'updated_at'])

            return self.success_response(
                {},
                message="Password reset successful.",
                status_code=200
            )
        return self.error_response(
            "Password reset failed",
            status_code=400,
            data=serializer.errors
        )
    


class ProfileUpdateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def patch(self, request):
        serializer = ProfileUpdateSerializer(
            request.user, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Profile updated"})
        return Response(serializer.errors, status=400)


class DeleteUserView(StandardResponseMixin, APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        serializer = ConfirmDeleteUserSerializer(
            data=request.data,
            context={"request": request}
        )

        if not serializer.is_valid():
            return self.error_response(
                "Password verification failed",
                data=serializer.errors,
                status_code=400
            )

        request.user.delete()
        return self.success_response(
            message="Your account has been deleted successfully.",
            status_code=200,
            data=None
        )



class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = MeSerializer(request.user)
        return Response(serializer.data, status=200)

    def delete(self, request):
        password = request.data.get("password")
        if not password:
            return Response({"message": "Password is required."}, status=400)
        if not request.user.check_password(password):
            return Response({"message": "Incorrect password."}, status=400)
        request.user.delete()
        return Response({"message": "Account deleted successfully."}, status=200)




from servicereceiverapp.models import ReceiverProfile
from serviceproviderapp.models import ProviderProfile

class ProviderProfileStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        #profile_done=False
        # if ProviderProfile.provider_profile_setup_done:
        profile_done = ProviderProfile.objects.filter(user=request.user).exists()
            #profile_done = True
        return Response({
            "provider_profile_setup_done": profile_done,
            "current_mode": request.user.role
        }, status=200)

class SwitchUserModeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        target_mode = (request.data.get("mode") or "").strip().lower()
        if target_mode not in ["provider", "receiver"]:
            return Response({"error": "mode must be provider or receiver"}, status=400)

        if request.user.role == target_mode:
            profile_done = ProviderProfile.objects.filter(user=request.user).exists()
            return Response({
                "message": "Mode unchanged",
                "role": request.user.role,
                "provider_profile_setup_done": profile_done
            }, status=200)

        if target_mode == "provider":
            profile_done = ProviderProfile.objects.filter(user=request.user).exists()
            if not profile_done:
                return Response(
                    {
                        #"error": "Provider profile is not set up yet",
                        "provider_profile_setup_done": False
                    },
                    status=200
                )

        if target_mode == "receiver":
            ReceiverProfile.objects.get_or_create(user=request.user)

        request.user.role = target_mode
        request.user.save(update_fields=["role", "updated_at"])

        profile_done = ProviderProfile.objects.filter(user=request.user).exists()
        return Response({
            "message": "Mode switched successfully",
            "role": request.user.role,
            "provider_profile_setup_done": profile_done
        }, status=200)












