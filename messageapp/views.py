from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets, status, serializers as drf_serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Prefetch, Max, F
from django.utils import timezone
from rest_framework.pagination import PageNumberPagination
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import Conversation, Message
from serviceproviderapp.models import ProviderProfile
from servicereceiverapp.models import ReceiverProfile
from .serializers import (
    ConversationListSerializer, ConversationDetailSerializer,
    ConversationCreateSerializer, ConversationStatusUpdateSerializer,
    MessageSerializer, MessageCreateSerializer
)
from rest_framework.parsers import MultiPartParser, FormParser

# Standard pagination
class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


# Mixin for consistent responses
class StandardResponseMixin:
    """Mixin for consistent API responses"""
    def success_response(self, data, message="Success", status_code=200):
        return Response({
            "success": True,
            "statusCode": status_code,
            "message": message,
            "data": data,
            "timestamp": timezone.now().isoformat()
        }, status=status_code)
    
    def error_response(self, message, status_code=400, data=None):
        detail = self.extract_first_error(data)
        if detail and detail not in message:
            message = f"{message}: {detail}"
        return Response({
            "success": False,
            "statusCode": status_code,
            "message": message,
            "data": data,
            "timestamp": timezone.now().isoformat()
        }, status=status_code)

    def extract_first_error(self, errors):
        if isinstance(errors, dict):
            if "non_field_errors" in errors:
                extracted = self.extract_first_error(errors.get("non_field_errors"))
                if extracted:
                    return extracted
            for field, value in errors.items():
                if isinstance(value, list) and value:
                    nested = value[0]
                    if isinstance(nested, (dict, list)):
                        extracted = self.extract_first_error(nested)
                        if extracted:
                            return f"{field} :: {extracted}"
                    return f"{field} :: {nested}"
                if isinstance(value, str):
                    return f"{field} :: {value}"
                extracted = self.extract_first_error(value)
                if extracted:
                    return f"{field} :: {extracted}"
        elif isinstance(errors, list) and errors:
            extracted = self.extract_first_error(errors[0])
            if extracted:
                return extracted
        elif errors:
            return str(errors)
        return None

def extract_first_error(errors):
    """Extract the first error message from serializer errors dict"""
    for field, messages in errors.items():
        if isinstance(messages, list) and messages:
            return messages[0]
             #return f"{field}: {messages[0]}"
        elif isinstance(messages, str):
            return messages
    return "Validation Error"


