# urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    QuotationViewSet, OrderViewSet, ReviewViewSet, 
    ProviderDashboardViewSet, payment_status
)

# Create router for automatic URL routing
router = DefaultRouter()

# Register viewsets
router.register(r'quotations', QuotationViewSet, basename='quotation')
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'reviews', ReviewViewSet, basename='review')
router.register(r'provider-dashboard', ProviderDashboardViewSet, basename='provider-dashboard')


urlpatterns = [
    path('', include(router.urls)),
    path('payment/status/', payment_status, name='payment-status'),
]

# Generated URLs:
# 
# Quotations:
# GET    /api/quotations/                           - List quotations
# POST   /api/quotations/                           - Create quotation (Provider)
# GET    /api/quotations/{id}/                      - Get quotation detail
# PATCH  /api/quotations/{id}/update-status/        - Accept/Decline (Receiver)
# 
# Orders:
# GET    /api/orders/                               - List orders
# POST   /api/orders/                               - Create order (Receiver)
# GET    /api/orders/{id}/                          - Get order detail
# PATCH  /api/orders/{id}/update-status/            - Update order status
# POST   /api/orders/create-payment-intent/         - Create Stripe payment
# POST   /api/orders/stripe-webhook/                - Stripe webhook
# POST   /api/orders/{id}/release-payment/          - Release payment (Admin)
# 
# Reviews:
# GET    /api/reviews/                              - List reviews
# POST   /api/reviews/                              - Create review (Receiver)
# GET    /api/reviews/{id}/                         - Get review detail
# GET    /api/reviews/provider/{provider_id}/       - Get reviews for provider
# 
# Provider Dashboard:
# GET    /api/provider-dashboard/earnings/          - Get earnings dashboard
# GET    /api/provider-dashboard/hiring-list/       - Get hiring list