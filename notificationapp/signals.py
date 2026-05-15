from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from messageapp.models import Conversation
from quoteapp.models import Quotation, Order
from .notification_helpers import (
    notify_conversation_status,
    notify_quotation_status,
    notify_order_paid,
)


def _stash_previous_value(instance, model_cls, field_name, attr_name):
    if not instance.pk:
        setattr(instance, attr_name, None)
        return
    try:
        previous_value = model_cls.objects.only(field_name).get(pk=instance.pk).__dict__.get(field_name)
    except model_cls.DoesNotExist:
        previous_value = None
    setattr(instance, attr_name, previous_value)


@receiver(pre_save, sender=Conversation)
def conversation_status_before_save(sender, instance, **kwargs):
    _stash_previous_value(instance, Conversation, "conversation_status", "_previous_conversation_status")


@receiver(post_save, sender=Conversation)
def conversation_status_notification(sender, instance, created, **kwargs):
    if created:
        return

    previous_status = getattr(instance, "_previous_conversation_status", None)
    current_status = instance.conversation_status

    if previous_status == current_status:
        return

    if previous_status == "pending" and current_status in ["active", "expired"]:
        notify_conversation_status(instance, current_status)


@receiver(pre_save, sender=Quotation)
def quotation_status_before_save(sender, instance, **kwargs):
    _stash_previous_value(instance, Quotation, "quotation_status", "_previous_quotation_status")


@receiver(post_save, sender=Quotation)
def quotation_status_notification(sender, instance, created, **kwargs):
    if created:
        return

    previous_status = getattr(instance, "_previous_quotation_status", None)
    current_status = instance.quotation_status

    if previous_status == current_status:
        return

    if current_status in ["accepted", "declined"]:
        notify_quotation_status(instance, current_status)


@receiver(pre_save, sender=Order)
def order_payment_before_save(sender, instance, **kwargs):
    _stash_previous_value(instance, Order, "payment_status", "_previous_payment_status")


@receiver(post_save, sender=Order)
def order_payment_notification(sender, instance, created, **kwargs):
    if created:
        return

    previous_status = getattr(instance, "_previous_payment_status", None)
    current_status = instance.payment_status

    if previous_status == current_status:
        return

    if current_status == "paid":
        notify_order_paid(instance)