class ConversationViewSet(StandardResponseMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        user = self.request.user
        
        # Base queryset with optimized joins - prevents N+1 queries
        queryset = Conversation.objects.select_related(
            'receiver__user',  # Join receiver and user tables
            'provider__user'   # Join provider and user tables
        )
        
        # Prefetch last message for list view (most recent first)
        if self.action == 'list':
            queryset = queryset.prefetch_related(
                Prefetch(
                    'message_set',
                    queryset=Message.objects.order_by('-created_at')[:1],
                    to_attr='prefetched_messages'
                )
            )
        
        # Filter based on user role - show conversations user is part of
        if user.role == 'provider':
            # If user is a provider
            return queryset.filter(provider__user=user).exclude(
                receiver__user=F('provider__user')
            )
        
        if user.role == 'receiver':
            # If user is a receiver
            return queryset.filter(receiver__user=user).exclude(
                receiver__user=F('provider__user')
            )
            
        # If user has no profile, return empty
        return queryset.none()
    
    def get_serializer_class(self):
        # Return appropriate serializer based on action
        if self.action == 'list':
            return ConversationListSerializer
        elif self.action == 'retrieve':
            return ConversationDetailSerializer
        elif self.action == 'create':
            return ConversationCreateSerializer
        elif self.action == 'update_status':
            return ConversationStatusUpdateSerializer
        return ConversationDetailSerializer
    
    @swagger_auto_schema(
        operation_description="Get list of conversations (inbox)",
        manual_parameters=[
            openapi.Parameter('status', openapi.IN_QUERY, type=openapi.TYPE_STRING,
                            description="Filter by status: pending, active, expired"),
        ]
    )




    def list(self, request, *args, **kwargs):

        queryset = self.get_queryset()

        # 🔹 Filter by conversation status if provided
        status_filter = request.query_params.get('status')
        if status_filter in ['pending', 'active', 'expired']:
            queryset = queryset.filter(conversation_status=status_filter)

        # 🔹 Auto-expire pending conversations
        self._auto_expire_conversations(queryset)

        # 🔹 Order by most recently updated
        queryset = queryset.order_by('-updated_at')

        # 🔹 Paginate ONCE
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(
                page,
                many=True,
                context={'request': request}
            )
            return self.get_paginated_response(serializer.data)

        # 🔹 Fallback (normally not hit if pagination is enabled)
        serializer = self.get_serializer(
            queryset,
            many=True,
            context={'request': request}
        )
        return Response(serializer.data)

    def _auto_expire_conversations(self, queryset):
        # Auto-expire pending conversations past 24 hours
        expired_conversations = queryset.filter(
            conversation_status='pending',
            expires_at__lte=timezone.now()
        )
        expired_conversations.update(conversation_status='expired')
    
    @swagger_auto_schema(
        operation_description="Create new conversation (Receiver initiates)",
        request_body=ConversationCreateSerializer,
        responses={201: ConversationDetailSerializer()}
    )


    def create(self, request, *args, **kwargs):
        # Only receivers can initiate conversations

        try:
            receiver = ReceiverProfile.objects.get(user=request.user)
        except ReceiverProfile.DoesNotExist:
            return self.error_response(
                "Only service receivers can initiate conversations",
                status_code=403
            )
        
        # Create conversation with receiver in context
        serializer = self.get_serializer(
            data=request.data,
            context={'receiver': receiver}
        )
        
        if serializer.is_valid():
            try:
                conversation = serializer.save()
            except drf_serializers.ValidationError as exc:
                first_error = self.extract_first_error(exc.detail)
                return self.error_response(
                    first_error or "Validation failed",
                    status_code=400,
                    data=exc.detail
                )
            
            detail_serializer = ConversationDetailSerializer(
                conversation,
                context={'request': request}  
            )
            return self.success_response(
                detail_serializer.data,
                message="Conversation created successfully",
                status_code=201
            )
        
        first_error = self.extract_first_error(serializer.errors)
        return self.error_response(
            first_error or "Validation failed",
            status_code=400,
            data=serializer.errors
        )

    @swagger_auto_schema(
        operation_description="Get current conversation status",
        responses={200: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                'statusCode': openapi.Schema(type=openapi.TYPE_INTEGER),
                'message': openapi.Schema(type=openapi.TYPE_STRING),
                'data': openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'conversation_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'conversation_status': openapi.Schema(type=openapi.TYPE_STRING),
                        'is_accepted': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'expires_at': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                ),
                'timestamp': openapi.Schema(type=openapi.TYPE_STRING),
            }
        )}
    )
    @action(detail=True, methods=['get'], url_path='status')
    def conversation_status(self, request, pk=None):
        conversation = self.get_object()

        # Keep status fresh for expired pending requests.
        if (
            conversation.conversation_status == 'pending' and
            conversation.expires_at <= timezone.now()
        ):
            conversation.conversation_status = 'expired'
            conversation.save(update_fields=['conversation_status', 'updated_at'])

        data = {
            "conversation_id": conversation.conversation_id,
            "conversation_status": conversation.conversation_status,
            "is_accepted": conversation.conversation_status == 'active',
            "expires_at": conversation.expires_at,
        }

        return self.success_response(
            data,
            message="Conversation status fetched successfully",
            status_code=200
        )
    
    @swagger_auto_schema(
        operation_description="Get conversation details with all messages",
        responses={200: ConversationDetailSerializer()}
    )
    def retrieve(self, request, pk=None):
        conversation = self.get_object()
        #serializer = self.get_serializer(conversation)
        serializer = self.get_serializer(
            conversation,
            context={'request': request}  # ✅ ADD THIS
        )
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_description="Accept or decline conversation (Provider only)",
        request_body=ConversationStatusUpdateSerializer,
        responses={200: ConversationDetailSerializer()}
    )
    @action(detail=True, methods=['patch'], url_path='update-status')
    def update_status(self, request, pk=None):
        conversation = self.get_object()
        
        # Verify user is the provider
        try:
            provider = ProviderProfile.objects.get(user=request.user)
            if conversation.provider != provider:
                return self.error_response(
                    "You can only update conversations sent to you",
                    status_code=403
                )
        except ProviderProfile.DoesNotExist:
            return self.error_response(
                "Only service providers can accept/decline conversations",
                status_code=403
            )
        
        # Update status
        serializer = ConversationStatusUpdateSerializer(
            conversation,
            data=request.data,
            partial=True
        )
        
        if serializer.is_valid():
            serializer.save()
            
            detail_serializer = ConversationDetailSerializer(
                conversation,
                context={'request': request}  # ✅ ADD THIS
            )
            return Response(detail_serializer.data)
        
        return self.error_response(
            "Validation failed",
            status_code=400,
            data=serializer.errors
        )


