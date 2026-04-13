import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Message, Conversation
from django.contrib.auth import get_user_model

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):

        query_string = self.scope['query_string'].decode()
        token = None
        
        if 'token=' in query_string:
            token = query_string.split('token=')[1].split('&')[0]
        
        # ✅  2. Authenticate user with JWT token
        if token:
            try:
                from rest_framework_simplejwt.tokens import AccessToken
                access_token = AccessToken(token)
                user_id = access_token['user_id']
                self.user = await self.get_user(user_id)
            except Exception:
                await self.close()# Invalid token → reject connection
                return
        else:
            await self.close()# No token → reject connection
            return
        
         # ✅3. Get conversation_id from URL
         # From URL: ws://api.com/ws/chat/42/ → conversation_id = 42
        self.conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]

        # ✅ 4. Check if user is authorized to access this conversation
        is_authorized = await self.check_user_authorization()
        if not is_authorized:
            await self.close()
            return

        
        # # ✅ 5. Join the conversation's WebSocket group
        # Example: "chat_42" for conversation ID 42
        self.room_group_name = f"chat_{self.conversation_id}"

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name# Unique channel for this connection
        )
        await self.accept()# ✅ Connection successful

    # ✅ Add this method
    @database_sync_to_async
    def get_user(self, user_id):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        return User.objects.get(id=user_id)
    

    async def receive(self, text_data):
        pass 


    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            "message_id": event["message_id"],
            "sender_id": event["sender_id"],
            "sender_name": event["sender_name"],
            "message_text": event.get("message_text"),
            "message_image": event.get("message_image"),
            "message_file": event.get("message_file"),
            "created_at": event["created_at"],
            # ✅ ADD THESE
            "quotation_id": event.get("quotation_id"),
            "quotation_status": event.get("quotation_status"),
            "accept_url": event.get("accept_url"),
            "reject_url": event.get("reject_url"),
            "payment_status": event.get("payment_status"),
            "payment_link": event.get("payment_link"),  # ✅ ADD THIS
            "terms_conditions": event.get("terms_conditions"),  # ✅ ADD THIS

            # ✅ ADD ORDER FIELDS
            "order_id": event.get("order_id"),
            "order_status": event.get("order_status"),
            "complete_url": event.get("complete_url"),
            "cancel_url": event.get("cancel_url"),
        }))


    # ✅ NEW METHOD:
    @database_sync_to_async
    def check_user_authorization(self):
        try:
            conversation = Conversation.objects.select_related(
                'receiver__user', 'provider__user'
            ).get(conversation_id=self.conversation_id)
            
            # Check if conversation is active
            if conversation.conversation_status != "active":
                return False
            
            # # Check if user is receiver OR provider
            is_allowed = (
                conversation.receiver.user_id == self.user.id
                or conversation.provider.user_id == self.user.id
            )
            return is_allowed
            
        except Conversation.DoesNotExist:
            return False
