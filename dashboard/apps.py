from django.apps import AppConfig
from django.conf import settings
from django.db.models.signals import post_migrate


def _ensure_default_superuser(sender, **kwargs) -> None:
    """Create a superuser using configured environment credentials if needed."""
    username = getattr(settings, "DJANGO_ADMIN_USERNAME", None)
    password = getattr(settings, "DJANGO_ADMIN_PASSWORD", None)

    if not username or not password:
        return

    email = getattr(settings, "DJANGO_ADMIN_EMAIL", "") or ""

    from django.contrib.auth import get_user_model

    User = get_user_model()

    if User.objects.filter(username=username).exists():
        return

    User.objects.create_superuser(username=username, email=email, password=password)


class DashboardConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dashboard'
    verbose_name = 'Panel de control'

    def ready(self):
        post_migrate.connect(_ensure_default_superuser, sender=self)