class MessageViewSet(StandardResponseMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    serializer_class = MessageSerializer
    parser_classes = [MultiPartParser, FormParser]
    def get_queryset(self):
        user = self.request.user
        
        queryset = Message.objects.select_related(
            'sender',
            'conversation__receiver__user',
            'conversation__provider__user'
        ).filter(
            Q(conversation__receiver__user=user) | 
            Q(conversation__provider__user=user)
        )
        
        # If filtering by conversation, apply it
        conversation_id = self.request.query_params.get('conversation_id', None)
        if conversation_id:
            queryset = queryset.filter(conversation_id=conversation_id)
        
        return queryset.order_by('created_at')  # Chronological order
    
    def get_serializer_class(self):
        if self.action == 'create':
            return MessageCreateSerializer
        return MessageSerializer
    

    def list(self, request, *args, **kwargs):
        conversation_id = request.query_params.get('conversation_id')
        if not conversation_id:
            return self.error_response("conversation_id required", 400)
        

        conversation = Conversation.objects.select_related(
            'receiver__user', 'provider__user'
        ).get(conversation_id=conversation_id)
        
        # Get other person
        current_user = request.user
        if conversation.receiver.user == current_user:
            other = conversation.provider.user
        else:
            other = conversation.receiver.user
        
        # Get messages
        queryset = self.get_queryset()
        messages = MessageSerializer(
            queryset,
            many=True,
            context={"request": request}
        ).data
        
        return Response({
            "count": len(messages),
            "conversation": conversation.conversation_id,
            "other_person": {
                "id": str(other.id),
                "name": other.name,
                "email": other.email,
                "image": request.build_absolute_uri(other.image.url) if other.image else None
            },
            "conversation_status": conversation.conversation_status,
            "results": messages
        })
    



    @swagger_auto_schema(
        operation_description="Send a message in conversation",
        request_body=MessageCreateSerializer,
        responses={201: MessageSerializer()}
    )
    def create(self, request, *args, **kwargs):
        # Add sender to context
        serializer = self.get_serializer(
            data=request.data,
            context={'sender': request.user}
        )
        
        if serializer.is_valid():
            # Verify user is part of the conversation
            conversation = serializer.validated_data['conversation']
            if (conversation.receiver.user != request.user and 
                conversation.provider.user != request.user):
                return self.error_response(
                    "You are not part of this conversation",
                    status_code=403
                )
            
            message = serializer.save()
            

            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            
            channel_layer = get_channel_layer()
            conversation_id = message.conversation.conversation_id

            message_image_url = None
            message_file_url = None
            
            if message.message_image:
                message_image_url = request.build_absolute_uri(message.message_image.url)
            
            if message.message_file:
                message_file_url = request.build_absolute_uri(message.message_file.url)

            async_to_sync(channel_layer.group_send)(
                f'chat_{conversation_id}',
                {
                    'type': 'chat_message',
                    'message_id': message.message_id,
                    # 'sender_id': message.sender.id,
                    'sender_id': str(message.sender.id),
                    'sender_name': message.sender.name,
                    'message_text': message.message_text,
                    'message_image': message_image_url,
                    'message_file': message_file_url,
                    'created_at': message.created_at.isoformat()
                }
            )
            
            detail_serializer = MessageSerializer(
                message,
                context={"request": request}
            )
            return self.success_response(detail_serializer.data, message="Message sent", status_code=201)
        
        first_error = self.extract_first_error(serializer.errors)
        error_message = "Validation failed"
        if first_error:
            error_message = f"Validation failed: {first_error}"

        return self.error_response(
            error_message,
            status_code=400,
            data=serializer.errors
        )
    
    
