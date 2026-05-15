import logging
import requests
from django.conf import settings
from .models import DeviceToken

logger = logging.getLogger(__name__)


def send_onesignal_notification(user, title, body, data=None):
    try:
        device_tokens = list(
            DeviceToken.objects.filter(user=user, is_active=True).values_list("token", flat=True)
        )

        if not device_tokens:
            logger.warning("No device tokens found for user %s", user.id)
            return {"error": "No device tokens found"}

        headers = {
            "Authorization": f"Basic {settings.ONESIGNAL_REST_API_KEY}",
            "Content-Type": "application/json",
        }

        payload = {
            "app_id": settings.ONESIGNAL_APP_ID,
            "include_subscription_ids": device_tokens,
            "target_channel": "push",
            "headings": {"en": title},
            "contents": {"en": body},
            "data": data or {},
        }

        response = requests.post(
            "https://onesignal.com/api/v1/notifications",
            headers=headers,
            json=payload,
            timeout=10,
        )

        result = response.json()
        if response.status_code == 200 and result.get("recipients", 0) > 0:
            logger.info("OneSignal notification sent to user %s: %s", user.id, title)
        else:
            logger.warning("OneSignal response for user %s: %s", user.id, result)

        return result

    except Exception as exc:
        logger.error("OneSignal notification failed for user %s: %s", user.id, exc)
        return None
