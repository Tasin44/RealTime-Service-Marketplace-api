from django.urls import path
from . import views

urlpatterns = [
    path("device-token/register/", views.register_device_token),
    path("device-token/delete/", views.delete_device_token),
    path("list/", views.list_notifications),
    path("<int:notification_id>/read/", views.mark_notification_read),
    path("test-push/", views.test_push_notification),
]
