# Base models for SistemaPOS project
from django.db import models


class TimeStampedModel(models.Model):
    """Modelo base con marcas de tiempo."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ("-created_at",)
