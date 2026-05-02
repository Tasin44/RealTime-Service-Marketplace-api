from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    ServiceCategory, ProviderProfile, ProviderKeyword, ProviderWorkImage,
    ProviderDocument
)
from django.contrib.auth import get_user_model
from django.conf import settings 
User = get_user_model()


def _absolute_media_url(request, file_field):
    if not file_field:
        return None
    if request:
        return request.build_absolute_uri(file_field.url)
    return f"{settings.BASE_URL.rstrip('/')}{file_field.url}"



ALLOWED_COUNTRIES = [
    'Afghanistan', 'Albania', 'Algeria', 'Andorra', 'Angola', 'Antigua and Barbuda', 'Argentina', 'Armenia', 'Australia', 'Austria',
    'Azerbaijan', 'Bahamas', 'Bahrain', 'Bangladesh', 'Barbados', 'Belarus', 'Belgium', 'Belize', 'Benin', 'Bhutan',
    'Bolivia', 'Bosnia and Herzegovina', 'Botswana', 'Brazil', 'Brunei', 'Bulgaria', 'Burkina Faso', 'Burundi', 'Cabo Verde', 'Cambodia',
    'Cameroon', 'Canada', 'Central African Republic', 'Chad', 'Chile', 'China', 'Colombia', 'Comoros', 'Congo (Congo-Brazzaville)', 'Costa Rica',
    'Côte d’Ivoire', 'Croatia', 'Cuba', 'Cyprus', 'Czechia', 'Democratic Republic of the Congo', 'Denmark', 'Djibouti', 'Dominica', 'Dominican Republic',
    'Ecuador', 'Egypt', 'El Salvador', 'Equatorial Guinea', 'Eritrea', 'Estonia', 'Eswatini', 'Ethiopia', 'Fiji', 'Finland',
    'France', 'Gabon', 'Gambia', 'Georgia', 'Germany', 'Ghana', 'Greece', 'Grenada', 'Guatemala', 'Guinea',
    'Guinea-Bissau', 'Guyana', 'Haiti', 'Honduras', 'Hungary', 'Iceland', 'India', 'Indonesia', 'Iran', 'Iraq',
    'Ireland', 'Israel', 'Italy', 'Jamaica', 'Japan', 'Jordan', 'Kazakhstan', 'Kenya', 'Kiribati', 'Kuwait',
    'Kyrgyzstan', 'Laos', 'Latvia', 'Lebanon', 'Lesotho', 'Liberia', 'Libya', 'Liechtenstein', 'Lithuania', 'Luxembourg',
    'Madagascar', 'Malawi', 'Malaysia', 'Maldives', 'Mali', 'Malta', 'Marshall Islands', 'Mauritania', 'Mauritius', 'Mexico',
    'Micronesia', 'Moldova', 'Monaco', 'Mongolia', 'Montenegro', 'Morocco', 'Mozambique', 'Myanmar', 'Namibia', 'Nauru',
    'Nepal', 'Netherlands', 'New Zealand', 'Nicaragua', 'Niger', 'Nigeria', 'North Korea', 'North Macedonia', 'Norway', 'Oman',
    'Pakistan', 'Palau', 'Panama', 'Papua New Guinea', 'Paraguay', 'Peru', 'Philippines', 'Poland', 'Portugal', 'Qatar',
    'Romania', 'Russia', 'Rwanda', 'Saint Kitts and Nevis', 'Saint Lucia', 'Saint Vincent and the Grenadines', 'Samoa', 'San Marino', 'Sao Tome and Principe', 'Saudi Arabia',
    'Senegal', 'Serbia', 'Seychelles', 'Sierra Leone', 'Singapore', 'Slovakia', 'Slovenia', 'Solomon Islands', 'Somalia', 'South Africa',
    'South Korea', 'South Sudan', 'Spain', 'Sri Lanka', 'Sudan', 'Suriname', 'Sweden', 'Switzerland', 'Syria', 'Taiwan',
    'Tajikistan', 'Tanzania', 'Thailand', 'Timor-Leste', 'Togo', 'Tonga', 'Trinidad and Tobago', 'Tunisia', 'Turkey', 'Turkmenistan',
    'Tuvalu', 'Uganda', 'Ukraine', 'United Arab Emirates', 'United Kingdom', 'United States', 'Uruguay', 'Uzbekistan', 'Vanuatu', 'Vatican City',
    'Venezuela', 'Vietnam', 'Yemen', 'Zambia', 'Zimbabwe'
]
class UserImageField(serializers.ImageField):
    def to_representation(self, value):
        request = self.context.get("request")
        return _absolute_media_url(request, value)

class UserSerializer(serializers.ModelSerializer):
  
    """Basic serializer for User model (name, email). Used in nested provider/receiver profiles.
    Why: Avoid exposing password; keep lightweight for scalability."""
    image = UserImageField(read_only=True)
    class Meta:
        model = User
        fields = ['id', 'name', 'email', 'image']
        read_only_fields = ['id', 'name', 'email']  # Prevent updates to core auth fields.


    

