from django.contrib import admin
from .models import Conversation, Message

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['conversation_id', 'get_receiver_id', 'get_receiver_name', 'get_provider_id', 'get_provider_name', 'conversation_status', 'created_at']
    search_fields = ['receiver__user__name', 'receiver__user__email', 'provider__user__name', 'provider__user__email']
    list_filter = ['conversation_status']

    def get_receiver_id(self, obj):
        return obj.receiver.user.id
    get_receiver_id.short_description = 'Receiver User ID'

    def get_receiver_name(self, obj):
        return f"{obj.receiver.user.name} ({obj.receiver.user.email})"
    get_receiver_name.short_description = 'Receiver Details'
    get_receiver_name.admin_order_field = 'receiver__user__name'

    def get_provider_id(self, obj):
        return obj.provider.user.id
    get_provider_id.short_description = 'Provider User ID'

    def get_provider_name(self, obj):
        return f"{obj.provider.user.name} ({obj.provider.user.email})"
    get_provider_name.short_description = 'Provider Details'
    get_provider_name.admin_order_field = 'provider__user__name'


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['message_id', 'conversation', 'get_sender_id', 'get_sender_name', 'get_sender_email', 'created_at']
    search_fields = ['sender__name', 'sender__email', 'message_text']

    def get_sender_id(self, obj):
        return obj.sender.id
    get_sender_id.short_description = 'Sender User ID'
    get_sender_id.admin_order_field = 'sender__id'

    def get_sender_name(self, obj):
        return obj.sender.name
    get_sender_name.short_description = 'Sender Name'
    get_sender_name.admin_order_field = 'sender__name'

    def get_sender_email(self, obj):
        return obj.sender.email
    get_sender_email.short_description = 'Sender Email'
    get_sender_email.admin_order_field = 'sender__email'
