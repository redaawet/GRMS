"""Fallback-friendly GIS field definitions."""

from __future__ import annotations

from django.core.exceptions import ImproperlyConfigured
from django.db import models

try:  # pragma: no cover - exercised when GDAL is available
    from django.contrib.gis.db.models import LineStringField as DjangoLineStringField
    from django.contrib.gis.db.models import PointField as DjangoPointField
except (ImproperlyConfigured, ImportError, OSError):  # pragma: no cover - runtime fallback
    class _GeometryJSONField(models.JSONField):
        description = "Geometry stored as GeoJSON when spatial libraries are unavailable"

        def __init__(self, *args, **kwargs):
            kwargs.pop("srid", None)
            kwargs.pop("dim", None)
            kwargs.pop("geography", None)
            super().__init__(*args, **kwargs)

    class DjangoPointField(_GeometryJSONField):
        pass

    class DjangoLineStringField(_GeometryJSONField):
        pass

PointField = DjangoPointField
LineStringField = DjangoLineStringField