class ServiceCategorySerializer(serializers.ModelSerializer):
    """Serializer for ServiceCategory - simple and efficient"""
    category_image = serializers.SerializerMethodField()
    #category_id=serializers.IntegerField(readonly=True)
    class Meta:
        model = ServiceCategory
        fields = ['id','category_name', 'category_image', 'created_at']
        read_only_fields = ['created_at']
        
    def get_category_image(self, obj):
        request = self.context.get('request')
        return _absolute_media_url(request, obj.category_image)



class ProviderKeywordSerializer(serializers.ModelSerializer):
    """Serializer for provider keywords/tags"""
    class Meta:
        model = ProviderKeyword
        fields = ['id', 'keyword']
        read_only_fields = ['id']

class ProviderWorkImageSerializer(serializers.ModelSerializer):
    """Serializer for provider work images/portfolio"""
    class Meta:
        model = ProviderWorkImage
        fields = ['id', 'image', 'created_at']
        read_only_fields = ['id', 'created_at']

class ProviderDocumentSerializer(serializers.ModelSerializer):
    """Serializer for KYC documents"""
    class Meta:
        model = ProviderDocument
        fields = [
            'document_type', 'document_front', 
            'verification_id', 'status', 'uploaded_at'
        ]
        read_only_fields = ['verification_id', 'status', 'uploaded_at']
        
class ProviderProfileListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for list views - only essential fields
    Avoids N+1 by using select_related and prefetch_related in viewset
    """
    # Nested user data without additional query (select_related in view)
    #user_name = serializers.CharField(source='user.username', read_only=True)
    user_name = serializers.CharField(source='user.name', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_image = UserImageField(source="user.image", read_only=True)

    # Nested category data without additional query (select_related in view)
    category_name = serializers.CharField(source='service_category.category_name', read_only=True)
    category_image = serializers.SerializerMethodField()
    user_id = serializers.CharField(source='user.id', read_only=True)
    # Count of work images (annotated in view to avoid N+1)
    work_images_count = serializers.IntegerField(read_only=True)
    conversation_status = serializers.SerializerMethodField()
    
    class Meta:
        model = ProviderProfile
        fields = [
            'id','user_id','user_name', 'user_email','user_image', 'category_name', 
            'category_image', 'service_title', 'provider_description',
            'provider_experience', 'provider_done_work', 'provider_rating',
            'provider_service_charge', 'provider_country', 'provider_city','provider_profile_setup_done','provider_stripe_account_id','stripe_connected',
            'provider_is_verified', 'work_images_count', 'conversation_status', 'created_at'
        ]

    def get_category_image(self, obj):
        request = self.context.get('request')
        return _absolute_media_url(request, obj.service_category.category_image)

    def get_conversation_status(self, obj):
        status_map = self.context.get('conversation_status_map', {})
        return status_map.get(str(obj.user_id)) or status_map.get(str(obj.id))

class ProviderProfileDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for single provider view with all related data
    Uses prefetch_related to avoid N+1 queries
    """
    # Full nested user object
    user = UserSerializer(read_only=True)
    
    # Full nested category object
    service_category = ServiceCategorySerializer(read_only=True)
    
    # Related keywords (prefetched in view)
    keywords = ProviderKeywordSerializer(many=True, source='providerkeyword_set', read_only=True)
    
    # Related work images (prefetched in view)
    work_images = ProviderWorkImageSerializer(many=True, read_only=True)
    
    # Related documents (prefetched in view)
    documents = ProviderDocumentSerializer(many=True, source='providerdocument_set', read_only=True)
    conversation_status = serializers.SerializerMethodField()

    class Meta:
        model = ProviderProfile
        fields = [
            'id','user', 'service_category', 'service_title',
            'provider_description', 'provider_experience', 'provider_done_work',
            'provider_rating', 'provider_service_charge', 'provider_language',
            'provider_licence_number', 'provider_country',
            'provider_city', 'provider_service_area', 'provider_total_hired','provider_profile_setup_done',
            'provider_total_earnings', 'provider_available_balance',
            'provider_is_verified', 'keywords', 'work_images', 'documents',
            'provider_stripe_account_id','stripe_connected', 'conversation_status',
            'created_at', 'updated_at'
        ]

    def get_conversation_status(self, obj):
        status_map = self.context.get('conversation_status_map', {})
        return status_map.get(str(obj.user_id)) or status_map.get(str(obj.id))

