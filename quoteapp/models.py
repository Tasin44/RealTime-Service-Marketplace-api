from django.db import models
from django.contrib.auth.models import User
from serviceproviderapp .models import ProviderProfile
from servicereceiverapp .models import ReceiverProfile
from serviceproviderapp.models import ServiceCategory
from django.conf import settings
# Create your models here.
# ===========================
# QUOTATIONS
# ===========================
class Quotation(models.Model):
    # quotation_id = models.AutoField(primary_key=True)# No need to declare any PK — Django auto-adds: id = models.BigAutoField(primary_key=True)
    provider = models.ForeignKey(ProviderProfile, on_delete=models.CASCADE)
    receiver = models.ForeignKey(ReceiverProfile, on_delete=models.CASCADE)

    service_category = models.ForeignKey(ServiceCategory, on_delete=models.RESTRICT)
    service_description = models.TextField(null=True, blank=True)
    service_cost = models.DecimalField(max_digits=10, decimal_places=2)
    service_timeline = models.CharField(max_length=255)#start time, end time will be provided by frontend
    terms_conditions = models.TextField(null=True, blank=True)

    quotation_status = models.CharField(
        max_length=20,
        choices=[('sent', 'Sent'), ('accepted', 'Accepted'), ('declined', 'Declined')],
        default='sent'
    )

    payment_status = models.CharField(
        max_length=20,
        choices=[('pending', 'Pending'), ('paid', 'Paid')],
        default='pending'
    )
    # ADD THESE NEW FIELDS:
    urgency_type = models.CharField(
        max_length=20,
        choices=[('normal', 'Normal'), ('urgent', 'Urgent')],
        default='normal'
    )
    platform_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.99)  # $0.99 or $2.99
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # service_cost + platform_fee

    payment_link = models.URLField(max_length=500, null=True, blank=True)
    cancellation_reason = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


# ===========================
# ORDERS
# ===========================
class Order(models.Model):
    order_id = models.AutoField(primary_key=True)
    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE)
    receiver = models.ForeignKey(ReceiverProfile, on_delete=models.CASCADE)
    provider = models.ForeignKey(ProviderProfile, on_delete=models.CASCADE)

    #those below 4 information won't be always same as qutotaion, they can be change at the time of making order 
    service_category = models.ForeignKey(ServiceCategory, on_delete=models.RESTRICT)
    service_description = models.TextField(null=True, blank=True)
    service_cost = models.DecimalField(max_digits=10, decimal_places=2)
    service_time_taken = models.CharField(max_length=255, null=True, blank=True)

    platform_commission = models.DecimalField(max_digits=10, decimal_places=2,default=0)
    provider_amount = models.DecimalField(max_digits=10, decimal_places=2)

    order_status = models.CharField(
        max_length=20,
        choices=[('active', 'Active'), ('completed', 'Completed'), ('cancelled', 'Cancelled'), ('refunded', 'Refunded')],
        default='active'
    )

    payment_intent_id = models.CharField(max_length=255, null=True, blank=True)
    payment_status = models.CharField(
        max_length=20,
        choices=[('unpaid', 'Unpaid'), ('paid', 'Paid'), ('released', 'Released'), ('refunded', 'Refunded')],
        default='unpaid'
    )

    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(null=True, blank=True)

    # ADD THESE NEW FIELDS:
    urgency_type = models.CharField(max_length=20, default='normal')  # Copy from quotation
    platform_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # $0.99 or $2.99
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Total client pays
    # ADD THESE FIELDS
    cancellation_requested_by = models.CharField(max_length=20, null=True, blank=True)  # 'receiver' or 'provider'
    cancellation_request_status = models.CharField(
        max_length=20,
        choices=[('none', 'None'), ('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')],
        default='none'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


# ===========================
# REVIEWS
# ===========================
class Review(models.Model):
    id = models.BigAutoField(primary_key=True)
    provider = models.ForeignKey(ProviderProfile, on_delete=models.CASCADE)
    receiver = models.ForeignKey(ReceiverProfile, on_delete=models.CASCADE)
    order = models.ForeignKey(Order, on_delete=models.CASCADE)

    rating = models.IntegerField()
    review_text = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)


# ===========================
# TRANSACTIONS
# ===========================
class Transaction(models.Model):
    transaction_id = models.AutoField(primary_key=True)
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    stripe_account_id = models.CharField(max_length=255, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    platform_fee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    provider_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=[('hold', 'Hold'), ('released', 'Released'), ('refunded', 'Refunded')],
        default='hold'
    )

    created_at = models.DateTimeField(auto_now_add=True)

