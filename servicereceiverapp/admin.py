from django.contrib import admin
from .models import ReceiverProfile

@admin.register(ReceiverProfile)
class ReceiverProfileAdmin(admin.ModelAdmin):
    list_display = ['receiver_id', 'get_user_id', 'get_user_name', 'get_user_email', 'created_at']
    search_fields = ['user__name', 'user__email', 'user__id']

    def get_user_id(self, obj):
        return obj.user.id
    get_user_id.short_description = 'User ID'
    get_user_id.admin_order_field = 'user__id'

    def get_user_name(self, obj):
        return obj.user.name
    get_user_name.short_description = 'Receiver Name'
    get_user_name.admin_order_field = 'user__name'

    def get_user_email(self, obj):
        return obj.user.email
    get_user_email.short_description = 'Receiver Email'
    get_user_email.admin_order_field = 'user__email'
