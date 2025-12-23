from __future__ import annotations

import json

from django.http import JsonResponse

from . import models
from .utils import slice_linestring_by_chainage


def _serialize_geometry(geom):
    if not geom:
        return None
    if hasattr(geom, "geojson"):
        try:
            return json.loads(geom.geojson)
        except Exception:
            return None
    if isinstance(geom, (dict, list)):
        return geom
    if isinstance(geom, str):
        try:
            return json.loads(geom)
        except Exception:
            return None
    return None


def _feature(geometry, properties=None):
    return {"type": "Feature", "geometry": geometry, "properties": properties or {}}


def _feature_collection(features):
    return {"type": "FeatureCollection", "features": features}


def _section_geometry(section: models.RoadSection):
    if section.geometry:
        return _serialize_geometry(section.geometry)
    road_geom = getattr(section.road, "geometry", None)
    if road_geom:
        sliced = slice_linestring_by_chainage(
            road_geom,
            float(section.start_chainage_km),
            float(section.end_chainage_km),
        )
        return _serialize_geometry(sliced.get("geometry") if sliced else None)
    return None


def _segment_geometry(segment: models.RoadSegment):
    road_geom = getattr(segment.section.road, "geometry", None)
    if road_geom:
        sliced = slice_linestring_by_chainage(
            road_geom,
            float(segment.station_from_km),
            float(segment.station_to_km),
        )
        return _serialize_geometry(sliced.get("geometry") if sliced else None)
    return None


def road_geojson_view(request):
    road_id = request.GET.get("road_id")
    if not road_id or not road_id.isdigit():
        return JsonResponse({"error": "road_id is required."}, status=400)
    road = models.Road.objects.filter(pk=int(road_id)).first()
    if not road:
        return JsonResponse({"error": "Road not found."}, status=404)
    geometry = _serialize_geometry(getattr(road, "geometry", None))
    feature = _feature(geometry, {"id": road.id, "label": str(road)})
    return JsonResponse(_feature_collection([feature]))


def sections_geojson_view(request):
    road_id = request.GET.get("road_id")
    if not road_id or not road_id.isdigit():
        return JsonResponse({"error": "road_id is required."}, status=400)
    road_id_int = int(road_id)
    current_id = request.GET.get("current_id")
    current_id = int(current_id) if current_id and current_id.isdigit() else None
    sections = models.RoadSection.objects.filter(road_id=road_id_int)
    features = []
    for section in sections:
        geometry = _section_geometry(section)
        if not geometry:
            continue
        features.append(
            _feature(
                geometry,
                {
                    "id": section.id,
                    "label": str(section),
                    "is_current": section.id == current_id,
                },
            )
        )
    return JsonResponse(_feature_collection(features))


def segments_geojson_view(request):
    road_id = request.GET.get("road_id")
    if not road_id or not road_id.isdigit():
        return JsonResponse({"error": "road_id is required."}, status=400)
    road_id_int = int(road_id)
    section_id = request.GET.get("section_id")
    current_id = request.GET.get("current_id")
    current_id = int(current_id) if current_id and current_id.isdigit() else None

    sections = models.RoadSection.objects.filter(road_id=road_id_int)
    if section_id and section_id.isdigit():
        sections = sections.filter(pk=int(section_id))
    segments = models.RoadSegment.objects.filter(section__in=sections).select_related("section")

    features = []
    for segment in segments:
        geometry = _segment_geometry(segment)
        if not geometry:
            continue
        features.append(
            _feature(
                geometry,
                {
                    "id": segment.id,
                    "label": str(segment),
                    "is_current": segment.id == current_id,
                },
            )
        )
    return JsonResponse(_feature_collection(features))


def structures_geojson_view(request):
    road_id = request.GET.get("road_id")
    if not road_id or not road_id.isdigit():
        return JsonResponse({"error": "road_id is required."}, status=400)
    road_id_int = int(road_id)
    section_id = request.GET.get("section_id")
    current_id = request.GET.get("current_id")
    current_id = int(current_id) if current_id and current_id.isdigit() else None

    structures = models.StructureInventory.objects.filter(road_id=road_id_int)
    if section_id and section_id.isdigit():
        structures = structures.filter(section_id=int(section_id))

    features = []
    for structure in structures:
        geometry = _serialize_geometry(structure.location_point)
        if not geometry:
            continue
        features.append(
            _feature(
                geometry,
                {
                    "id": structure.id,
                    "label": str(structure),
                    "is_current": structure.id == current_id,
                    "category": structure.structure_category,
                },
            )
        )
    return JsonResponse(_feature_collection(features))
