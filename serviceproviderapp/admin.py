from django.contrib import admin

# Register your models here.
from .models import ServiceCategory,ProviderDocument,ProviderKeyword,ProviderProfile,ProviderWorkImage,BankDetails
# Register your models here.
admin.site.register(ServiceCategory)
admin.site.register(ProviderDocument)

admin.site.register(ProviderKeyword)
admin.site.register(ProviderProfile)
admin.site.register(ProviderWorkImage)

@admin.register(BankDetails)
class BankDetailsAdmin(admin.ModelAdmin):
    list_display = ['provider', 'bank_account_name', 'bank_account_number', 'created_at']
    search_fields = ['bank_account_name', 'provider__user__email']