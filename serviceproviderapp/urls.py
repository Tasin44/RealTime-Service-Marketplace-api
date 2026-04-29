


from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ServiceCategoryViewSet, ProviderProfileViewSet, stripe_connect_onboard, stripe_connection_status, stripe_onboard_complete, add_bank_details, get_bank_details

# Create router for automatic URL routing
router = DefaultRouter()

# Register viewsets with router
# This automatically creates: list, create, retrieve, update, partial_update, destroy routes
router.register(r'categories', ServiceCategoryViewSet, basename='category')
router.register(r'providers', ProviderProfileViewSet, basename='provider')

# URL patterns
urlpatterns = [
    # Include all router-generated URLs
    path('', include(router.urls)),
    path('stripe/onboard/', stripe_connect_onboard),
    path('stripe/status/', stripe_connection_status),
    path('stripe/onboard-complete/', stripe_onboard_complete),
    path('bank-details/', add_bank_details, name='add_bank_details'),
    path('bank-details/get/', get_bank_details, name='get_bank_details'),
    # Additional custom URLs if needed can be added here
    # Example: path('custom-endpoint/', CustomView.as_view(), name='custom'),
]

# Generated URLs:
# GET    /api/categories/                    - List all categories
# GET    /api/categories/{id}/               - Get single category
# 
# GET    /api/providers/                     - List providers (with filters)
# POST   /api/providers/                     - Create provider profile
# GET    /api/providers/{id}/                - Get single provider detail
# PUT    /api/providers/{id}/                - Update provider profile
# PATCH  /api/providers/{id}/                - Partial update provider
# DELETE /api/providers/{id}/                - Delete provider profile
# GET    /api/providers/top-rated/           - Get top-rated providers
# POST   /api/providers/{id}/upload-work-image/        - Upload work image
# DELETE /api/providers/{id}/delete-work-image/{image_id}/ - Delete work image
# POST   /api/providers/{id}/submit-document/          - Submit KYC document
# GET    /api/providers/by-country/          - Search by country




















