from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
import uuid
class ServiceCategory(models.Model):
    # category_id = models.IntegerField(primary_key=True)
    category_name = models.CharField(max_length=100, unique=True)
    category_image = models.ImageField(upload_to="category_images/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.category_name


class ProviderProfile(models.Model):
    # provider_id = models.IntegerField(primary_key=True)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    service_category = models.ForeignKey(ServiceCategory, on_delete=models.RESTRICT)

    service_title = models.CharField(max_length=255, null=True, blank=True)
    provider_description = models.TextField(null=True, blank=True)#entered by provider manually
    provider_experience = models.IntegerField(null=True, blank=True)#entered by provider manually
    provider_done_work = models.IntegerField(default=0)#From this app:how many works done on this app
    provider_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)#From this app: how much rating got from this app
    provider_service_charge = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)#Per Hour service charge - entered by provider manually

    provider_language = models.CharField(max_length=255, null=True, blank=True)#entered by provider manually
    # provider_location = models.CharField(max_length=255, null=True, blank=True)
    provider_licence_number = models.CharField(max_length=100, null=True, blank=True)#entered by provider manually
    provider_country = models.CharField(max_length=100, null=True, blank=True)#entered by provider manually
    provider_city = models.CharField(max_length=100, null=True, blank=True)#entered by provider manually
    provider_service_area = models.TextField(null=True, blank=True)#entered by provider manually
    #new
    provider_state = models.CharField(max_length=100, null=True, blank=True)
    provider_zip_code = models.CharField(max_length=20, null=True, blank=True)

    provider_profile_setup_done=models.BooleanField(default=False)


    provider_total_hired = models.IntegerField(default=0)#From this app
    provider_total_earnings = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)#From this app
    provider_available_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)#From this app

    provider_stripe_account_id = models.CharField(max_length=255, null=True, blank=True)

    #Newly added for stripe connect-24th Dec-----------------------------------------------\
    stripe_connected = models.BooleanField(default=False)
    stripe_connection_date = models.DateTimeField(null=True, blank=True)
    #--------------------------------------------------------------------------------------/
    provider_is_verified = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Provider: {self.user.email}"


# ===========================
# PROVIDER KEYWORDS
# ===========================
class ProviderKeyword(models.Model):#entered by provider manually
    id = models.AutoField(primary_key=True)
    provider = models.ForeignKey(ProviderProfile, on_delete=models.CASCADE)
    keyword = models.CharField(max_length=100)

    def __str__(self):
        return self.keyword



class ProviderWorkImage(models.Model):#entered by provider manually
    id = models.BigAutoField(primary_key=True)
    provider = models.ForeignKey(ProviderProfile, on_delete=models.CASCADE, related_name='work_images')
    image = models.ImageField(upload_to='provider_work_images/')
    created_at = models.DateTimeField(auto_now_add=True)


# ===========================
# PROVIDER DOCUMENTS
# ===========================
class ProviderDocument(models.Model):#entered by provider manually
    DOCUMENT_TYPE_CHOICES = [
        ("passport", "Passport"),
        ("national_id", "National ID Card"),
        ("driving_licence", "Driving Licence"),
    ]    
    # document_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.ForeignKey(ProviderProfile, on_delete=models.CASCADE)
    document_type = models.CharField(max_length=100,choices=DOCUMENT_TYPE_CHOICES)
    document_front = models.CharField(max_length=255)
    # document_back = models.CharField(max_length=255, null=True, blank=True)
    verification_id = models.CharField(max_length=100, null=True, blank=True)
    status = models.CharField(max_length=50, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)


class BankDetails(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.OneToOneField(ProviderProfile, on_delete=models.CASCADE, related_name='bank_details')
    bank_account_name = models.CharField(max_length=255)
    bank_account_number = models.CharField(max_length=50)

    #=========new
    bank_name = models.TextField(null=True, blank=True)
    routing_number = models.TextField(null=True, blank=True)
    #===========

    bank_details = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Bank Details - {self.provider.user.email}"

    class Meta:
        verbose_name_plural = "Bank Details"





