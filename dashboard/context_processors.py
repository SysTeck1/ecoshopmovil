from __future__ import annotations

from django.contrib.staticfiles.storage import staticfiles_storage
from django.templatetags.static import static

from .models import SiteConfiguration


def dashboard_branding(request):
    """Expose global branding configuration to all templates."""
    site_config = SiteConfiguration.get_solo()
    logo_url = _resolve_logo_url(site_config)
    return {
        "dashboard_logo_url": logo_url,
    }


def _resolve_logo_url(site_config: SiteConfiguration) -> str:
    """Devuelve la URL del logo configurado o un placeholder estático."""

    # Si hay un logo configurado y parece estar disponible, úsalo
    logo_field = site_config.logo
    if logo_field and logo_field.name:
        try:
            if logo_field.storage.exists(logo_field.name):
                return logo_field.url
        except Exception:
            # Si no podemos verificar la existencia, seguimos con el fallback estático
            pass

    # Fallback a un logo dentro de los archivos estáticos versionados
    if staticfiles_storage.exists("img/logo/placeholder.svg"):
        return staticfiles_storage.url("img/logo/placeholder.svg")

    # Último recurso: URL relativa generada con templatetag static
    return static("img/logo/placeholder.svg")
