from django.shortcuts import render
from django.conf import settings
# Create your views here.
#claude 
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Sum, Count, Prefetch, F
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from rest_framework.pagination import PageNumberPagination
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import stripe
from decimal import Decimal
from django.shortcuts import render
from .models import Quotation, Order, Review, Transaction
from serviceproviderapp.models import ProviderProfile
from servicereceiverapp.models import ReceiverProfile
from .serializers import (
    QuotationListSerializer, QuotationDetailSerializer, QuotationCreateSerializer,
    QuotationUpdateStatusSerializer, OrderListSerializer, OrderDetailSerializer,
    OrderCreateSerializer, OrderUpdateStatusSerializer, ReviewSerializer,
    TransactionSerializer, ProviderEarningsSerializer, HiringListSerializer,
    PaymentIntentSerializer,AcceptedQuotationForOrderSerializer

)
from .ai_utils import enhance_service_description

# Stripe configuration - load from environment variables in production
stripe.api_key = settings.STRIPE_SECRET_KEY  # Use from settings
# PLATFORM_STRIPE_ACCOUNT_ID = settings.PLATFORM_STRIPE_ACCOUNT_ID  # Admin Stripe account

class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination for all list views"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
    
class StandardResponseMixin:
    """Mixin for consistent API responses"""

    def success_response(self, data, message="Success", status_code=200):
        return Response({
            "success": True,
            "statusCode": status_code,
            "message": message,
            "data": data,
            # "timestamp": timezone.now().isoformat()
        }, status=status_code)

    def error_response(self, message, status_code=400, data=None):
        detail = self._extract_error_detail(data)
        if detail and detail not in message:
            message = f"{message}: {detail}"
        return Response({
            "success": False,
            "statusCode": status_code,
            "message": message,
            "data": data,
            # "timestamp": timezone.now().isoformat()
        }, status=status_code)

    def _extract_error_detail(self, data):
        if not data:
            return None
        if isinstance(data, str):
            return data
        if isinstance(data, list) and data:
            return self._extract_error_detail(data[0])
        if isinstance(data, dict):
            if "non_field_errors" in data:
                return self._extract_error_detail(data["non_field_errors"])
            for value in data.values():
                detail = self._extract_error_detail(value)
                if detail:
                    return detail
        return None


