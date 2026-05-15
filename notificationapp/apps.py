from django.apps import AppConfig


class NotificationappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notificationapp'

    def ready(self):
        from . import signals  # noqa: F401
