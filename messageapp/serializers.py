from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta
from .models import Conversation, Message
from serviceproviderapp.models import ProviderProfile
from servicereceiverapp.models import ReceiverProfile
from django.contrib.auth import get_user_model
from django.utils.timesince import timesince
from django.conf import settings

User = get_user_model()


def _absolute_media_url(request, file_field):
    if not file_field:
        return None
    if request:
        return request.build_absolute_uri(file_field.url)
    return f"{settings.BASE_URL.rstrip('/')}{file_field.url}"

# Basic user info serializer - prevents N+1 queries
class UserBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'name', 'email']
        read_only_fields = ['id', 'name', 'email']


# List view serializer - lightweight, shows last message preview
class ConversationListSerializer(serializers.ModelSerializer):
    # receiver_name = serializers.CharField(source='receiver.user.name', read_only=True)
    # provider_name = serializers.CharField(source='provider.user.name', read_only=True)

    '''
    message_receiver = serializers.SerializerMethodField()
    message_sender = serializers.SerializerMethodField() 
    '''
    other_person = serializers.SerializerMethodField()  # ✅ Just this

    # Last message preview - will be added via annotation in view
    last_message = serializers.SerializerMethodField()
    # unread_count = serializers.SerializerMethodField()
    expires_at = serializers.SerializerMethodField()  # ✅ Make expires_at dynamic
# user_image = UserImageField(source="user.image", read_only=True)
    class Meta:
        model = Conversation
        fields = [
            'conversation_id','other_person',  # ✅ Single field
            'conversation_status', 'expires_at', 'last_message',
            'created_at', 'updated_at'
        ]

    '''
    #previously it was showing service receiver and service provider 
    def get_message_receiver(self, obj):
        return {
            'id': obj.receiver.user.id,
            'name': obj.receiver.user.name,
            'email': obj.receiver.user.email
        }
    
    def get_message_sender(self, obj):
        return {
            'user': {
                'id': obj.provider.user.id,
                'name': obj.provider.user.name,
                'email': obj.provider.user.email
            },
            'service_title': obj.provider.service_title
        }
    '''
    
    '''
    def get_message_receiver(self, obj):
        request = self.context.get('request')
        if not request:
            return None
        
        current_user = request.user
        
        # Show the OTHER person in the conversation
        if obj.receiver.user == current_user:
            # If current user is receiver, show provider info
            return {
                'id': obj.provider.user.id,
                'name': obj.provider.user.name,
                'email': obj.provider.user.email
            }
        else:
            # If current user is provider, show receiver info
            return {
                'id': obj.receiver.user.id,
                'name': obj.receiver.user.name,
                'email': obj.receiver.user.email,
            }

    def get_message_sender(self, obj):
        request = self.context.get('request')
        if not request:
            return None
        
        current_user = request.user
        
        # Show the OTHER person's info
        if obj.provider.user == current_user:
            # If current user is provider, show receiver as "sender" of conversation
            return {
                'user': {
                    'id': obj.receiver.user.id,
                    'name': obj.receiver.user.name,
                    'email': obj.receiver.user.email
                },
                'service_title': obj.provider.service_title  # Keep provider's service title
            }
        else:
            # If current user is receiver, show provider as "sender" of conversation
            return {
                'user': {
                    'id': obj.receiver.user.id,  # Changed from provider
                    'name': obj.receiver.user.name,  # Changed from provider
                    'email': obj.receiver.user.email  # Changed from provider
                },
                'service_title': obj.provider.service_title
            }
    
    '''
    def get_other_person(self, obj):
        request = self.context.get('request')
        if not request:
            return None
        current_user = request.user
        
        # Return the OTHER person in conversation
        if obj.receiver.user == current_user:
            # Current user is receiver → show provider
            other = obj.provider
        else:
            # Current user is provider → show receiver
            other = obj.receiver
        
        return {
            'id': other.user.id,
            'name': other.user.name,
            'email': other.user.email,
            # 'image': other.user.image.url if hasattr(other.user, 'image') and other.user.image else None
            'image': _absolute_media_url(request, other.user.image)
        }
        
    def get_expires_at(self, obj):  # ✅ New method
        # If conversation is already expired, return "message expired"
        if obj.conversation_status == 'expired':
            return "message expired"
        # Otherwise return the actual expiry timestamp
        return obj.expires_at
    
    def get_last_message(self, obj):
        # Get the last message from prefetched data to avoid extra queries
        messages = getattr(obj, 'prefetched_messages', [])
        if messages:
            last_msg = messages[0]  # Already ordered by -created_at
             # Determine if sender is the receiver or provider
            return {
                'message_id': last_msg.message_id,
                'sender_id': last_msg.sender.id,
                'message_text': last_msg.message_text,
                'created_at': last_msg.created_at
            }
        return None
    
    '''
    def get_unread_count(self, obj):
        # Placeholder - implement read/unread tracking if needed
        return 0
    '''



