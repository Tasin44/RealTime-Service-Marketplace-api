
from django.apps import AppConfig

class AuthappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'authapp'
    verbose_name = 'User Authentication'
    
    def ready(self):
        import authapp.signals  # Import signals