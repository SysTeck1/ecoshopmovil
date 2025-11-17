from __future__ import annotations

from pathlib import Path

from django.conf import settings
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

    static_logo_url = _find_static_asset("img/logo/logo.png")
    if static_logo_url:
        return static_logo_url

    # Si hay un logo configurado y parece estar disponible, úsalo
    logo_field = site_config.logo
    if logo_field and logo_field.name:
        try:
            if logo_field.storage.exists(logo_field.name):
                return logo_field.url
        except Exception:
            # Si no podemos verificar la existencia, seguimos con el fallback estático
            pass

    placeholder_url = _find_static_asset("img/logo/placeholder.svg")
    if placeholder_url:
        return placeholder_url

    # Último recurso: URL relativa generada con templatetag static
    return static("img/logo/placeholder.svg")


def _find_static_asset(*relative_paths: str) -> str:
    """Devuelve la URL estática para el primer asset disponible."""

    static_root = Path(settings.BASE_DIR) / "static"

    for relative in relative_paths:
        file_path = static_root / Path(relative)
        if file_path.exists():
            return static(relative)

        try:
            if staticfiles_storage.exists(relative):
                return staticfiles_storage.url(relative)
        except Exception:
            return static(relative)

    return ""