class ProviderProfileCreateUpdateSerializer(serializers.ModelSerializer):

    keywords = serializers.ListField(
        child=serializers.CharField(max_length=100),
        write_only=True,
        required=False
    )

    # ✅ for OUTPUT
    keywords_display = serializers.SerializerMethodField(read_only=True)
    
    # Country validation
    provider_country = serializers.CharField(max_length=100)

    #===========\
    provider_state = serializers.CharField(max_length=100, required=False, allow_blank=True)
    provider_zip_code = serializers.CharField(max_length=20, required=False, allow_blank=True)
    #=============/

    user_image = UserImageField(source="user.image", read_only=True)

    class Meta:
        model = ProviderProfile
        fields = [
            'id','user','user_image', 'service_category', 'service_title',
            'provider_description', 'provider_experience', 'provider_service_charge',
            'provider_language', 'provider_licence_number',
            'provider_country', 'provider_city', 'provider_state', 'provider_zip_code','provider_service_area','provider_profile_setup_done','provider_stripe_account_id','stripe_connected',
            'keywords',          # input
            'keywords_display'   # output
        ]
        read_only_fields = [
            'provider_done_work', 'provider_rating',
            'provider_total_hired', 'provider_total_earnings',
            'provider_available_balance', 'provider_is_verified'
        ]
    

    def get_keywords_display(self, obj):
        return list(
            obj.providerkeyword_set.values_list('keyword', flat=True)
        )

    def validate_provider_country(self, value):
        """Validate country name against predefined list"""
        if value and value not in ALLOWED_COUNTRIES:
            raise serializers.ValidationError(
                f"Invalid country. Must be one of: {', '.join(ALLOWED_COUNTRIES)}"
            )
        return value
    
    def validate_provider_experience(self, value):
        """Validate experience is positive number"""
        if value is not None and value < 0:
            raise serializers.ValidationError("Experience cannot be negative")
        return value
    
    def create(self, validated_data):
        """
        Create provider profile with keywords in a single transaction
        Efficient bulk creation of keywords
        """
        # Extract keywords from validated data
        keywords_data = validated_data.pop('keywords', [])
        
        # Create provider profile
        provider = ProviderProfile.objects.create(**validated_data)
        
        # Bulk create keywords if provided (efficient for multiple inserts)
        if keywords_data:
            keyword_objects = [
                ProviderKeyword(provider=provider, keyword=kw)
                for kw in keywords_data
            ]
            ProviderKeyword.objects.bulk_create(keyword_objects)
        
        return provider
    
    def update(self, instance, validated_data):
        """
        Update provider profile and keywords efficiently
        """
        # Extract keywords from validated data
        keywords_data = validated_data.pop('keywords', None)
        
        # Update provider profile fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update keywords if provided (delete old, create new)
        if keywords_data is not None:
            # Delete existing keywords in one query
            instance.providerkeyword_set.all().delete()
            
            # Bulk create new keywords
            keyword_objects = [
                ProviderKeyword(provider=instance, keyword=kw)
                for kw in keywords_data
            ]
            ProviderKeyword.objects.bulk_create(keyword_objects)
        
        return instance

class ProviderWorkImageUploadSerializer(serializers.ModelSerializer):
    """Serializer for uploading work images"""
    image = serializers.SerializerMethodField()

    class Meta:
        model = ProviderWorkImage
        fields = ['id','provider_id', 'image', 'created_at']#'provider', 
        read_only_fields = ['id', 'created_at']

    def get_image(self, obj):
        request = self.context.get('request')
        return _absolute_media_url(request, obj.image)


class TopRatedProviderSerializer(serializers.ModelSerializer):

    user_name = serializers.CharField(source='user.name', read_only=True)
    user_image = UserImageField(source="user.image", read_only=True)
    category_name = serializers.CharField(source='service_category.category_name', read_only=True)
    
    # These will be annotated in the view
    average_rating = serializers.DecimalField(max_digits=3, decimal_places=2, read_only=True)
    total_work = serializers.IntegerField(read_only=True)
    conversation_status = serializers.SerializerMethodField()
    
    class Meta:
        model = ProviderProfile
        fields = [
            'id','user_name','user_image', 'category_name', 'service_title',
            'provider_country', 'provider_city', 'average_rating','provider_stripe_account_id','stripe_connected',
            'total_work', 'provider_is_verified', 'conversation_status'
        ]    

    def get_conversation_status(self, obj):
        status_map = self.context.get('conversation_status_map', {})
        return status_map.get(str(obj.user_id)) or status_map.get(str(obj.id))



    #Newly added for stripe connect-24th Dec-----------------------------------------------\
class ProviderStripeStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProviderProfile
        fields = ['provider_stripe_account_id', 'stripe_connected', 'stripe_connection_date', 'stripe_details_submitted']
        read_only_fields = fields

    #--------------------------------------------------------------------------------------/

from rest_framework import serializers
from .models import BankDetails

class BankDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankDetails
        fields = [
            'id', 'bank_account_name', 'bank_account_number',
            'bank_name', 'routing_number', 'bank_details',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at']


