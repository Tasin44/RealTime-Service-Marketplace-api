from django.db.models.signals import post_save
from django.dispatch import receiver

from authapp.models import User
from servicereceiverapp.models import ReceiverProfile


@receiver(post_save, sender=User)
def ensure_receiver_profile(sender, instance, created, **kwargs):
	if instance.role != "receiver":
		return
	ReceiverProfile.objects.get_or_create(user=instance)
