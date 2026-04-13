from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ReceiverProfileViewSet

# Create router for automatic URL routing
router = DefaultRouter()

# Register viewsets with router
# This automatically creates: list, create, retrieve, update, partial_update, destroy routes
router.register(r'profiles', ReceiverProfileViewSet, basename='receiver-profile')

# URL patterns
urlpatterns = [
    # Include all router-generated URLs
    path('', include(router.urls)),
    
    # Additional custom URLs if needed can be added here
    # Example: path('custom-endpoint/', CustomView.as_view(), name='custom'),
]

# Generated URLs:
# GET    /api/receiver/profiles/            - List all receiver profiles
# POST   /api/receiver/profiles/            - Create receiver profile
# GET    /api/receiver/profiles/{id}/       - Get single receiver profile
# PUT    /api/receiver/profiles/{id}/       - Update receiver profile
# PATCH  /api/receiver/profiles/{id}/       - Partial update receiver profile
# DELETE /api/receiver/profiles/{id}/       - Delete receiver profile




















