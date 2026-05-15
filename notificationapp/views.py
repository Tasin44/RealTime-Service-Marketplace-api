import logging
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import DeviceToken, Notification
from .serializers import DeviceTokenSerializer, NotificationSerializer

logger = logging.getLogger(__name__)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def register_device_token(request):
	serializer = DeviceTokenSerializer(data=request.data)
	if serializer.is_valid():
		DeviceToken.objects.update_or_create(
			user=request.user,
			token=serializer.validated_data["token"],
			defaults={
				"device_type": serializer.validated_data.get("device_type", ""),
				"is_active": True,
			},
		)
		return Response({"success": True, "message": "Token registered"}, status=201)
	logger.warning("Device token register failed: %s", serializer.errors)
	return Response(serializer.errors, status=400)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_device_token(request):
	token = request.data.get("token")
	if not token:
		logger.warning("Device token delete failed: missing token")
		return Response({"error": "token is required"}, status=400)
	DeviceToken.objects.filter(user=request.user, token=token).delete()
	return Response({"success": True, "message": "Token deleted"}, status=200)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_notifications(request):
	notifications = Notification.objects.filter(user=request.user)[:50]
	serializer = NotificationSerializer(notifications, many=True)
	return Response({"success": True, "data": serializer.data}, status=200)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def mark_notification_read(request, notification_id):
	try:
		notification = Notification.objects.get(id=notification_id, user=request.user)
	except Notification.DoesNotExist:
		return Response({"error": "Notification not found"}, status=404)

	notification.is_read = True
	notification.save(update_fields=["is_read"])
	return Response({"success": True, "message": "Marked as read"}, status=200)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def test_push_notification(request):
	from notificationapp.onesignal_service import send_onesignal_notification

	title = request.data.get("title", "Test Notification")
	body = request.data.get("body", "This is a test push notification")
	result = send_onesignal_notification(
		user=request.user,
		title=title,
		body=body,
		data={"type": "test"},
	)
	return Response({"success": True, "onesignal_response": result}, status=200)