class QuotationViewSet(StandardResponseMixin,viewsets.ModelViewSet):
    """
    ViewSet for Quotation (Offer) management
    Provider creates quotations, Receiver accepts/declines
    """
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        """
        Optimized queryset with select_related to prevent N+1 queries
        Returns quotations based on user role
        """
        user = self.request.user
        
        # Base queryset with eager loading of related objects
        queryset = Quotation.objects.select_related(
            'provider__user',  # Join provider and user tables
            'receiver__user',  # Join receiver and user tables
            'service_category'  # Join category table
        )
        
        # Filter based on user role
        if user.role == 'provider':
            try:
                # If user is a provider, show quotations they created
                provider = ProviderProfile.objects.get(user=user)
                return queryset.filter(provider=provider)
            except ProviderProfile.DoesNotExist:
                pass
        if user.role == 'receiver':
            try:
                # If user is a receiver, show quotations sent to them
                receiver = ReceiverProfile.objects.get(user=user)
                return queryset.filter(receiver=receiver)
            except ReceiverProfile.DoesNotExist:
                pass
        
        # If user has no role, return empty queryset
        return queryset.none()
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return QuotationListSerializer
        elif self.action == 'retrieve':
            return QuotationDetailSerializer
        elif self.action == 'create':
            return QuotationCreateSerializer
        elif self.action == 'update_status':
            return QuotationUpdateStatusSerializer
        return QuotationDetailSerializer
    
    @swagger_auto_schema(
        operation_description="Get list of quotations (filtered by user role)",
        manual_parameters=[
            openapi.Parameter('status', openapi.IN_QUERY, type=openapi.TYPE_STRING, 
                            description="Filter by status: sent, accepted, declined"),
        ]
    )
    def list(self, request, *args, **kwargs):
        """
        List quotations with optional status filter
        Automatically filtered by user role (provider/receiver)
        """
        queryset = self.get_queryset()
        
        # Filter by status if provided
        status_filter = request.query_params.get('status', None)
        if status_filter and status_filter in ['sent', 'accepted', 'declined']:
            queryset = queryset.filter(quotation_status=status_filter)
        
        # Order by most recent first
        queryset = queryset.order_by('-created_at')
        
        # Paginate and return
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_description="Create a new quotation (Provider only)",
        request_body=QuotationCreateSerializer,
        responses={201: QuotationDetailSerializer()}
    )
    def create(self, request, *args, **kwargs):
        """
        Create new quotation - Only providers can create
        """
        # Verify user is a provider
        try:
            provider = ProviderProfile.objects.get(user=request.user)
        except ProviderProfile.DoesNotExist:
            return Response(
                {"error": "Only service providers can create quotations"},
                status=status.HTTP_403_FORBIDDEN
            )
        
    
        # ✅ ADD THIS SECTION - Enhance description with AI
        data = request.data.copy()
        original_description = data.get('service_description', '')
        
        if original_description:
            # Get category name for context
            category_id = data.get('service_category')
            category_name = None
            if category_id:
                try:
                    from serviceproviderapp.models import ServiceCategory
                    category = ServiceCategory.objects.get(id=category_id)
                    category_name = category.category_name
                except:
                    pass
            
            # Enhance with AI
            enhanced_description = enhance_service_description(
                original_description=original_description,
                service_category=category_name,
                urgency_type=data.get('urgency_type', 'normal'),
                message_type='offer'  # ✅ ADD THIS
            )
            data['service_description'] = enhanced_description
            # ✅ ADD THIS DEBUG LINE
            print(f"🔥 Original: {original_description}")
            print(f"✨ Enhanced: {enhanced_description}")
            print(f"📦 Data being sent to serializer: {data}")

        # Continue with existing serializer logic
        serializer = self.get_serializer(
            data=data,  # ✅ Use enhanced data instead of request.data
            context={'provider': provider}
        )
        # )
        
        if serializer.is_valid():
            #for message sending--------------------------------------------------------
            quotation = serializer.save()



            from messageapp.models import Conversation, Message
            from django.utils import timezone
            from datetime import timedelta
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync

            # 🔹 Get receiver & provider
            receiver = quotation.receiver
            provider = quotation.provider

            # 🔹 Get or create conversation
            conversation, created = Conversation.objects.get_or_create(
                receiver=receiver,
                provider=provider,
                defaults={
                    "conversation_status": "active",
                    "expires_at": timezone.now() + timedelta(hours=24)
                }
            )


            # Generate API endpoints for accept/reject
            quote_accept_url = f"{settings.BASE_URL}/offer/quotations/{quotation.id}/update-status/"
            quote_reject_url = f"{settings.BASE_URL}/offer/quotations/{quotation.id}/update-status/"


            message_text = f"""📄 New offer created for {receiver.user.name}

            Service: {quotation.service_description}
            Cost: ${quotation.service_cost}
            Platform Fee: ${quotation.platform_fee}
            Total Amount: ${quotation.total_amount}
            Timeline: {quotation.service_timeline}
            Urgency: {quotation.urgency_type}"""
            # 🔹 Save message
            message = Message.objects.create(
                conversation=conversation,
                sender=provider.user,
                message_text=message_text.strip()
            )

            # 🔹 Send WebSocket event
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"chat_{conversation.conversation_id}",
                {
                    "type": "chat_message",
                    "message_id": message.message_id,
                    "sender_id": str(provider.user.id),
                    "sender_name": provider.user.name,
                    # "message_text": message.message_text,
                    "message_text": message_text.strip(),  # ✅ Just the text
                    "message_image": None,
                    "message_file": None,
                    "created_at": message.created_at.isoformat(),
                    # ✅ Send quotation data separately
                    "quotation_id": quotation.id,
                    "quotation_status": quotation.quotation_status,
                    "accept_url": quote_accept_url,
                    "reject_url": quote_reject_url,
                    # "payment_link": quotation.payment_link,  # ✅ ADD THIS
                     "terms_conditions": quotation.terms_conditions  # ✅ ADD THIS
                }
            )
            #-------------------------------------------------------------
            # Return detailed view of created quotation
            detail_serializer = QuotationDetailSerializer(quotation)
            return Response(
                detail_serializer.data,
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @swagger_auto_schema(
        operation_description="Update quotation status (Receiver only - Accept/Decline)",
        request_body=QuotationUpdateStatusSerializer,
        responses={200: QuotationDetailSerializer()}
    )
    @action(detail=True, methods=['patch'], url_path='update-status')
    def update_status(self, request, pk=None):
        """
        Update quotation status - Only receiver can accept/decline
        """
        quotation = self.get_object()
        
        # Verify user is the receiver
        try:
            receiver = ReceiverProfile.objects.get(user=request.user)
            if quotation.receiver != receiver:
                return Response(
                    {"error": "You can only update quotations sent to you"},
                    status=status.HTTP_403_FORBIDDEN
                )
        except ReceiverProfile.DoesNotExist:
            return Response(
                {"error": "Only service receivers can update quotation status"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Update status
        serializer = QuotationUpdateStatusSerializer(
            quotation,
            data=request.data,
            partial=True
        )
        
        if serializer.is_valid():
            serializer.save()
            #----------------------------------------------------------
            # ✅ If quotation accepted → generate payment link + notify via WS
            if serializer.instance.quotation_status == 'accepted':
                quotation = serializer.instance

                try:
                    payment_link = stripe.PaymentLink.create(
                        line_items=[{
                            'price_data': {
                                'currency': 'usd',
                                'product_data': {
                                    'name': f'{quotation.service_category.category_name} - {quotation.service_description[:50]}',
                                },
                                'unit_amount': int(quotation.total_amount * 100),
                            },
                            'quantity': 1,
                        }],
                        metadata={
                            'quotation_id': quotation.id,
                            'provider_id': quotation.provider.id,
                            'receiver_id': quotation.receiver.receiver_id,
                        },
                        after_completion={
                            'type': 'redirect',
                            'redirect': {
                                'url': f'{settings.BASE_URL}/offer/payment/status/?status=success&quotation_id={quotation.id}',
                            }
                        },
                    )

                    quotation.payment_link = payment_link.url
                    quotation.save(update_fields=['payment_link'])
                    quotation.refresh_from_db()

                except stripe.error.StripeError as e:
                    print("Stripe error:", e)
                    payment_link = None


                from channels.layers import get_channel_layer
                from asgiref.sync import async_to_sync

                channel_layer = get_channel_layer()
                from messageapp.models import Conversation, Message
                from django.utils import timezone
                from datetime import timedelta
                from channels.layers import get_channel_layer
                from asgiref.sync import async_to_sync
                # 🔹 Get or create conversation
                conversation, created = Conversation.objects.get_or_create(
                    receiver=quotation.receiver,
                    provider=quotation.provider,
                    defaults={
                        "conversation_status": "active",
                        "expires_at":timezone.now()+ timedelta(hours=24)
                    }
                )
                async_to_sync(channel_layer.group_send)(
                    f"chat_{conversation.conversation_id}",
                    {
                        "type": "chat_message",
                        "message_id": None,
                        "sender_id": str(request.user.id),
                        "sender_name": request.user.name,
                        "message_text": "✅ Quotation accepted. Please proceed to payment.",
                        "created_at": quotation.updated_at.isoformat(),
                        "quotation_id": quotation.id,
                        "quotation_status": quotation.quotation_status,
                        "payment_status": quotation.payment_status,  # ✅ ADD THIS
                        "payment_link": quotation.payment_link,  # ✅ NOW SENT
                    }
                )

            detail_serializer = QuotationDetailSerializer(quotation)
            return Response(detail_serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


    @action(detail=False, methods=['get'], url_path='accepted-for-order')
    def accepted_for_order(self, request):
        """
        Provider-only API:
        Get accepted quotations of a specific receiver
        """
        user = request.user

        # ✅ Provider check
        try:
            provider = ProviderProfile.objects.get(user=user)
        except ProviderProfile.DoesNotExist:
            return Response(
                {"error": "Only providers can access this"},
                status=status.HTTP_403_FORBIDDEN
            )

        receiver_user_id = request.query_params.get('receiver_user_id')
        if not receiver_user_id:
            return Response(
                {"error": "receiver_user_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ✅ Fetch accepted quotations
        quotations = Quotation.objects.filter(
            provider=provider,
            receiver__user__id=receiver_user_id,
            quotation_status='accepted'
        ).select_related('receiver__user', 'service_category')

        serializer = AcceptedQuotationForOrderSerializer(quotations, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="Cancel quotation with reason (Receiver only - after acceptance)",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'cancellation_reason': openapi.Schema(type=openapi.TYPE_STRING, description='Reason for cancellation')
            },
            required=['cancellation_reason']
        ),
        responses={200: QuotationDetailSerializer()}
    )
    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel_quotation(self, request, pk=None):
        quotation = self.get_object()
        
        # Verify user is the receiver
        try:
            receiver = ReceiverProfile.objects.get(user=request.user)
            if quotation.receiver != receiver:
                return Response(
                    {"error": "You can only cancel quotations sent to you"},
                    status=status.HTTP_403_FORBIDDEN
                )
        except ReceiverProfile.DoesNotExist:
            return Response(
                {"error": "Only service receivers can cancel quotations"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if quotation is accepted (if not, just decline it)
        if quotation.quotation_status != 'accepted':
            return Response(
                {"error": "Quotation must be accepted to request cancellation. Use reject instead."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        cancellation_reason = request.data.get('cancellation_reason', '').strip()
        if not cancellation_reason:
            return Response(
                {"error": "Cancellation reason is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if order already created
        if Order.objects.filter(quotation=quotation).exists():
            return Response(
                {"error": "Order already created. Please use order cancellation instead."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update quotation with cancellation request (admin will review)
        quotation.quotation_status = 'declined'  # or add new status 'pending_cancellation'
        quotation.cancellation_reason = cancellation_reason
        quotation.save()
        
        # Notify provider via WebSocket
        from messageapp.models import Conversation, Message
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        
        try:
            conversation = Conversation.objects.get(
                receiver=receiver,
                provider=quotation.provider
            )
            
            message = Message.objects.create(
                conversation=conversation,
                sender=receiver.user,
                message_text=f"⚠️ Cancellation requested for quotation\nReason: {cancellation_reason}\nStatus: Pending admin review"
            )
            
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"chat_{conversation.conversation_id}",
                {
                    "type": "chat_message",
                    "message_id": message.message_id,
                    "sender_id": str(receiver.user.id),
                    "sender_name": receiver.user.name,
                    "message_text": message.message_text,
                    "message_image": None,
                    "message_file": None,
                    "created_at": message.created_at.isoformat()
                }
            )
        except Conversation.DoesNotExist:
            pass
        
        detail_serializer = QuotationDetailSerializer(quotation)
        return Response({
            "message": "Cancellation request submitted. Admin will review and respond.",
            "quotation": detail_serializer.data
        })


from django.utils import timezone
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from messageapp.models import Conversation

def payment_status(request):
    quotation_id = request.GET.get('quotation_id')
    status_param = request.GET.get('status', 'failed')

    if status_param == 'success' and quotation_id:
        try:
            quotation = Quotation.objects.select_related(
                'provider', 'receiver'
            ).get(id=quotation_id)

            # ✅ 1. Update DB
            quotation.payment_status = 'paid'
            quotation.save(update_fields=['payment_status'])

            # ✅ 2. FIND conversation
            conversation = Conversation.objects.get(
                provider=quotation.provider,
                receiver=quotation.receiver
            )

            # ✅ 3. SEND WebSocket update
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"chat_{conversation.conversation_id}",
                {
                    "type": "chat_message",
                    "message_id": None,
                    "sender_id": "system",
                    "sender_name": "System",
                    "message_text": "💰 Payment completed successfully",
                    "created_at": timezone.now().isoformat(),
                    "quotation_id": quotation.id,
                    "quotation_status": quotation.quotation_status,
                    "payment_status": "paid",
                    "payment_link": quotation.payment_link,
                }
            )

        except (Quotation.DoesNotExist, Conversation.DoesNotExist):
            pass

    return render(request, 'payment.html', {
        'status': status_param,
        'quotation_id': quotation_id
    })

class OrderViewSet(StandardResponseMixin,viewsets.ModelViewSet):
    """
    ViewSet for Order management
    Handles order creation, status updates, and payment processing
    """
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        """
        Optimized queryset with select_related and prefetch_related
        Prevents N+1 queries by eager loading related objects
        """
        user = self.request.user
        
        # Base queryset with optimized joins
        queryset = Order.objects.select_related(
            'provider__user',
            'receiver__user',
            'service_category',
            'quotation'
        )
        
        # Filter based on user role
        if user.role == 'provider':
            try:
                provider = ProviderProfile.objects.get(user=user)
                return queryset.filter(provider=provider)
            except ProviderProfile.DoesNotExist:
                return queryset.none()

        if user.role == 'receiver':
            try:
                receiver = ReceiverProfile.objects.get(user=user)
                return queryset.filter(receiver=receiver)
            except ReceiverProfile.DoesNotExist:
                return queryset.none()
        
        return queryset.none()
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return OrderListSerializer
        elif self.action == 'retrieve':
            return OrderDetailSerializer
        elif self.action == 'create':
            return OrderCreateSerializer
        return OrderDetailSerializer
    
    @swagger_auto_schema(
        operation_description="Get list of orders (filtered by user role)",
        manual_parameters=[
            openapi.Parameter('order_status', openapi.IN_QUERY, type=openapi.TYPE_STRING,
                            description="Filter by status: active, completed, cancelled, refunded"),
            openapi.Parameter('payment_status', openapi.IN_QUERY, type=openapi.TYPE_STRING,
                            description="Filter by payment: unpaid, paid, released, refunded"),
        ]
    )
    def list(self, request, *args, **kwargs):
        """
        List orders with optional filters
        Automatically filtered by user role
        """
        queryset = self.get_queryset()
        
        # Filter by order status
        order_status_filter = request.query_params.get('order_status', None)
        if order_status_filter:
            queryset = queryset.filter(order_status=order_status_filter)
        
        # Filter by payment status
        payment_status_filter = request.query_params.get('payment_status', None)
        if payment_status_filter:
            queryset = queryset.filter(payment_status=payment_status_filter)
        
        # Order by most recent first
        queryset = queryset.order_by('-created_at')
        
        # Paginate and return
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_description="Create order after quotation acceptance (Receiver only)",
        request_body=OrderCreateSerializer,
        responses={201: OrderDetailSerializer()}
    )
    
    def create(self, request, *args, **kwargs):

        try:
            provider = ProviderProfile.objects.get(user=request.user)
        except ProviderProfile.DoesNotExist:
            return Response(
                {"error": "Only service providers can create orders"},
                status=status.HTTP_403_FORBIDDEN
            )
        #--------------------------------------------------------------------
        # ✅ ADD THIS SECTION - Enhance description with AI
        data = request.data.copy()
        original_description = data.get('service_description', '')
        
        if original_description:
            # Get category name for context
            category_id = data.get('service_category')
            category_name = None
            if category_id:
                try:
                    from serviceproviderapp.models import ServiceCategory
                    category = ServiceCategory.objects.get(id=category_id)
                    category_name = category.category_name
                except:
                    pass
            
            # Enhance with AI
            enhanced_description = enhance_service_description(
                original_description=original_description,
                service_category=category_name,
                urgency_type=data.get('urgency_type', 'normal'),
                message_type='order'  # ✅ CHANGE THIS
            )
            data['service_description'] = enhanced_description
        
        # Continue with existing serializer logic
        serializer = self.get_serializer(
            data=data,  # ✅ Use enhanced data instead of request.data
            context={'provider': provider}
        )

        #--------------------------------------------------------------------
        # Create order
        # serializer = self.get_serializer(data=request.data,context={"request": request})
        
        if serializer.is_valid():
            order = serializer.save()

                # ✅ ADD THIS - Enhance order description AFTER save
            if order.service_description:
                enhanced_order_description = enhance_service_description(
                    original_description=order.service_description,  # From quotation
                    service_category=order.service_category.category_name,
                    urgency_type=order.urgency_type,
                    message_type='order'  # Different prompt
                )
                order.service_description = enhanced_order_description
                order.save(update_fields=['service_description'])

            from messageapp.models import Conversation, Message
            from django.utils import timezone
            from datetime import timedelta
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            # 🔹 1. Get or create conversation
            conversation, created = Conversation.objects.get_or_create(
                receiver=order.receiver,
                provider=order.provider,
                defaults={
                    "conversation_status": "active",
                    "expires_at": timezone.now() + timedelta(hours=24)
                }
            )

            # 🔹 2. Reactivate if expired
            if conversation.conversation_status == "expired":
                conversation.conversation_status = "active"
                conversation.expires_at = timezone.now() + timedelta(hours=24)
                conversation.save()

            # 🔹 3. Create inbox message (EXACT LIKE OFFER)
            message = Message.objects.create(
                conversation=conversation,
                sender=order.receiver.user,
                message_text=(
                    f"📦 New order received\n"
                    f"Service: {order.service_category}\n"
                    f"Amount: ${order.service_cost}"
                )
            )

            # 🔹 4. WebSocket broadcast (same group logic)
            channel_layer = get_channel_layer()
            complete_url = f"{settings.BASE_URL}/offer/orders/{order.order_id}/update-status/"
            cancel_url = f"{settings.BASE_URL}/offer/orders/{order.order_id}/update-status/"

            async_to_sync(channel_layer.group_send)(
                f"chat_{conversation.conversation_id}",
                {
                    "type": "chat_message",
                    "message_id": message.message_id,

                    "sender_id": str(message.sender.id),
                    "sender_name": message.sender.name,
                    "message_text": message.message_text,
                    "message_image": None,
                    "message_file": None,
                    "created_at": message.created_at.isoformat(),
                    "order_id": order.order_id,
                    "order_status": order.order_status,
                    "complete_url": complete_url,
                    "cancel_url": cancel_url,
                }
            )

            # Return detailed view
            detail_serializer = OrderDetailSerializer(order)
            return Response(
                detail_serializer.data,
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @swagger_auto_schema(
        operation_description="Update order status (Complete/Cancel)",
        request_body=OrderUpdateStatusSerializer,
        responses={200: OrderDetailSerializer()}
    )
    
    @action(detail=True, methods=['patch'], url_path='update-status')
    def update_status(self, request, pk=None):
        """
        Update order status
        Provider: can mark as completed
        Receiver: can cancel (with admin approval)
        """
        order = self.get_object()
        
        serializer = OrderUpdateStatusSerializer(
            order,
            data=request.data,
            partial=True
        )
        
        if serializer.is_valid():
            serializer.save()
            
            # Return detailed view
            detail_serializer = OrderDetailSerializer(order)
            return Response(detail_serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @swagger_auto_schema(
        operation_description="Create Stripe payment intent for order",
        request_body=PaymentIntentSerializer,
        responses={200: openapi.Response('Payment intent created', schema=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'client_secret': openapi.Schema(type=openapi.TYPE_STRING),
                'payment_intent_id': openapi.Schema(type=openapi.TYPE_STRING),
                'amount': openapi.Schema(type=openapi.TYPE_NUMBER),
            }
        ))}
    )

    @action(detail=True, methods=['patch'])
    def complete(self, request, pk=None):
        """Provider marks complete; admin releases (placeholder).
        Why: Update status; calc available_balance via signal."""
        order = self.get_object()
        if request.user != order.provider.user:
            return Response({"error": "Unauthorized."}, status=status.HTTP_403_FORBIDDEN)
        if order.order_status != 'active':
            return Response({"error": "Invalid status."}, status=status.HTTP_400_BAD_REQUEST)
        order.order_status = 'completed'
        order.completed_at = timezone.now()
        order.payment_status = 'released'  # Admin approval in prod.
        order.save()
        # Stripe transfer placeholder: stripe.Transfer.create(amount=order.provider_amount * 100, destination=order.provider.stripe_account_id)
        return Response(OrderSerializer(order).data)


    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Aggregate stats for provider.
        Why: Annotate/Sum for O(1) queries; scalable with indexes on status/created_at."""
        profile = ProviderProfile.objects.get(user=request.user)  # Assume linked.
        last_month = timezone.now() - timedelta(days=30)
        # Use annotations instead of loops.
        stats = Order.objects.filter(provider=profile).aggregate(
            total_hired=Count('id', filter=Q(order_status='active')),  # Accepted = active hires.
            total_earnings=Sum('provider_amount', filter=Q(order_status__in=['completed', 'active'])),
            available_balance=Sum('provider_amount', filter=Q(payment_status='hold')),
            last_month_earnings=Sum('provider_amount', filter=Q(created_at__gte=last_month, order_status='completed')),
            active_hires=Count('id', filter=Q(order_status='active')),
            canceled=Count('id', filter=Q(order_status='cancelled'))
        )
        # Hiring list: Paginated orders with receiver.
        hiring_list = Order.objects.filter(provider=profile).select_related('receiver__user').order_by('-created_at')[:10]  # Limit for perf; paginate if needed.
        hiring_serializer = OrderListSerializer(hiring_list, many=True)
        stats['hiring_list'] = hiring_serializer.data
        return Response(stats)
    
    @action(detail=False, methods=['post'], url_path='create-payment-intent')
    def create_payment_intent(self, request):
        serializer = PaymentIntentSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        order_id = serializer.validated_data['order_id']
        
        try:
            order = Order.objects.select_for_update().get(order_id=order_id)
            
            # Verify user is the receiver
            receiver = ReceiverProfile.objects.get(user=request.user)
            if order.receiver != receiver:
                return Response(
                    {"error": "You can only pay for your own orders"},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # CALCULATE AMOUNTS
            service_cost_cents = int(order.service_cost * 100)
            platform_fee_cents = int(order.platform_fee * 100)  # $0.99 or $2.99
            platform_commission_cents = int(order.platform_commission * 100)  # 5%
            provider_amount_cents = int(order.provider_amount * 100)
            total_amount_cents = int(order.total_amount * 100)
            
            # GET PROVIDER STRIPE ACCOUNT
            provider_stripe_account = order.provider.stripe_account_id
            if not provider_stripe_account:
                return Response(
                    {"error": "Provider has not connected Stripe account"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # CREATE PAYMENT INTENT WITH DESTINATION CHARGE
            payment_intent = stripe.PaymentIntent.create(
                amount=total_amount_cents,  # Client pays: service_cost + platform_fee
                currency='usd',
                payment_method_types=['card'],
                application_fee_amount=platform_fee_cents + platform_commission_cents,  # Admin gets: $0.99/$2.99 + 5%
                transfer_data={
                    'destination': provider_stripe_account,  # Provider gets: service_cost - 5%
                },
                metadata={
                    'order_id': order.order_id,
                    'service_cost': str(order.service_cost),
                    'platform_fee': str(order.platform_fee),
                    'platform_commission': str(order.platform_commission),
                    'provider_amount': str(order.provider_amount),
                }
            )
            
            # SAVE PAYMENT INTENT
            order.payment_intent_id = payment_intent.id
            order.save(update_fields=['payment_intent_id'])
            
            return Response({
                'client_secret': payment_intent.client_secret,
                'payment_intent_id': payment_intent.id,
                'total_amount': order.total_amount,
                'service_cost': order.service_cost,
                'platform_fee': order.platform_fee,
                'breakdown': {
                    'service_cost': str(order.service_cost),
                    'platform_fee': str(order.platform_fee),
                    'total': str(order.total_amount),
                    'provider_receives': str(order.provider_amount),
                    'platform_earns': str(order.platform_fee + order.platform_commission)
                }
            })
            
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)
        except ReceiverProfile.DoesNotExist:
            return Response({"error": "Only receivers can make payments"}, status=status.HTTP_403_FORBIDDEN)
        except stripe.error.StripeError as e:
            return Response({"error": f"Stripe error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='stripe-webhook', permission_classes=[])
    def stripe_webhook(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        webhook_secret = settings.STRIPE_WEBHOOK_SECRET
        print("Stripe webhook received")
        print(f"Stripe signature header present: {bool(sig_header)}")
        print(f"Payload size: {len(payload) if payload else 0}")
        
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        except ValueError as exc:
            print(f"Stripe webhook invalid payload: {exc}")
            return Response(status=status.HTTP_400_BAD_REQUEST)
        except stripe.error.SignatureVerificationError as exc:
            print(f"Stripe webhook signature verification failed: {exc}")
            return Response(status=status.HTTP_400_BAD_REQUEST)

        print(f"Stripe webhook event type: {event.get('type')}")
        
        # ✅ HANDLE PAYMENT LINK COMPLETION (checkout.session.completed)
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            quotation_id = session.get('metadata', {}).get('quotation_id')
            print(f"Payment Link completed. Quotation ID from metadata: {quotation_id}")
            
            if quotation_id:
                try:
                    quotation = Quotation.objects.get(id=quotation_id)
                    # Payment via payment link - quotation accepted implicitly
                    if quotation.quotation_status == 'sent':
                        quotation.quotation_status = 'accepted'

                        #quotation.save()
                                    # ✅ MARK PAYMENT AS PAID
                    quotation.payment_status = 'paid'
                    quotation.save(update_fields=['quotation_status', 'payment_status'])
                    print(
                        "Quotation marked paid via payment link. "
                        f"quotation_id={quotation.id}, quotation_status={quotation.quotation_status}, "
                        f"payment_status={quotation.payment_status}"
                    )
                except Quotation.DoesNotExist:
                    print(f"Quotation not found for payment link. quotation_id={quotation_id}")
                    pass
        
        # HANDLE PAYMENT INTENT SUCCESS
        if event['type'] == 'payment_intent.succeeded':
            payment_intent = event['data']['object']
            print(f"PaymentIntent succeeded. payment_intent_id={payment_intent.get('id')}")
            
            try:
                order = Order.objects.get(payment_intent_id=payment_intent['id'])
                order.payment_status = 'paid'
                order.save(update_fields=['payment_status'])
                print(
                    "Order marked paid via payment intent. "
                    f"order_id={order.order_id}, payment_status={order.payment_status}"
                )
                
                # CREATE TRANSACTION RECORD
                Transaction.objects.create(
                    order=order,
                    user=order.receiver.user,
                    stripe_account_id=order.provider.stripe_account_id,
                    amount=order.total_amount,
                    platform_fee=order.platform_fee + order.platform_commission,
                    provider_amount=order.provider_amount,
                    status='hold'
                )
                
            except Order.DoesNotExist:
                print(
                    "Order not found for payment intent. "
                    f"payment_intent_id={payment_intent.get('id')}"
                )
                pass
        
        return Response(status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        operation_description="Release payment to provider after work completion (Admin only)",
        responses={200: OrderDetailSerializer()}
    )

    @action(detail=True, methods=['post'], url_path='release-payment')
    def release_payment(self, request, pk=None):
        """
        Release payment to provider after work completion
        Admin action - funds transferred from hold to provider
        """
        order = self.get_object()
        
        # Check if user is admin (add proper admin check)
        if not request.user.is_staff:
            return Response(
                {"error": "Only admins can release payments"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Validate order can be released
        if order.order_status != 'completed':
            return Response(
                {"error": "Order must be completed before releasing payment"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if order.payment_status != 'paid':
            return Response(
                {"error": "Order has not been paid yet"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        with transaction.atomic():
            # FUNDS ALREADY TRANSFERRED TO PROVIDER VIA DESTINATION CHARGE
            # Just update status - no additional Stripe call needed
            order.payment_status = 'released'
            order.save(update_fields=['payment_status'])
            
            # UPDATE TRANSACTION
            Transaction.objects.filter(order=order).update(status='released')
        
        return Response(OrderDetailSerializer(order).data)
    
    @swagger_auto_schema(
        operation_description="Request order cancellation with reason (Receiver only)",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'reason': openapi.Schema(type=openapi.TYPE_STRING, description='Cancellation reason')
            },
            required=['reason']
        ),
        responses={200: OrderDetailSerializer()}
    )
    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel(self, request, pk=None):
        order = self.get_object()
        
        
        # Check if already cancelled
        if order.order_status == 'cancelled':
            return Response(
                {"error": "Order is already cancelled"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if completed
        if order.order_status == 'completed':
            return Response(
                {"error": "Cannot cancel completed order"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        cancellation_reason = request.data.get('reason', '').strip()
        if not cancellation_reason:
            return Response(
                {"error": "Cancellation reason is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # If payment not made yet, cancel directly
        if order.payment_status == 'unpaid':
            order.order_status = 'cancelled'
            order.cancelled_at = timezone.now()
            order.cancellation_reason = cancellation_reason
            order.cancellation_requested_by = 'receiver'
            order.cancellation_request_status = 'approved'
            order.save()
            
            return Response({
                "message": "Order cancelled successfully (no payment was made)",
                "order": OrderDetailSerializer(order).data
            })
        
        # If payment made, request admin approval
        order.cancellation_reason = cancellation_reason
        order.cancellation_requested_by = 'receiver'
        order.cancellation_request_status = 'pending'
        order.save()
        
        # Notify provider
        from messageapp.models import Conversation, Message
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        
        try:
            conversation = Conversation.objects.get(
                receiver=order.receiver,
                provider=order.provider
            )
            
            message = Message.objects.create(
                conversation=conversation,
                sender=receiver.user,
                message_text=f"⚠️ Order cancellation requested\nOrder ID: {order.order_id}\nReason: {cancellation_reason}\nStatus: Pending admin review"
            )
            
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"chat_{conversation.conversation_id}",
                {
                    "type": "chat_message",
                    "message_id": message.message_id,
                    "sender_id": str(receiver.user.id),
                    "sender_name": receiver.user.name,
                    "message_text": message.message_text,
                    "message_image": None,
                    "message_file": None,
                    "created_at": message.created_at.isoformat()
                }
            )
        except Conversation.DoesNotExist:
            pass
        
        return Response({
            "message": "Cancellation request submitted. Admin will review within 24-48 hours.",
            "order": OrderDetailSerializer(order).data
        })
    @swagger_auto_schema(
        operation_description="Provider cancels order (no reason required, auto-refund)",
        responses={200: OrderDetailSerializer()}
    )
    @action(detail=True, methods=['post'], url_path='provider-cancel')
    def provider_cancel(self, request, pk=None):
        order = self.get_object()
        
        # Check if user is the provider
        try:
            provider = ProviderProfile.objects.get(user=request.user)
            if order.provider != provider:
                return Response(
                    {"error": "Only the provider can cancel this order"},
                    status=status.HTTP_403_FORBIDDEN
                )
        except ProviderProfile.DoesNotExist:
            return Response(
                {"error": "Only providers can use this endpoint"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if already cancelled/completed
        if order.order_status in ['cancelled', 'completed']:
            return Response(
                {"error": f"Cannot cancel {order.order_status} order"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Cancel order
        order.order_status = 'cancelled'
        order.cancelled_at = timezone.now()
        order.cancellation_reason = "Cancelled by provider"
        order.cancellation_requested_by = 'provider'
        order.cancellation_request_status = 'approved'
        
        # If payment was made, process refund
        if order.payment_status == 'paid' and order.payment_intent_id:
            try:
                # Create refund in Stripe
                refund = stripe.Refund.create(
                    payment_intent=order.payment_intent_id,
                    reason='requested_by_customer',
                    metadata={
                        'order_id': order.order_id,
                        'cancelled_by': 'provider'
                    }
                )
                
                order.payment_status = 'refunded'
                
                # Update transaction
                Transaction.objects.filter(order=order).update(status='refunded')
                
            except stripe.error.StripeError as e:
                return Response(
                    {"error": f"Refund failed: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        order.save()
        
        # Notify receiver
        from messageapp.models import Conversation, Message
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        
        try:
            conversation = Conversation.objects.get(
                receiver=order.receiver,
                provider=order.provider
            )
            
            refund_text = " Your payment has been refunded." if order.payment_status == 'refunded' else ""
            
            message = Message.objects.create(
                conversation=conversation,
                sender=provider.user,
                message_text=f"❌ Order cancelled by provider\nOrder ID: {order.order_id}{refund_text}"
            )
            
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"chat_{conversation.conversation_id}",
                {
                    "type": "chat_message",
                    "message_id": message.message_id,
                    "sender_id": str(provider.user.id),
                    "sender_name": provider.user.name,
                    "message_text": message.message_text,
                    "message_image": None,
                    "message_file": None,
                    "created_at": message.created_at.isoformat()
                }
            )
        except Conversation.DoesNotExist:
            pass
        
        return Response({
            "message": "Order cancelled successfully" + (" and refund processed" if order.payment_status == 'refunded' else ""),
            "order": OrderDetailSerializer(order).data
        })


class ReviewViewSet(StandardResponseMixin,viewsets.ModelViewSet):
  """
  ViewSet for Review management
  Only receivers can create reviews for completed orders
  """
  permission_classes = [IsAuthenticated]
  pagination_class = StandardResultsSetPagination
  serializer_class = ReviewSerializer

  def get_queryset(self):
    """
    Optimized queryset with select_related
    Returns reviews based on user role
    """
    user = self.request.user
    
    # Base queryset with eager loading
    queryset = Review.objects.select_related(
        'provider__user',
        'receiver__user',
        'order'
    )
    
    # Filter based on user role
    if user.role == 'provider':
        try:
            provider = ProviderProfile.objects.get(user=user)
            # Provider sees reviews about them
            return queryset.filter(provider=provider).order_by('-created_at')
        except ProviderProfile.DoesNotExist:
            pass

    if user.role == 'receiver':
        try:
            receiver = ReceiverProfile.objects.get(user=user)
            # Receiver sees their own reviews
            return queryset.filter(receiver=receiver).order_by('-created_at')
        except ReceiverProfile.DoesNotExist:
            pass
    
    return queryset.none()

  @swagger_auto_schema(
      operation_description="Create review for completed order (Receiver only)",
      request_body=ReviewSerializer,
      responses={201: ReviewSerializer()}
  )
  def create(self, request):
    """
    Create review - Only receiver can review completed orders
    """
    # Verify user is a receiver
    try:
        receiver = ReceiverProfile.objects.get(user=request.user)
    except ReceiverProfile.DoesNotExist:
        return Response(
            {"error": "Only service receivers can create reviews"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = self.get_serializer(data=request.data)
    
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

  # ✅ FIXED: This should be at class level, NOT inside create()
  @swagger_auto_schema(
      operation_description="Get reviews for a specific provider by user ID",
      manual_parameters=[
          openapi.Parameter('provider_user_id', openapi.IN_QUERY, type=openapi.TYPE_STRING, 
                          description="Provider's user UUID", required=True),
      ],
      responses={200: ReviewSerializer(many=True)}
  )
  @action(detail=False, methods=['get'], url_path='by-provider-user')
  def by_provider_user(self, request):
      """
      Get all reviews for a specific provider using their user ID
      Public endpoint - anyone can view reviews
      """
      provider_user_id = request.query_params.get('provider_user_id')
      
      if not provider_user_id:
          return Response(
              {"error": "provider_user_id parameter is required"},
              status=status.HTTP_400_BAD_REQUEST
          )
      
      # Find provider by user UUID
      try:
          provider = ProviderProfile.objects.get(user__id=provider_user_id)
      except ProviderProfile.DoesNotExist:
          return Response(
              {"error": "Provider not found"},
              status=status.HTTP_404_NOT_FOUND
          )
      
      # Get all reviews for this provider
      queryset = Review.objects.filter(
          provider=provider
      ).select_related(
          'receiver__user',
          'order'
      ).order_by('-created_at')
      
      # Paginate results
      page = self.paginate_queryset(queryset)
      if page is not None:
          serializer = self.get_serializer(page, many=True)
          return self.get_paginated_response(serializer.data)
      
      serializer = self.get_serializer(queryset, many=True)
      return Response(serializer.data)


class ProviderDashboardViewSet(StandardResponseMixin,viewsets.ViewSet):
    """
    ViewSet for provider dashboard analytics
    Earnings, hiring list, statistics
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Get provider earnings dashboard",
        responses={200: ProviderEarningsSerializer()}
    )
    
    
    @action(detail=False, methods=['get'], url_path='earnings')
    def earnings(self, request):
        """
        Get provider earnings dashboard
        Shows: total earnings, available balance, last month earnings,
               active hires, cancelled works
        Efficient aggregation queries - O(1) complexity
        """
        try:
            provider = ProviderProfile.objects.get(user=request.user)
        except ProviderProfile.DoesNotExist:
            return Response(
                {"error": "Provider profile not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Calculate last month date range
        today = timezone.now()
        last_month_start = today - timedelta(days=30)
        
        # Efficient aggregation using single query with annotations
        # Uses COUNT and SUM aggregations - O(1) database operations
        stats = Order.objects.filter(
            provider=provider
        ).aggregate(
            # Total earnings from all completed orders
            total_earnings=Sum(
                'provider_amount',
                filter=Q(order_status='completed')
            ),
            # Earnings from last 30 days
            last_month_earnings=Sum(
                'provider_amount',
                filter=Q(
                    order_status='completed',
                    completed_at__gte=last_month_start
                )
            ),
            # Count of active orders
            active_hires=Count(
                'order_id',
                filter=Q(order_status='active')
            ),
            # Count of cancelled orders
            cancelled_works=Count(
                'order_id',
                filter=Q(order_status='cancelled')
            )
        )
        
        # Prepare response data
        data = {
            'total_earnings': stats['total_earnings'] or Decimal('0.00'),
            'available_balance': provider.provider_available_balance,
            'last_month_earnings': stats['last_month_earnings'] or Decimal('0.00'),
            'active_hires': stats['active_hires'],
            'cancelled_works': stats['cancelled_works'],
            'total_hired': provider.provider_total_hired,
            'rating':provider.provider_rating,
        }
        
        serializer = ProviderEarningsSerializer(data=data)
        serializer.is_valid()
        
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_description="Get hiring list for provider",
        manual_parameters=[
            openapi.Parameter('order_status', openapi.IN_QUERY, type=openapi.TYPE_STRING,
                            description="Filter by status: active, completed, cancelled"),
        ],
        responses={200: HiringListSerializer(many=True)}
    )
   
    @action(detail=False, methods=['get'], url_path='hiring-list')
    def hiring_list(self, request):
        """
        Provider → sees receivers who hired them
        Receiver → sees providers they hired
        """
        
        hiring_data = None  # ✅ INITIALIZE THIS
        
        # Step 1: Check if user is Provider
        try:
            provider = ProviderProfile.objects.get(user=request.user)
            queryset = Order.objects.filter(provider=provider).select_related(
                'receiver__user',
                'service_category'
            )
            
            order_status_filter = request.query_params.get('order_status', None)
            if order_status_filter:
                queryset = queryset.filter(order_status=order_status_filter)
            
            queryset = queryset.order_by('-created_at')
            
            hiring_data = [
                {
                    'receiver_id': order.receiver.receiver_id,
                    'receiver_name': order.receiver.user.username,
                    'receiver_image': None,
                    'service_category': order.service_category.category_name,
                    'order_status': order.order_status,
                    'payment_status': order.payment_status,
                    'service_cost': order.service_cost,
                    'provider_amount': order.provider_amount,
                    'order_date': order.created_at,
                    'completed_at': order.completed_at
                }
                for order in queryset
            ]
            
        except ProviderProfile.DoesNotExist:
            # Step 2: Check if user is Receiver
            try:
                receiver = ReceiverProfile.objects.get(user=request.user)
                queryset = Order.objects.filter(receiver=receiver).select_related(
                    'provider__user',
                    'service_category'
                )
                
                order_status_filter = request.query_params.get('order_status', None)
                if order_status_filter:
                    queryset = queryset.filter(order_status=order_status_filter)
                
                queryset = queryset.order_by('-created_at')
                
                hiring_data = [
                    {
                        'provider_id': order.provider.id,
                        'provider_name': order.provider.user.username,
                        'provider_image': None,
                        'service_category': order.service_category.category_name,
                        'order_status': order.order_status,
                        'payment_status': order.payment_status,
                        'service_cost': order.service_cost,
                        'provider_amount': order.provider_amount,
                        'order_date': order.created_at,
                        'completed_at': order.completed_at
                    }
                    for order in queryset
                ]
                
            except ReceiverProfile.DoesNotExist:
                return Response(
                    {"error": "User is neither provider nor receiver"}, 
                    status=status.HTTP_403_FORBIDDEN
                )
        
        # ✅ CHECK IF DATA WAS POPULATED
        if hiring_data is None:
            return Response(
                {"error": "User is neither provider nor receiver"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = HiringListSerializer(data=hiring_data, many=True)
        serializer.is_valid()
        return Response(serializer.data)

