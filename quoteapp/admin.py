from django.contrib import admin
from .models import Quotation, Order, Review, Transaction

@admin.register(Quotation)
class QuotationAdmin(admin.ModelAdmin):
    list_display = ['id', 'get_provider_details', 'get_receiver_details', 'quotation_status', 'payment_status', 'created_at']
    search_fields = ['provider__user__name', 'provider__user__email', 'receiver__user__name', 'receiver__user__email']
    list_filter = ['quotation_status', 'payment_status']
    readonly_fields = ('cancellation_reason',)

    def get_provider_details(self, obj):
        return f"ID: {obj.provider.user.id} | {obj.provider.user.name} ({obj.provider.user.email})"
    get_provider_details.short_description = 'Provider Details'
    get_provider_details.admin_order_field = 'provider__user__name'

    def get_receiver_details(self, obj):
        return f"ID: {obj.receiver.user.id} | {obj.receiver.user.name} ({obj.receiver.user.email})"
    get_receiver_details.short_description = 'Receiver Details'
    get_receiver_details.admin_order_field = 'receiver__user__name'


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_id', 'get_provider_details', 'get_receiver_details', 'order_status', 'payment_status', 'created_at']
    search_fields = ['provider__user__name', 'provider__user__email', 'receiver__user__name', 'receiver__user__email']
    list_filter = ['order_status', 'payment_status']

    def get_provider_details(self, obj):
        return f"ID: {obj.provider.user.id} | {obj.provider.user.name} ({obj.provider.user.email})"
    get_provider_details.short_description = 'Provider Details'
    get_provider_details.admin_order_field = 'provider__user__name'

    def get_receiver_details(self, obj):
        return f"ID: {obj.receiver.user.id} | {obj.receiver.user.name} ({obj.receiver.user.email})"
    get_receiver_details.short_description = 'Receiver Details'
    get_receiver_details.admin_order_field = 'receiver__user__name'


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['id', 'get_provider_details', 'get_receiver_details', 'rating', 'created_at']
    search_fields = ['provider__user__name', 'provider__user__email', 'receiver__user__name', 'receiver__user__email']
    list_filter = ['rating']

    def get_provider_details(self, obj):
        return f"ID: {obj.provider.user.id} | {obj.provider.user.name} ({obj.provider.user.email})"
    get_provider_details.short_description = 'Provider Details'
    get_provider_details.admin_order_field = 'provider__user__name'

    def get_receiver_details(self, obj):
        return f"ID: {obj.receiver.user.id} | {obj.receiver.user.name} ({obj.receiver.user.email})"
    get_receiver_details.short_description = 'Receiver Details'
    get_receiver_details.admin_order_field = 'receiver__user__name'


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['transaction_id', 'get_user_id', 'get_user_name', 'get_user_email', 'amount', 'status', 'created_at']
    search_fields = ['user__name', 'user__email', 'stripe_account_id']
    list_filter = ['status']

    def get_user_id(self, obj):
        return obj.user.id
    get_user_id.short_description = 'User ID'
    get_user_id.admin_order_field = 'user__id'

    def get_user_name(self, obj):
        return obj.user.name
    get_user_name.short_description = 'User Name'
    get_user_name.admin_order_field = 'user__name'

    def get_user_email(self, obj):
        return obj.user.email
    get_user_email.short_description = 'User Email'
    get_user_email.admin_order_field = 'user__email'