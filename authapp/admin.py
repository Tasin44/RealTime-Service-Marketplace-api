from django.contrib import admin
from .models import User,OTP
# Register your models here.
admin.site.register(User)
admin.site.register(OTP)

# Admin UI branding only (no functional changes).
admin.site.site_header = "Chiripa Administration"
admin.site.site_title = "Chiripa Administration"
admin.site.index_title = "Operations Dashboard"
