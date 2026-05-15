import logging
from .models import Notification
from .onesignal_service import send_onesignal_notification

logger = logging.getLogger(__name__)


def _send_and_store(user, notification_type, title, body, data):
    Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        body=body,
        data=data or {},
    )
    send_onesignal_notification(user, title, body, data)


def notify_conversation_status(conversation, status_value):
    receiver_user = conversation.receiver.user
    provider_user = conversation.provider.user

    if status_value == "active":
        title = "Request accepted"
        body = f"{provider_user.name or provider_user.email} accepted your message request."
        data = {
            "type": "conversation_accepted",
            "conversation_id": conversation.conversation_id,
            "provider_user_id": str(provider_user.id),
        }
        _send_and_store(receiver_user, "conversation_accepted", title, body, data)
        logger.info("Conversation accepted notification sent. conversation_id=%s", conversation.conversation_id)
        return

    if status_value == "expired":
        title = "Request declined"
        body = f"{provider_user.name or provider_user.email} declined your message request."
        data = {
            "type": "conversation_declined",
            "conversation_id": conversation.conversation_id,
            "provider_user_id": str(provider_user.id),
        }
        _send_and_store(receiver_user, "conversation_declined", title, body, data)
        logger.info("Conversation declined notification sent. conversation_id=%s", conversation.conversation_id)


def notify_quotation_status(quotation, status_value):
    provider_user = quotation.provider.user
    receiver_user = quotation.receiver.user

    if status_value == "accepted":
        title = "Quotation accepted"
        body = f"{receiver_user.name or receiver_user.email} accepted your quotation."
        data = {
            "type": "quotation_accepted",
            "quotation_id": quotation.id,
            "receiver_user_id": str(receiver_user.id),
        }
        _send_and_store(provider_user, "quotation_accepted", title, body, data)
        logger.info("Quotation accepted notification sent. quotation_id=%s", quotation.id)
        return

    if status_value == "declined":
        title = "Quotation declined"
        body = f"{receiver_user.name or receiver_user.email} declined your quotation."
        data = {
            "type": "quotation_declined",
            "quotation_id": quotation.id,
            "receiver_user_id": str(receiver_user.id),
        }
        _send_and_store(provider_user, "quotation_declined", title, body, data)
        logger.info("Quotation declined notification sent. quotation_id=%s", quotation.id)


def notify_order_paid(order):
    provider_user = order.provider.user
    receiver_user = order.receiver.user

    title = "Order paid"
    body = f"{receiver_user.name or receiver_user.email} completed payment for order #{order.order_id}."
    data = {
        "type": "order_paid",
        "order_id": order.order_id,
        "receiver_user_id": str(receiver_user.id),
    }
    _send_and_store(provider_user, "order_paid", title, body, data)
    logger.info("Order paid notification sent. order_id=%s", order.order_id)
