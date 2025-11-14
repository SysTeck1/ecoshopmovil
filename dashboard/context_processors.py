from __future__ import annotations

from django.templatetags.static import static

from .models import SiteConfiguration


def dashboard_branding(request):
    """Expose global branding configuration to all templates."""
    site_config = SiteConfiguration.get_solo()
    logo_url = site_config.logo.url if site_config.logo else static("img/logo/placeholder.svg")
    return {
        "dashboard_logo_url": logo_url,
    }
