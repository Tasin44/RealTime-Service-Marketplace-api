from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from .models import User, OTP


class CustomUserCreationForm(UserCreationForm):
	class Meta(UserCreationForm.Meta):
		model = User
		fields = ("username", "email", "name", "role", "verified")


class CustomUserChangeForm(UserChangeForm):
	class Meta(UserChangeForm.Meta):
		model = User
		fields = ("username", "email", "name","verified", "image")


@admin.register(User)
class CustomUserAdmin(UserAdmin):
	add_form = CustomUserCreationForm
	form = CustomUserChangeForm
	model = User

	list_display = ("email", "name", "role", "verified", "is_staff", "is_active")
	list_filter = ("role", "verified", "is_staff", "is_active")
	ordering = ("email",)
	search_fields = ("email", "name", "username")

	fieldsets = (
		(None, {"fields": ("username", "password")}),
		("Personal info", {"fields": ("name", "email", "image")}),
		("Role", {"fields": ("role", "verified")}),
		("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
		("Important dates", {"fields": ("last_login", "date_joined")}),
	)

	add_fieldsets = (
		(None, {
			"classes": ("wide",),
			"fields": ("username", "email", "name", "role", "verified", "password1", "password2"),
		}),
	)


@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
	list_display = ("email", "otp_code", "is_used", "created_at", "expires_at")
	list_filter = ("is_used",)
	search_fields = ("email",)

# Admin UI branding only (no functional changes).
admin.site.site_header = "Chiripa Administration"
admin.site.site_title = "Chiripa Administration"
admin.site.index_title = "Operations Dashboard"
