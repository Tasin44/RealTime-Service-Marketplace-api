from django.shortcuts import render
from django.conf import settings
from django.utils import timezone
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Prefetch, Count, Avg, Q, F
from django.core.cache import cache
from rest_framework.pagination import PageNumberPagination
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import requests
import os
from .models import (
    ServiceCategory, ProviderProfile, ProviderKeyword,
    ProviderWorkImage, ProviderDocument
)
from .serializers import (
    ServiceCategorySerializer, ProviderProfileListSerializer,
    ProviderProfileDetailSerializer, ProviderProfileCreateUpdateSerializer,
    ProviderWorkImageUploadSerializer, ProviderDocumentSerializer,
    TopRatedProviderSerializer,ProviderStripeStatusSerializer
)
from .utils import verify_document_with_kycaid,COUNTRY_ISO_MAP
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import redirect
from rest_framework.decorators import api_view, permission_classes
import stripe 
stripe.api_key = settings.STRIPE_SECRET_KEY


# Create your views here.
# ---------------------------
# Standard Response Mixin
# ---------------------------
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
    


# Standard pagination class for all list views
class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination: 20 items per page, customizable via query param"""
    page_size = 20  # Default page size
    page_size_query_param = 'page_size'  # Allow client to override page size
    max_page_size = 100  # Maximum allowed page size


class ServiceCategoryViewSet(StandardResponseMixin,viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for ServiceCategory - Read-only for frontend
    Admin creates categories via Django admin panel
    """
    queryset = ServiceCategory.objects.all().order_by('category_name')
    serializer_class = ServiceCategorySerializer
    permission_classes = [AllowAny]  # Public access to view categories
    pagination_class = None  # No pagination for categories (small dataset)
    
    @swagger_auto_schema(
        operation_description="Get all service categories",
        responses={200: ServiceCategorySerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):

        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True , context={'request': request})
        
        # # Cache the result for 1 hour
        # cache.set(cache_key, serializer.data, 3600)
        
        return Response(serializer.data)

