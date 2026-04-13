from django.urls import path
from .views import (
    SignupView, VerifyOTPView, ResendOTPView, LoginView,
    LogoutView, ForgotPasswordView, ResetPasswordView,ProfileUpdateView,DeleteUserView,MeView
)

urlpatterns = [
    path('signup/', SignupView.as_view(), name='signup'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
    path('resend-otp/', ResendOTPView.as_view(), name='resend-otp'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),
    path('profile/', ProfileUpdateView.as_view(), name='profile'),
    path("delete-account/", DeleteUserView.as_view(), name="delete-account"),
    path("me/", MeView.as_view(), name="me"),

]