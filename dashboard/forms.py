from __future__ import annotations

from typing import Any

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

try:
    from PIL import Image, UnidentifiedImageError  # type: ignore
except ImportError:  # pragma: no cover - Pillow should exist, but guard just in case
    Image = None  # type: ignore
    UnidentifiedImageError = Exception  # type: ignore

from .models import SiteConfiguration

MAX_LOGO_SIZE_BYTES = 2 * 1024 * 1024  # 2 MB
ALLOWED_CONTENT_TYPES = {
    "image/png",
    "image/jpeg",
    "image/svg+xml",
    "image/webp",
    "image/gif",
}


def _is_raster_image(content_type: str) -> bool:
    return content_type in {"image/png", "image/jpeg", "image/webp", "image/gif"}


class SiteConfigurationLogoForm(forms.ModelForm):
    remove_logo = forms.BooleanField(
        required=False,
        label=_("Eliminar logo actual"),
    )

    class Meta:
        model = SiteConfiguration
        fields = ["logo"]
        widgets = {
            "logo": forms.ClearableFileInput(
                attrs={
                    "accept": "image/*",
                    "data-site-logo-input": "true",
                }
            )
        }
        labels = {
            "logo": _("Seleccionar nuevo logo"),
        }

    def clean_logo(self) -> Any:
        logo = self.cleaned_data.get("logo")
        remove_logo = self.cleaned_data.get("remove_logo")

        if not logo:
            if remove_logo:
                return None
            if self.instance and getattr(self.instance, "logo", None):
                return self.instance.logo
            return None

        if logo.size and logo.size > MAX_LOGO_SIZE_BYTES:
            raise ValidationError(
                _(f"El archivo excede el tamaño máximo de {MAX_LOGO_SIZE_BYTES // (1024 * 1024)} MB."),
                code="file_too_large",
            )

        content_type = getattr(logo, "content_type", "") or ""
        if content_type and content_type not in ALLOWED_CONTENT_TYPES:
            raise ValidationError(
                _("Tipo de archivo no soportado. Usa PNG, JPG, SVG, WEBP o GIF."),
                code="invalid_type",
            )

        if _is_raster_image(content_type) and Image:
            try:
                image = Image.open(logo)
                image.verify()
            except (UnidentifiedImageError, OSError) as exc:  # pragma: no cover - Pillow errors
                raise ValidationError(
                    _("El archivo seleccionado no es una imagen válida."),
                    code="invalid_image",
                ) from exc
            finally:
                logo.seek(0)

        return logo

    def save(self, commit: bool = True) -> SiteConfiguration:
        instance = super().save(commit=False)
        remove_logo = self.cleaned_data.get("remove_logo")

        if remove_logo and instance.logo:
            instance.logo.delete(save=False)
            instance.logo = None

        if commit:
            instance.save()
        return instance