# Detail view serializer - shows conversation with all messages
class ConversationDetailSerializer(serializers.ModelSerializer):
    # receiver = serializers.SerializerMethodField()
    # provider = serializers.SerializerMethodField()

    message_receiver = serializers.SerializerMethodField()  # ✅ Renamed
    message_sender = serializers.SerializerMethodField()    # ✅ Renamed

    other_person = serializers.SerializerMethodField()  # ✅ Same change
    messages = serializers.SerializerMethodField()
    expires_at = serializers.SerializerMethodField()  # ✅ Add this

    class Meta:
        model = Conversation
        fields = [
            'conversation_id', 'other_person','message_receiver', 'message_sender',  # ✅ Updated
            'conversation_status', 'expires_at', 'messages', 
            'created_at', 'updated_at'
        ]
    '''
    def get_receiver(self, obj):
        return {
            'receiver_id': obj.receiver.receiver_id,
            'user': UserBasicSerializer(obj.receiver.user).data
        }
    '''
    '''
    def get_message_receiver(self, obj):  # ✅ Renamed
        return UserBasicSerializer(obj.receiver.user).data  # ❌ Removed receiver_id
    '''

    
    '''
    def get_provider(self, obj):
        return {
            'provider_id': obj.provider.id,
            'user': UserBasicSerializer(obj.provider.user).data,
            'service_title': obj.provider.service_title
        }
    '''
    '''
    def get_message_sender(self, obj):  # ✅ Renamed
        return {
            'user': UserBasicSerializer(obj.provider.user).data,
            'service_title': obj.provider.service_title
        }  # ❌ Removed provider_id
    '''
    def get_message_receiver(self, obj):
        request = self.context.get('request')
        if not request:
            return None
        
        current_user = request.user
        
        # Show the OTHER person in the conversation
        if obj.receiver.user == current_user:
            # If current user is receiver, show provider info
            return {
                'id': obj.provider.user.id,
                'name': obj.provider.user.name,
                'email': obj.provider.user.email
            }
        else:
            # If current user is provider, show receiver info
            return {
                'id': obj.receiver.user.id,
                'name': obj.receiver.user.name,
                'email': obj.receiver.user.email
            }

    def get_message_sender(self, obj):
        request = self.context.get('request')
        if not request:
            return None
        
        current_user = request.user
        
        # Show the OTHER person's info
        if obj.provider.user == current_user:
            # If current user is provider, show receiver as "sender" of conversation
            return {
                'user': {
                    'id': obj.receiver.user.id,
                    'name': obj.receiver.user.name,
                    'email': obj.receiver.user.email
                },
                'service_title': obj.provider.service_title  # Keep provider's service title
            }
        else:
            # # If current user is receiver, show RECEIVER (themselves) as sender
            return {
                'user': {
                'id': obj.receiver.user.id,  # Changed from provider
                'name': obj.receiver.user.name,  # Changed from provider
                'email': obj.receiver.user.email  # Changed from provider
                },
                'service_title': obj.provider.service_title
            }
        
    def get_other_person(self, obj):
        request = self.context.get('request')
        if not request:
            return None
        current_user = request.user
        
        # Return the OTHER person in conversation
        if obj.receiver.user == current_user:
            # Current user is receiver → show provider
            other = obj.provider
        else:
            # Current user is provider → show receiver
            other = obj.receiver
        
        return {
            'id': other.user.id,
            'name': other.user.name,
            'email': other.user.email,
            # 'image': other.user.image.url if hasattr(other.user, 'image') and other.user.image else None
            'image': _absolute_media_url(request, other.user.image)
        }
    
    def get_messages(self, obj):
        # Get messages from prefetched data
        messages = obj.message_set.all().order_by('created_at')
        return MessageSerializer(messages, many=True, context=self.context).data
    
    def get_expires_at(self, obj):  # ✅ Add this method
        if obj.conversation_status == 'expired':
            return "message expired"
        return obj.expires_at

