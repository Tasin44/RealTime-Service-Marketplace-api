from django.contrib import admin
from .models import ServiceCategory, ProviderDocument, ProviderKeyword, ProviderProfile, ProviderWorkImage, BankDetails

@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'category_name', 'created_at']
    search_fields = ['category_name']

@admin.register(ProviderProfile)
class ProviderProfileAdmin(admin.ModelAdmin):
    list_display = ['id', 'get_user_name', 'get_user_email', 'service_category', 'provider_is_verified']
    search_fields = ['user__name', 'user__email', 'service_category__category_name']
    list_filter = ['provider_is_verified', 'service_category']

    def get_user_name(self, obj):
        return obj.user.name
    get_user_name.short_description = 'Provider Name'
    get_user_name.admin_order_field = 'user__name'

    def get_user_email(self, obj):
        return obj.user.email
    get_user_email.short_description = 'Provider Email'
    get_user_email.admin_order_field = 'user__email'

@admin.register(ProviderDocument)
class ProviderDocumentAdmin(admin.ModelAdmin):
    list_display = ['id', 'get_user_name', 'get_user_email', 'document_type', 'status', 'uploaded_at']
    search_fields = ['provider__user__name', 'provider__user__email', 'document_type', 'status']
    list_filter = ['status', 'document_type']

    def get_user_name(self, obj):
        return obj.provider.user.name
    get_user_name.short_description = 'Provider Name'
    get_user_name.admin_order_field = 'provider__user__name'

    def get_user_email(self, obj):
        return obj.provider.user.email
    get_user_email.short_description = 'Provider Email'
    get_user_email.admin_order_field = 'provider__user__email'

@admin.register(ProviderWorkImage)
class ProviderWorkImageAdmin(admin.ModelAdmin):
    list_display = ['id', 'get_user_name', 'get_user_email', 'created_at']
    search_fields = ['provider__user__name', 'provider__user__email']

    def get_user_name(self, obj):
        return obj.provider.user.name
    get_user_name.short_description = 'Provider Name'
    get_user_name.admin_order_field = 'provider__user__name'

    def get_user_email(self, obj):
        return obj.provider.user.email
    get_user_email.short_description = 'Provider Email'
    get_user_email.admin_order_field = 'provider__user__email'

@admin.register(ProviderKeyword)
class ProviderKeywordAdmin(admin.ModelAdmin):
    list_display = ['id', 'get_user_name', 'get_user_email', 'keyword']
    search_fields = ['provider__user__name', 'provider__user__email', 'keyword']

    def get_user_name(self, obj):
        return obj.provider.user.name
    get_user_name.short_description = 'Provider Name'
    get_user_name.admin_order_field = 'provider__user__name'

    def get_user_email(self, obj):
        return obj.provider.user.email
    get_user_email.short_description = 'Provider Email'
    get_user_email.admin_order_field = 'provider__user__email'

@admin.register(BankDetails)
class BankDetailsAdmin(admin.ModelAdmin):
    list_display = ['id', 'get_user_name', 'get_user_email', 'bank_account_name', 'bank_account_number', 'created_at']
    search_fields = ['provider__user__name', 'provider__user__email', 'bank_account_name', 'bank_account_number']

    def get_user_name(self, obj):
        return obj.provider.user.name
    get_user_name.short_description = 'Provider Name'
    get_user_name.admin_order_field = 'provider__user__name'

    def get_user_email(self, obj):
        return obj.provider.user.email
    get_user_email.short_description = 'Provider Email'
    get_user_email.admin_order_field = 'provider__user__email'