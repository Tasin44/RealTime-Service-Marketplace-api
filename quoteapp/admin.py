from django.contrib import admin

# Register your models here.

from .models import Quotation,Order,Review,Transaction
# Register your models here.
# admin.site.register(Quotation)
admin.site.register(Order)

admin.site.register(Review)
admin.site.register(Transaction)

@admin.register(Quotation)
class QuotationAdmin(admin.ModelAdmin):
    readonly_fields = ('cancellation_reason',)