# Serializer for creating a new conversation (receiver initiates)
class ConversationCreateSerializer(serializers.Serializer):
    provider_id = serializers.CharField()  # User UUID
    initial_message = serializers.CharField(max_length=1000, default="Hi I want to take service")
    
    '''
    def validate_provider_id(self, value):
        # Check if provider exists
        if not ProviderProfile.objects.filter(id=value).exists():
            raise serializers.ValidationError("Provider not found")
        return value
    '''

    def validate_provider_user_id(self, value):
        try:
            # Find user by UUID
            user = User.objects.get(id=value)
            # Check if user has a provider profile
            if not hasattr(user, 'providerprofile'):
                raise serializers.ValidationError("User is not a provider")
        except User.DoesNotExist:
            raise serializers.ValidationError("Provider user not found")
        except ValueError:
            raise serializers.ValidationError("Invalid user ID format")
        return value
    
    def create(self, validated_data):
        receiver = self.context['receiver']  # From view
        provider_id = validated_data['provider_id']
        initial_message = validated_data['initial_message']
        
        # provider = ProviderProfile.objects.get(id=provider_id)
         # Get user and their provider profile
        user = User.objects.get(id=provider_id)
        provider = user.providerprofile  # Assuming OneToOne relation

        # Check if conversation already exists
        existing_conv = Conversation.objects.filter(
            receiver=receiver, 
            provider=provider
        ).first()
        
        if existing_conv:
            # If expired, create new message to reactivate
            if existing_conv.conversation_status == 'expired':
                existing_conv.conversation_status = 'pending'
                existing_conv.expires_at = timezone.now() + timedelta(hours=24)
                existing_conv.save()
            
            # Add initial message
            Message.objects.create(
                conversation=existing_conv,
                sender=receiver.user,
                message_text=initial_message
            )
            return existing_conv
        
        # Create new conversation with 24-hour expiry
        conversation = Conversation.objects.create(
            receiver=receiver,
            provider=provider,
            conversation_status='pending',
            expires_at=timezone.now() + timedelta(hours=24)
        )
        
        # Create initial message
        Message.objects.create(
            conversation=conversation,
            sender=receiver.user,
            message_text=initial_message
        )
        
        return conversation


# Serializer for provider accepting/declining conversation
class ConversationStatusUpdateSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['accept', 'decline'])
    
    def update(self, instance, validated_data):
        action = validated_data['action']
        
        # Check if conversation is still pending and not expired
        if instance.conversation_status != 'pending':
            raise serializers.ValidationError("Conversation has already been processed")
        
        if timezone.now() > instance.expires_at:
            instance.conversation_status = 'expired'
            instance.save()
            raise serializers.ValidationError("Conversation request has expired")
        
        # Update status based on action
        if action == 'accept':
            instance.conversation_status = 'active'
        else:
            instance.conversation_status = 'expired'
        
        instance.save()
        return instance


# Message serializer
class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.name', read_only=True)
    sender_id = serializers.CharField(source='sender.id', read_only=True)
    receiver_id = serializers.SerializerMethodField()
    receiver_name = serializers.SerializerMethodField()
    message_image = serializers.SerializerMethodField()
    message_file = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            'message_id', 'conversation', 'sender','receiver_id',
            'sender_name', 'message_text', 'message_image','sender_id','receiver_name',
            'message_file', 'message_voice', 'created_at'
        ]
        read_only_fields = ['message_id', 'sender', 'created_at']

    def get_receiver_id(self, obj):
        # The receiver is the OTHER person in the conversation
        if obj.sender == obj.conversation.receiver.user:
            return str(obj.conversation.provider.user.id)
        else:
            return str(obj.conversation.receiver.user.id)
    
    def get_receiver_name(self, obj):
        if obj.sender == obj.conversation.receiver.user:
            return obj.conversation.provider.user.name
        else:
            return obj.conversation.receiver.user.name
        
    def get_message_image(self, obj):
        request = self.context.get("request")
        if obj.message_image and request:
            return request.build_absolute_uri(obj.message_image.url)
        return None

    def get_message_file(self, obj):
        request = self.context.get("request")
        if obj.message_file and request:
            return request.build_absolute_uri(obj.message_file.url)
        return None

#Last advice from claude for class MessageSerializer(serializers.ModelSerializer):
'''
Remove:

receiver_id - not needed (client knows conversation participants)
receiver_name - not needed
get_receiver_id() method
get_receiver_name() method

Why?

Messages are fetched per conversation
Client already knows who the "other person" is from conversation detail
Just show sender info per message - receiver is implied

'''
# Serializer for sending messages
class MessageCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = [
            'conversation', 'message_text', 'message_image', 
            'message_file', 'message_voice'
        ]
    
    def validate_conversation(self, value):
        sender = self.context.get('sender')

        # Receiver must wait for provider acceptance while conversation is pending.
        if value.conversation_status == 'pending' and sender == value.receiver.user:
            raise serializers.ValidationError(
                "Please Wait untill the provider accept your msg request"
            )

        # Check if conversation is active
        if value.conversation_status != 'active':
            raise serializers.ValidationError("Please Wait untill the provider accept your msg request")
        return value
    
    def validate(self, data):
        # At least one content field must be provided
        if not any([
            data.get('message_text'),
            data.get('message_image'),
            data.get('message_file'),
            data.get('message_voice')
        ]):
            raise serializers.ValidationError("At least one message content field is required")
        return data
    
    def create(self, validated_data):
        # Sender comes from context (request.user)
        sender = self.context['sender']
        validated_data['sender'] = sender
        
        message = Message.objects.create(**validated_data)
        
        # Update conversation's updated_at timestamp
        # validated_data['conversation'].save()
        conversation = validated_data['conversation']
        conversation.updated_at = timezone.now()
        conversation.save(update_fields=["updated_at"])
        return message

class MessageListSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    conversation = serializers.IntegerField()
    other_person = serializers.DictField()
    conversation_status = serializers.CharField()
    results = MessageSerializer(many=True)
