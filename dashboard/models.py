from __future__ import annotations

import logging
import shutil
from pathlib import Path

from django.conf import settings
from django.core.files.storage import default_storage
from django.db import models


def _delete_file(path: str | None) -> None:
    if path and default_storage.exists(path):
        default_storage.delete(path)


logger = logging.getLogger(__name__)


class SiteConfiguration(models.Model):
    """Configuración general del sitio (logo, temas, etc.)."""

    logo = models.ImageField(upload_to="branding/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuración del sitio"
        verbose_name_plural = "Configuraciones del sitio"

    def __str__(self) -> str:
        return "Configuración del sitio"

    @classmethod
    def get_solo(cls) -> "SiteConfiguration":
        instance = cls.objects.first()
        if instance is None:
            instance = cls.objects.create()
        return instance

    def save(self, *args, **kwargs):
        if self.pk:
            previous = type(self).objects.filter(pk=self.pk).only("logo").first()
        else:
            previous = None
        super().save(*args, **kwargs)
        previous_name = getattr(previous.logo, "name", None) if previous else None
        current_name = getattr(self.logo, "name", None)
        if previous_name and previous_name != current_name:
            _delete_file(previous_name)

        self._export_logo_to_static()

    def delete(self, *args, **kwargs):
        logo_name = getattr(self.logo, "name", None)
        super().delete(*args, **kwargs)
        _delete_file(logo_name)
        self._remove_static_logo_copy()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _export_logo_to_static(self) -> None:
        """Copia el logo cargado al directorio estático para entornos sin media persistente."""

        static_dir = Path(settings.BASE_DIR) / "static" / "img" / "logo"
        static_dir.mkdir(parents=True, exist_ok=True)
        static_logo_path = static_dir / "logo.png"

        logo_field = self.logo
        if logo_field and getattr(logo_field, "name", None):
            try:
                if logo_field.storage.exists(logo_field.name):
                    with logo_field.open("rb") as source, open(static_logo_path, "wb") as target:
                        shutil.copyfileobj(source, target)
                return
            except Exception as exc:  # pragma: no cover - log and continue fallback
                logger.warning("No se pudo exportar el logo a estáticos: %s", exc)

        self._remove_static_logo_copy()

    def _remove_static_logo_copy(self) -> None:
        static_logo_path = Path(settings.BASE_DIR) / "static" / "img" / "logo" / "logo.png"
        try:
            if static_logo_path.exists():
                static_logo_path.unlink()
        except Exception as exc:  # pragma: no cover - log and continue
            logger.warning("No se pudo eliminar la copia estática del logo: %s", exc)
