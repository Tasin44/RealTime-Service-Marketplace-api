
from rest_framework import serializers
from django.db import transaction
from decimal import Decimal
from .models import Quotation, Order, Review, Transaction
from serviceproviderapp.models import ProviderProfile, ServiceCategory
from servicereceiverapp.models import ReceiverProfile
from django.contrib.auth.models import User
from django.conf import settings
PLATFORM_COMMISSION = Decimal('0.05')  # 5% commission


def _absolute_media_url(request, file_field):
    if not file_field:
        return None
    if request:
        return request.build_absolute_uri(file_field.url)
    return f"{settings.BASE_URL.rstrip('/')}{file_field.url}"




class ServiceCategorySerializer(serializers.ModelSerializer):
    """Serializer for ServiceCategory - simple and efficient"""
    category_image = serializers.SerializerMethodField()
    class Meta:
        model = ServiceCategory
        fields = ['category_name', 'category_image', 'created_at']
        read_only_fields = ['created_at']
        
    def get_category_image(self, obj):
        request = self.context.get('request')
        return _absolute_media_url(request, obj.category_image)
    
class ProviderBasicSerializer(serializers.ModelSerializer):
    """Basic provider info to avoid circular imports and N+1"""
    user_id = serializers.UUIDField(source='user.id', read_only=True)
    user_name = serializers.CharField(source='user.name', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_image = serializers.SerializerMethodField()
    
    class Meta:
        model = ProviderProfile
        # fields = ['id','user_name', 'user_email', 'user_image', 'service_title', 'provider_rating']
        fields = [
            'user_id',
            'user_name',
            'user_email',
            'user_image',
            'service_title',
            'provider_rating',
        ]
    def get_user_image(self, obj):
        """Get user image from User model if exists"""
        # Assuming you have image field in User model or custom user model
        return None  # Replace with actual user image logic

class ReceiverBasicSerializer(serializers.ModelSerializer):
    """Basic receiver info to avoid circular imports and N+1"""
    user_id = serializers.UUIDField(source='user.id', read_only=True)
    user_name = serializers.CharField(source='user.name', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_image = serializers.SerializerMethodField()
    
    class Meta:
        model = ReceiverProfile
        # fields = ['receiver_id', 'user_name', 'user_email', 'user_image']
        fields = ['user_id', 'user_name', 'user_email', 'user_image']
    
    def get_user_image(self, obj):
        """Get user image from User model if exists"""
        return None  # Replace with actual user image logic



class QuotationListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for quotation list - prevents N+1 with select_related"""
    provider_name = serializers.CharField(source='provider.user.username', read_only=True)
    receiver_name = serializers.CharField(source='receiver.user.username', read_only=True)
    category_name = serializers.CharField(source='service_category.category_name', read_only=True)
    provider_user_id = serializers.UUIDField(source='provider.user.id', read_only=True)
    receiver_user_id = serializers.UUIDField(source='receiver.user.id', read_only=True)
    class Meta:
        model = Quotation
        fields = [
            'id','provider_user_id',
            'receiver_user_id','provider_name', 'receiver_name', 'category_name',
            'service_cost', 'service_timeline', 'quotation_status', 'payment_status','created_at'
        ]

class QuotationDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for single quotation view"""
    provider = ProviderBasicSerializer(read_only=True)
    receiver = ReceiverBasicSerializer(read_only=True)
    service_category = ServiceCategorySerializer(read_only=True)

    class Meta:
        model = Quotation
        fields = [
            "id",'provider', 'receiver', 'service_category',
            'service_description', 'service_cost', 'service_timeline',
            'terms_conditions', 'quotation_status', 
            'payment_link',  # ✅ ADD THIS
            'payment_status',
            'created_at', 'updated_at'
        ]


class QuotationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating quotations - only provider can create"""
    receiver_user_id = serializers.UUIDField(write_only=True) # receiver unique user id
    class Meta:
        model = Quotation
        fields = [
            'id','receiver_user_id', 'service_category', 'service_description',
            'service_cost', 'service_timeline', 'terms_conditions','urgency_type'  # ADD THIS
        ]

    def validate_receiver_user_id(self, value):
        try:
            receiver = ReceiverProfile.objects.get(user__id=value)
        except ReceiverProfile.DoesNotExist:
            raise serializers.ValidationError("Receiver not found")
        return receiver
    def validate_service_cost(self, value):
        """Validate service cost is positive"""
        if value <= 0:
            raise serializers.ValidationError("Service cost must be greater than 0")
        return value
    
    def validate_receiver(self, value):
        """Check if receiver profile exists and is active"""
        if not ReceiverProfile.objects.filter(receiver_id=value.receiver_id).exists():
            raise serializers.ValidationError("Invalid receiver profile")
        return value
    
    '''
    def validate_service_category(self, value):
        """Check if category exists"""
        if not ServiceCategory.objects.filter(category_id=value.category_id).exists():
            raise serializers.ValidationError("Invalid service category")
        return value
    '''

    def create(self, validated_data):
        """Create quotation with provider from context"""
        # Provider comes from authenticated user in view
        provider = self.context['provider']
        validated_data['provider'] = provider

        receiver = validated_data.pop('receiver_user_id')
        validated_data['receiver'] = receiver

        validated_data['quotation_status'] = 'sent'

        # CALCULATE PLATFORM FEE BASED ON URGENCY
        urgency_type = validated_data.get('urgency_type', 'normal')
        if urgency_type == 'urgent':
            validated_data['platform_fee'] = Decimal('2.99')
        else:
            validated_data['platform_fee'] = Decimal('0.99')

        # CALCULATE TOTAL AMOUNT
        validated_data['total_amount'] = validated_data['service_cost'] + validated_data['platform_fee']
    # ✅ AUTO-POPULATE FIXED TERMS
        FIXED_TERMS = """
        TERMS & CONDITIONS:

        1. Payment Structure:
        - Service Cost: As quoted by provider
        - Platform Fee: $0.99 (Normal) / $2.99 (Urgent)
        - Total Amount: Service Cost + Platform Fee

        2. Payment Hold Policy:
        - All amounts will be temporarily held in escrow
        - Funds will be released to the provider ONLY when the service is completed successfully
        - The receiver must approve completion before payment release

        3. Commission:
        - Platform charges 5% commission from the provider's service cost
        - Provider receives: Service Cost - 5% commission

        4. Cancellation Policy:
        - Receiver can cancel before payment with no penalty
        - After payment, cancellation requires admin approval with valid reason
        - Provider can cancel anytime (money will be refunded to receiver)

        5. Dispute Resolution:
        - All disputes will be reviewed by platform admin
        - Refunds processed within 5-7 business days after approval

        By accepting this quotation, both parties agree to these terms.
            """.strip()
        
        # Only set if not already provided
        if not validated_data.get('terms_conditions'):
            validated_data['terms_conditions'] = FIXED_TERMS

        # Create quotation
        quotation = Quotation.objects.create(**validated_data)
        return quotation

class QuotationUpdateStatusSerializer(serializers.ModelSerializer):
    """Serializer for updating quotation status (accept/decline by receiver)"""
    
    class Meta:
        model = Quotation
        fields = ['quotation_status']
    
    def validate_quotation_status(self, value):
        """Only allow accepted or declined status"""
        if value not in ['accepted', 'declined']:
            raise serializers.ValidationError("Status must be 'accepted' or 'declined'")
        return value
    
    def update(self, instance, validated_data):
        """Update quotation status"""
        # Only allow status change if current status is 'sent'
        if instance.quotation_status != 'sent':
            raise serializers.ValidationError("Quotation has already been processed")
        
        instance.quotation_status = validated_data['quotation_status']
        instance.save()
        
        return instance


class AcceptedQuotationForOrderSerializer(serializers.ModelSerializer):
    quotation_id = serializers.UUIDField(source='id', read_only=True)
    receiver_user_id = serializers.UUIDField(source='receiver.user.id', read_only=True)

    class Meta:
        model = Quotation
        fields = [
            'quotation_id',
            'receiver_user_id',
            'service_category',
            'service_cost',
            'payment_status',
            'service_timeline',
            'created_at',
        ]

class OrderListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for order list"""
    provider_name = serializers.CharField(source='provider.user.username', read_only=True)
    receiver_name = serializers.CharField(source='receiver.user.username', read_only=True)
    receiver_image = serializers.SerializerMethodField()
    category_name = serializers.CharField(source='service_category.category_name', read_only=True)
    quotation_id = serializers.IntegerField(source='quotation.id', read_only=True)

    class Meta:
        model = Order
        fields = [
            'order_id', 'quotation_id', 'provider_name', 'receiver_name', 'receiver_image',
            'category_name', 'service_cost', 'provider_amount', 
            'order_status', 'payment_status', 'created_at', 'completed_at'
        ]
    
    def get_receiver_image(self, obj):
        """Get receiver image"""
        return None  # Replace with actual image logic

class OrderDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for single order view"""
    provider = ProviderBasicSerializer(read_only=True)
    receiver = ReceiverBasicSerializer(read_only=True)
    service_category = ServiceCategorySerializer(read_only=True)
    quotation_id = serializers.IntegerField(source='quotation.id', read_only=True)

    # quotation_id = serializers.IntegerField(source='quotation.quotation_id', read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'order_id', 'quotation_id', 'provider', 'receiver', 'service_category',
            'service_description', 'service_cost', 'service_time_taken', 'provider_amount', 'order_status',
            'payment_intent_id', 'payment_status', 'completed_at',
            'cancelled_at', 'cancellation_reason', 
            'urgency_type', 'platform_fee', 'total_amount',  
            'cancellation_requested_by', 'cancellation_request_status',  # ✅ ADD THESE
            'created_at', 'updated_at'
        ]

class OrderCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating order after quotation acceptance"""
    
    class Meta:
        model = Order
        # fields = [
        #     'quotation', 'service_category', 'service_description',
        #     'service_cost', 'service_time_taken'
        # ]
        fields = [
            "quotation",
            "service_time_taken",
        ]
    
    def validate_quotation(self, value):
        """Validate quotation exists and is accepted"""

        if value.quotation_status != 'accepted':
            raise serializers.ValidationError(
                "Quotation must be accepted before creating order"
        ) 

        if Order.objects.filter(quotation=value).exists():
            raise serializers.ValidationError("Order already exists for this quotation")
        
        return value
    
    
    @transaction.atomic  # Ensure all DB operations are atomic
    def create(self, validated_data):
        """
        Create order with automatic commission calculation
        Uses database transaction to ensure data consistency
        """
        quotation = validated_data['quotation']
        # service_cost = validated_data['service_cost']
        service_cost = quotation.service_cost
        
        # Calculate platform commission (5%)
        # platform_commission = service_cost * PLATFORM_COMMISSION_RATE

        #new_23th dec--------------------------------------------------\
        platform_commission = service_cost * Decimal('0.05')
        provider_amount = service_cost - platform_commission
        

        # GET PLATFORM FEE FROM QUOTATION
        platform_fee = quotation.platform_fee  # $0.99 or $2.99
        total_amount = service_cost + platform_fee        
        #---------------------------------------------------------------/    

        # Create order with all required fields
        order = Order.objects.create(
            quotation=quotation,
            receiver=quotation.receiver,
            provider=quotation.provider,
            # service_category=validated_data['service_category'],
            # service_description=validated_data['service_description'],
            service_category=quotation.service_category,#changed because everything will be now copied from quotetion
            service_description=quotation.service_description,
            service_cost=service_cost,
            service_time_taken=validated_data.get('service_time_taken', ''),

            #new_23th dec--------------------------------------------------\
            urgency_type=quotation.urgency_type,  # ADD
            platform_fee=platform_fee,  # ADD
            total_amount=total_amount,  # ADD
            platform_commission=platform_commission,  # 5% of service_cost
            #---------------------------------------------------------------/    
            provider_amount=provider_amount,
            order_status='active',
            payment_status='unpaid'
        )
        
        return order

class OrderUpdateStatusSerializer(serializers.Serializer):
    """Serializer for updating order status"""
    order_status = serializers.ChoiceField(
        choices=['active', 'completed', 'cancelled', 'refunded']
    )
    cancellation_reason = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, data):
        """Validate cancellation reason is provided for cancelled orders"""
        if data.get('order_status') == 'cancelled' and not data.get('cancellation_reason'):
            raise serializers.ValidationError({
                'cancellation_reason': 'Cancellation reason is required when cancelling order'
            })
        return data
    
    @transaction.atomic  # Atomic transaction for status update
    def update(self, instance, validated_data):
        """
        Update order status with proper validations
        Updates provider statistics when order is completed
        """
        new_status = validated_data['order_status']
        old_status = instance.order_status
        
        # Validate status transitions
        if old_status == 'completed' and new_status != 'completed':
            raise serializers.ValidationError("Cannot change status of completed order")
        
        if old_status == 'refunded':
            raise serializers.ValidationError("Cannot change status of refunded order")
        
        # Update order status
        instance.order_status = new_status
        
        # Set timestamps based on status
        from django.utils import timezone
        if new_status == 'completed':
            instance.completed_at = timezone.now()
            
            # Update provider statistics (total_hired, total_earnings)
            provider = instance.provider
            provider.provider_total_hired += 1
            provider.provider_total_earnings += instance.provider_amount
            provider.save(update_fields=['provider_total_hired', 'provider_total_earnings'])
            
        elif new_status == 'cancelled':
            instance.cancelled_at = timezone.now()
            instance.cancellation_reason = validated_data.get('cancellation_reason', '')
        
        instance.save()
        
        return instance

class PaymentIntentSerializer(serializers.Serializer):
    """Serializer for creating Stripe payment intent"""
    order_id = serializers.IntegerField()
    
    def validate_order_id(self, value):
        """Validate order exists and is unpaid"""
        try:
            order = Order.objects.get(order_id=value)
            if order.payment_status != 'unpaid':
                raise serializers.ValidationError("Order has already been paid")
            return value
        except Order.DoesNotExist:
            raise serializers.ValidationError("Order not found")

class ReviewSerializer(serializers.ModelSerializer):
    """Serializer for creating and viewing reviews"""
    # ✅ INPUT (request)
    provider_user_uuid = serializers.UUIDField(write_only=True) 


    # ✅ OUTPUT (response)
    provider_user_id = serializers.UUIDField(
        source='provider.user.id', read_only=True
    )
    receiver_user_id = serializers.UUIDField(
        source='receiver.user.id', read_only=True
    )
    provider_name = serializers.CharField(source='provider.user.name', read_only=True)
    receiver_name = serializers.CharField(source='receiver.user.name', read_only=True)
    receiver_image = serializers.SerializerMethodField()
    quotation_id = serializers.IntegerField(source='quotation.id', read_only=True)

    class Meta:
        model = Review
        # fields = [
        #     'id',  'provider_user_id','receiver_user_id','provider', 'receiver', 'order', 'provider_name',
        #     'receiver_name', 'rating', 'review_text', 'created_at'
        # ]
        fields = [
            'id',
            'quotation_id',
            'provider_user_uuid',   # input only
            'provider_user_id',     # output only
            'receiver_user_id',
            'provider',
            'receiver',
            'order',
            'provider_name',
            'receiver_name',
            'receiver_image',
            'rating',
            'review_text',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'provider', 'receiver']

    def validate_provider_user_uuid(self, value):
        try:
            provider = ProviderProfile.objects.get(user__id=value)
        except ProviderProfile.DoesNotExist:
            raise serializers.ValidationError("Provider not found")
        return provider

    def validate_rating(self, value):
        """Validate rating is between 1 and 5"""
        if value < 1 or value > 5:
            raise serializers.ValidationError("Rating must be between 1 and 5")
        return value
    
    def validate(self, data):
        """Validate order exists, is completed, and not already reviewed"""
        order = data.get('order')
        
        if order.order_status != 'completed':
            raise serializers.ValidationError("Can only review completed orders")
        
        # Check if review already exists for this order
        if Review.objects.filter(order=order).exists():
            raise serializers.ValidationError("Review already exists for this order")
        
        return data
    
    def get_receiver_image(self, obj):
        request = self.context.get('request')
        return _absolute_media_url(request, obj.receiver.user.image)
    
    @transaction.atomic  # Atomic transaction for review creation
    def create(self, validated_data):
        """
        Create review and update provider rating
        Uses efficient aggregation to recalculate average rating
        """
        #provider = validated_data.pop('provider_user_id')
        provider = validated_data.pop('provider_user_uuid')
        order = validated_data['order']
        #review = Review.objects.create(**validated_data)

        review = Review.objects.create(
            provider=provider,              # ✅ REQUIRED
            receiver=order.receiver,        # ✅ REQUIRED
            **validated_data
        )
        
        # Recalculate provider average rating using aggregation (efficient)
        from django.db.models import Avg

        #provider = validated_data['provider']

        avg_rating = Review.objects.filter(
            provider=provider
        ).aggregate(avg=Avg('rating'))['avg']
        
        # Update provider rating and done work count
        provider.provider_rating = round(avg_rating, 2) if avg_rating else 0
        provider.provider_done_work = Review.objects.filter(provider=provider).count()
        provider.save(update_fields=['provider_rating', 'provider_done_work'])
        
        return review

class TransactionSerializer(serializers.ModelSerializer):
    """Serializer for transaction records"""
    order_id = serializers.IntegerField(source='order.order_id', read_only=True)
    user_name = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = Transaction
        fields = [
            'transaction_id', 'order_id', 'user', 'user_name',
            'stripe_account_id', 'amount', 'platform_fee',
            'provider_amount', 'status', 'created_at'
        ]
        read_only_fields = ['transaction_id', 'created_at']

class ProviderEarningsSerializer(serializers.Serializer):
    """Serializer for provider earnings dashboard"""
    total_earnings = serializers.DecimalField(max_digits=12, decimal_places=2)
    available_balance = serializers.DecimalField(max_digits=12, decimal_places=2)
    last_month_earnings = serializers.DecimalField(max_digits=12, decimal_places=2)
    active_hires = serializers.IntegerField()
    cancelled_works = serializers.IntegerField()
    total_hired = serializers.IntegerField()


class HiringListSerializer(serializers.Serializer):
    """Serializer for hiring list (providers hired by receivers)"""

    service_category = serializers.CharField()
    order_status = serializers.CharField()
    payment_status = serializers.CharField()
    service_cost = serializers.DecimalField(max_digits=10, decimal_places=2)
    provider_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    order_date = serializers.DateTimeField()
    completed_at = serializers.DateTimeField(allow_null=True)

    # Provider view fields (receiver info)
    receiver_id = serializers.IntegerField(required=False, allow_null=True)
    receiver_name = serializers.CharField(required=False, allow_null=True)
    receiver_image = serializers.CharField(required=False, allow_null=True)
    
    # Receiver view fields (provider info) - ADD THESE
    provider_id = serializers.IntegerField(required=False, allow_null=True)
    provider_name = serializers.CharField(required=False, allow_null=True)
    provider_image = serializers.CharField(required=False, allow_null=True)