class ProviderProfileViewSet(StandardResponseMixin,viewsets.ModelViewSet):

    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    
    # Search across multiple fields
    search_fields = [
        'service_title',
        'user__name',
        'user__email',
        'provider_city',
        'provider_state',
        'provider_zip_code',
        'provider_country',
        'provider_service_area',
        'providerkeyword__keyword',
        'service_category__category_name'
    ]
    
    # Allow ordering by these fields
    ordering_fields = [
        'provider_experience','provider_done_work','provider_rating', 'provider_service_charge',
        'created_at'
    ]
    
    def get_queryset(self):

        #❓❓❓what .select_related,prefetch_related,.annotate doing here? 
        queryset = ProviderProfile.objects.select_related(
            'user',  # Join user table
            'service_category'  # Join category table
        ).prefetch_related(
            # Prefetch related keywords (separate query, but efficient)
            'providerkeyword_set',
            # Prefetch work images
            'work_images',
            # Prefetch documents
            'providerdocument_set'
        ).annotate(
            # Annotate count to avoid separate queries
            work_images_count=Count('work_images')
        )
        
        return queryset
    
    def get_serializer_class(self):
        if self.action in ['retrieve', 'upload_work_image', 'delete_work_image']:
            return ProviderProfileDetailSerializer
        elif self.action == 'list':
            return ProviderProfileListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return ProviderProfileCreateUpdateSerializer

        return ProviderProfileDetailSerializer  # ✅ safe default
    
    @swagger_auto_schema(
        operation_description="Get list of all providers with filtering",
        manual_parameters=[
            openapi.Parameter('country', openapi.IN_QUERY, type=openapi.TYPE_STRING, description="Filter by country"),
            openapi.Parameter('category', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description="Filter by category ID"),
            openapi.Parameter('min_rating', openapi.IN_QUERY, type=openapi.TYPE_NUMBER, description="Minimum rating filter"),
            openapi.Parameter('is_verified', openapi.IN_QUERY, type=openapi.TYPE_BOOLEAN, description="Filter verified providers"),
            openapi.Parameter('search', openapi.IN_QUERY, type=openapi.TYPE_STRING, description="Search in title, description, etc."),
            openapi.Parameter('ordering', openapi.IN_QUERY, type=openapi.TYPE_STRING, description="Order by field (e.g., -provider_rating)"),
        ]
    )
    
    
    def list(self, request, *args, **kwargs):
        """
        List providers with advanced filtering
        Supports: country, category, rating, verification status, search
        """
        queryset = self.get_queryset().filter(user__role='provider')
        '''
        ❌Previous issue: When a user becomes provider, he also see him on the provider list, to get rid of this, I just include user_role='provider'

        Why this fixes your bug:
        When a user was previously verified as provider but later switches role back to receiver, their provider profile record may still exist.
        Before this fix, list queries returned that profile anyway.
        Now, list queries return only profiles where the linked user currently has role = provider, so receiver-mode users will not appear in provider listings.
        
        '''
        name = request.query_params.get('name')
        country = request.query_params.get('country') # Filter by country (case-insensitive exact match)
        state = request.query_params.get('state')
        zip_code = request.query_params.get('zip_code')
        category = request.query_params.get('category')
        category_name = request.query_params.get('category_name')
        min_rating = request.query_params.get('min_rating')# Filter by minimum rating
        is_verified = request.query_params.get('is_verified', None)
        
        # Filter by category ID
        category_id = request.query_params.get('category', None)
       
        if name:
            queryset = queryset.filter(user__name__icontains=name)

        if country:
            queryset = queryset.filter(provider_country__iexact=country)#❓❓❓ what is iexact here

        if state:
            queryset = queryset.filter(provider_state__iexact=state)

        if zip_code:
            queryset = queryset.filter(provider_zip_code__iexact=zip_code)

        if category:
            queryset = queryset.filter(service_category_id=category)

        if category_name:
            queryset = queryset.filter(service_category__category_name__icontains=category_name)


        if category_id:
            queryset = queryset.filter(service_category_id=category_id)
        
        
        if min_rating:
            try:
                queryset = queryset.filter(provider_rating__gte=float(min_rating))
            except ValueError:
                pass
        
        # Filter by verification status

        if is_verified is not None:
            is_verified_bool = is_verified.lower() == 'true'
            queryset = queryset.filter(provider_is_verified=is_verified_bool)
        
        # Apply search filter (handled by filter_backends)
        queryset = self.filter_queryset(queryset)#❓❓❓ what does this line doing
        
        # Paginate and return
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        #serializer = self.get_serializer(queryset, many=True)
        serializer = self.get_serializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_description="Get top-rated providers based on work done and rating",
        manual_parameters=[
            openapi.Parameter('category', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description="Filter by category ID"),
            openapi.Parameter('country', openapi.IN_QUERY, type=openapi.TYPE_STRING, description="Filter by country"),
            openapi.Parameter('limit', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description="Number of results (default: 10)"),
        ],
        responses={200: TopRatedProviderSerializer(many=True)}
    )

    @action(detail=False, methods=['get'], url_path='top-rated')
    def top_rated(self, request):
        category_id = request.query_params.get('category', None)
        country = request.query_params.get('country', None)
        limit = request.query_params.get('limit', 10)
        
        try:
            limit = int(limit)
            if limit > 100:  # Cap at 100 for performance
                limit = 100
        except ValueError:
            limit = 10
        
        # Base queryset with optimized joins
        queryset = ProviderProfile.objects.select_related(
            'user', 'service_category'
        ).filter(
            user__role='provider',
            provider_done_work__gt=0  # Only providers with completed work
        )
        
        # Apply category filter
        if category_id:
            queryset = queryset.filter(service_category_id=category_id)
        
        # Apply country filter
        if country:
            queryset = queryset.filter(provider_country__iexact=country)
        
        # Annotate with aggregated data and order
        # This uses a heap-like structure in DB for efficient top-N selection
        queryset = queryset.annotate(
            total_work=F('provider_done_work'),  # Alias for clarity
            average_rating=F('provider_rating')  # Already stored as average
        ).order_by(
            '-total_work',  # Primary: most work done
            '-average_rating'  # Secondary: highest rating
        )[:limit]  # Limit in DB query (efficient)
        
        # Serialize and return
        serializer = TopRatedProviderSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_description="Upload work images for provider portfolio",
        request_body=ProviderWorkImageUploadSerializer,
        responses={201: ProviderWorkImageUploadSerializer()}
    )

    @action(detail=True, methods=['get'], url_path='work-images')
    def get_work_images(self, request, pk=None):
        provider = self.get_object()
        images = ProviderWorkImage.objects.filter(provider=provider)

        serializer = ProviderWorkImageUploadSerializer(images, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(
        detail=True,
        methods=['post'],
        url_path='upload-work-image',
        parser_classes=[MultiPartParser, FormParser]
    )
    def upload_work_image(self, request, pk=None):
        """
        Upload work image for a specific provider
        Only the provider themselves can upload
        """
        provider = self.get_object()
        
        # Check if the user is the owner of this provider profile
        if provider.user != request.user:
            return Response(
                {"error": "You can only upload images to your own profile"},
                status=status.HTTP_403_FORBIDDEN
            )
        images = request.FILES.getlist('image')

        if not images:
            return Response(
                {"error": "No images provided"},
                status=status.HTTP_400_BAD_REQUEST
            )

        created_images = []
        for img in images:
            created_images.append(
            ProviderWorkImage.objects.create(
                provider=provider,
                image=img
            )
        )

        serializer = ProviderWorkImageUploadSerializer(created_images, many=True)
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @swagger_auto_schema(
        operation_description="Delete a work image",
        responses={204: "Image deleted successfully"}
    )


    @action(detail=True, methods=['delete'], url_path='delete-work-image/(?P<image_id>[^/.]+)')
    def delete_work_image(self, request, pk=None, image_id=None):
        
        provider = self.get_object()
        
        # Check ownership
        if provider.user != request.user:
            return Response(
                {"error": "You can only delete images from your own profile"},
                status=status.HTTP_403_FORBIDDEN
            )

        
        # Get and delete the image
        try:
            work_image = ProviderWorkImage.objects.get(
                id=image_id, 
                provider=provider
            )
            work_image.delete()
            return Response(
                    {"message": "Image deleted successfully"},
                    status=status.HTTP_200_OK
            )


        except ProviderWorkImage.DoesNotExist:
            return Response(
                {"error": "Image not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
    @action(detail=True, methods=['post'], url_path='submit-document',parser_classes=[MultiPartParser, FormParser])
    def submit_document(self, request, pk=None):
        provider = self.get_object()

        if provider.user != request.user:
            return Response({"detail": "Forbidden ! You can only verify your own profile"}, status=403)

        document_type = request.data.get("document_type")
        document_front = request.FILES.get("document_front")

        if not document_type or not document_front:
            return Response(
                {"detail": "document_type and document_front are required"},
                status=400
            )

        doc = ProviderDocument.objects.create(
            provider=provider,
            document_type=document_type,
            document_front=document_front,
            status="pending"
        )
            # if not country_code:
            #     raise ValueError("Invalid or unsupported country for KYC")
        result = verify_document_with_kycaid(
            document_file=document_front,
            document_type=document_type,
            # country_code=provider.provider_country[:2].upper()
            country_code = COUNTRY_ISO_MAP.get(provider.provider_country)

        )

        doc.verification_id = result["verification_id"]
        # doc.status = "verified" if result["verified"] else "failed"
        doc.status = "pending"
        doc.save()


        return Response(
            ProviderDocumentSerializer(doc).data,
            status=status.HTTP_201_CREATED
        )

    # 📌💥🚩🚩🚩the searching not only will happen by country, but also it'll happen by service_are,city, keyword.🚩🚩🚩
    @action(detail=False, methods=['get'], url_path='by-country')
    def by_country(self, request):
        country = request.query_params.get('country', None)
        
        if not country:
            return Response(
                {"error": "country parameter is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Filter queryset by country (case-insensitive)
        queryset = self.get_queryset().filter(
            user__role='provider',
            provider_country__iexact=country
        )
        
        # Paginate results
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)



def is_stripe_supported_country(country_code):
    try:
        stripe.CountrySpec.retrieve(country_code.upper())
        return True
    except stripe.error.InvalidRequestError:
        return False

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def stripe_connect_onboard(request):
    try:
        provider = ProviderProfile.objects.get(user=request.user)
    except ProviderProfile.DoesNotExist:
        return Response({"error": "Provider profile not found"}, status=404)

    if provider.stripe_connected:
        return Response({"message": "Stripe already connected"}, status=200)

    country = request.data.get('country', 'US').upper()  # Default to US or make dynamic

    if not is_stripe_supported_country(country):
        return Response({"error": f"{country} not supported by Stripe"}, status=400)

    # Reuse existing account if any
    if provider.provider_stripe_account_id:
        account_id = provider.provider_stripe_account_id
    else:
        account = stripe.Account.create(
            type='express',
            country=country,
            email=request.user.email,
            capabilities={
                'card_payments': {'requested': True},
                'transfers': {'requested': True},
            },
        )
        provider.provider_stripe_account_id = account.id
        provider.save(update_fields=['provider_stripe_account_id'])
        account_id = account.id

    account_link = stripe.AccountLink.create(
        account=account_id,
        refresh_url=f"{settings.BASE_URL}/provider/stripe/refresh",  # Update with your frontend URL
        return_url=f"{settings.BASE_URL}/provider/stripe/success?account_id={account_id}",
        type='account_onboarding',
    )

    if request.method == "GET":
        return redirect(account_link.url)

    return Response({
        "onboarding_url": account_link.url,
        "account_id": account_id
    })

@api_view(['GET'])
@permission_classes([AllowAny])
def stripe_onboard_complete(request):
    account_id = request.GET.get('account_id')
    if not account_id:
        return redirect(f"{settings.BASE_URL}/provider/dashboard?stripe=error")

    try:
        provider = ProviderProfile.objects.get(provider_stripe_account_id=account_id)
        account = stripe.Account.retrieve(account_id)

        if account.charges_enabled and account.payouts_enabled:
            provider.stripe_connected = True
            provider.stripe_connection_date = timezone.now()
            provider.stripe_details_submitted = account.details_submitted
            provider.save()
            return redirect(f"{settings.BASE_URL}/provider/dashboard?stripe=success")
        else:
            return redirect(f"{settings.BASE_URL}/provider/dashboard?stripe=incomplete")
    except Exception:
        return redirect(f"{settings.BASE_URL}/provider/dashboard?stripe=error")

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def stripe_connection_status(request):
    try:
        provider = ProviderProfile.objects.get(user=request.user)
        serializer = ProviderStripeStatusSerializer(provider)
        return Response({
            "success": True,
            "data": serializer.data
        })
    except ProviderProfile.DoesNotExist:
        return Response({"success": False, "message": "Not a provider"}, status=404)

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import BankDetails, ProviderProfile
from .serializers import BankDetailsSerializer

@api_view(['POST', 'PATCH'])
@permission_classes([IsAuthenticated])
def add_bank_details(request):
    try:
        # Get provider profile
        provider = ProviderProfile.objects.get(user=request.user)
        
        # Check if bank details already exist
        bank_details, created = BankDetails.objects.get_or_create(provider=provider)

        # PATCH should update existing bank details only
        if request.method == 'PATCH' and created:
            return Response(
                {'error': 'No bank details found to update'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Update with new data
        serializer = BankDetailsSerializer(bank_details, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            message = 'Bank details saved successfully' if created else 'Bank details updated successfully'
            return Response({
                'message': message,
                'data': serializer.data
            }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    except ProviderProfile.DoesNotExist:
        return Response({'error': 'Provider profile not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_bank_details(request):
    try:
        provider = ProviderProfile.objects.get(user=request.user)
        bank_details = BankDetails.objects.get(provider=provider)
        
        serializer = BankDetailsSerializer(bank_details)
        return Response({'data': serializer.data}, status=status.HTTP_200_OK)
    
    except ProviderProfile.DoesNotExist:
        return Response({'error': 'Provider profile not found'}, status=status.HTTP_404_NOT_FOUND)
    except BankDetails.DoesNotExist:
        return Response({'message': 'No bank details found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

