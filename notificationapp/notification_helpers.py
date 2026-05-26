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


def notify_quotation_paid(quotation):
    """Notify provider when receiver completes payment on a quotation (via payment link)."""
    provider_user = quotation.provider.user
    receiver_user = quotation.receiver.user

    title = "Payment received"
    body = f"{receiver_user.name or receiver_user.email} completed payment for your quotation."
    data = {
        "type": "quotation_paid",
        "quotation_id": quotation.id,
        "receiver_user_id": str(receiver_user.id),
    }
    _send_and_store(provider_user, "quotation_paid", title, body, data)
    logger.info("Quotation paid notification sent. quotation_id=%s", quotation.id)


def notify_order_paid(order):
    """Notify provider when receiver completes payment on an order."""
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


def notify_order_completed(order):
    """Notify receiver when an order is marked as completed."""
    provider_user = order.provider.user
    receiver_user = order.receiver.user

    title = "Order completed"
    body = f"Your order #{order.order_id} with {provider_user.name or provider_user.email} has been completed."
    data = {
        "type": "order_completed",
        "order_id": order.order_id,
        "provider_user_id": str(provider_user.id),
    }
    # Notify the receiver that the order is complete
    _send_and_store(receiver_user, "order_completed", title, body, data)
    logger.info("Order completed notification sent to receiver. order_id=%s", order.order_id)

    # Also notify the provider for confirmation
    provider_title = "Order completed"
    provider_body = f"Order #{order.order_id} with {receiver_user.name or receiver_user.email} has been marked as completed."
    provider_data = {
        "type": "order_completed",
        "order_id": order.order_id,
        "receiver_user_id": str(receiver_user.id),
    }
    _send_and_store(provider_user, "order_completed", provider_title, provider_body, provider_data)
    logger.info("Order completed notification sent to provider. order_id=%s", order.order_id)


def notify_order_cancelled(order):
    """Notify both parties when an order is cancelled."""
    provider_user = order.provider.user
    receiver_user = order.receiver.user
    cancelled_by = order.cancellation_requested_by or "system"

    if cancelled_by == "provider":
        # Provider cancelled → notify receiver
        title = "Order cancelled"
        body = f"{provider_user.name or provider_user.email} cancelled order #{order.order_id}."
        data = {
            "type": "order_cancelled",
            "order_id": order.order_id,
            "cancelled_by": "provider",
            "provider_user_id": str(provider_user.id),
        }
        _send_and_store(receiver_user, "order_cancelled", title, body, data)
        logger.info("Order cancelled notification sent to receiver. order_id=%s", order.order_id)
    elif cancelled_by == "receiver":
        # Receiver cancelled → notify provider
        title = "Order cancelled"
        body = f"{receiver_user.name or receiver_user.email} cancelled order #{order.order_id}."
        data = {
            "type": "order_cancelled",
            "order_id": order.order_id,
            "cancelled_by": "receiver",
            "receiver_user_id": str(receiver_user.id),
        }
        _send_and_store(provider_user, "order_cancelled", title, body, data)
        logger.info("Order cancelled notification sent to provider. order_id=%s", order.order_id)
    else:
        # System or unknown → notify both
        title = "Order cancelled"
        body_receiver = f"Order #{order.order_id} has been cancelled."
        body_provider = f"Order #{order.order_id} has been cancelled."
        data_receiver = {
            "type": "order_cancelled",
            "order_id": order.order_id,
            "cancelled_by": "system",
        }
        data_provider = {
            "type": "order_cancelled",
            "order_id": order.order_id,
            "cancelled_by": "system",
        }
        _send_and_store(receiver_user, "order_cancelled", title, body_receiver, data_receiver)
        _send_and_store(provider_user, "order_cancelled", title, body_provider, data_provider)
        logger.info("Order cancelled notification sent to both parties. order_id=%s", order.order_id)
