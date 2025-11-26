"""Fallback-friendly GIS field definitions."""

from __future__ import annotations

from django.core.exceptions import ImproperlyConfigured
from django.db import models


def _fallback_field_base():
    class _GeometryJSONField(models.JSONField):  # type: ignore[override]
        description = "Geometry stored as GeoJSON when spatial libraries are unavailable"

        def __init__(self, *args, **kwargs):
            kwargs.pop("srid", None)
            kwargs.pop("dim", None)
            kwargs.pop("geography", None)
            super().__init__(*args, **kwargs)

    return _GeometryJSONField


def _load_spatial_fields():
    try:  # pragma: no cover - exercised when GDAL is available
        from django.contrib.gis.db.models import LineStringField as DjangoLineStringField
        from django.contrib.gis.db.models import PointField as DjangoPointField

        return DjangoPointField, DjangoLineStringField
    except Exception:  # pragma: no cover - runtime fallback when GIS libs are missing
        GeometryBase = _fallback_field_base()

        class DjangoPointField(GeometryBase):
            pass

        class DjangoLineStringField(GeometryBase):
            pass

        return DjangoPointField, DjangoLineStringField


DjangoPointField, DjangoLineStringField = _load_spatial_fields()

PointField = DjangoPointField
LineStringField = DjangoLineStringField
