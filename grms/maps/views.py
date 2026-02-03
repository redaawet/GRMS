from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from grms.models import Road, RoadSection, RoadSegment, StructureInventory
from grms.utils import slice_linestring_by_chainage


def _serialize_geometry(geom) -> Optional[Dict[str, Any]]:
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


def _as_feature(geom, props: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not geom:
        return None
    g = geom
    try:
        if getattr(g, "srid", None) and g.srid != 4326:
            g = g.clone()
            g.transform(4326)
    except Exception:
        # Best-effort transform for Windows/proj issues.
        pass
    geometry = _serialize_geometry(g)
    if not geometry:
        return None
    if isinstance(geometry, dict) and "srid" in geometry:
        geometry = dict(geometry)
        geometry.pop("srid", None)
    return {"type": "Feature", "geometry": geometry, "properties": props}


def _section_geometry(section: RoadSection) -> Optional[Dict[str, Any]]:
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


def _segment_geometry(segment: RoadSegment) -> Optional[Dict[str, Any]]:
    base_geom = getattr(segment.section, "geometry", None) or getattr(segment.section.road, "geometry", None)
    if base_geom:
        sliced = slice_linestring_by_chainage(
            base_geom,
            float(segment.station_from_km),
            float(segment.station_to_km),
        )
        return _serialize_geometry(sliced.get("geometry") if sliced else None)
    return None


@staff_member_required
@require_GET
def map_context(request):
    road_id = request.GET.get("road_id")
    if not road_id:
        return JsonResponse({"error": "road_id is required"}, status=400)

    section_id = request.GET.get("section_id")
    segment_id = request.GET.get("segment_id")
    structure_id = request.GET.get("structure_id")

    road = Road.objects.filter(pk=road_id).only("id", "geometry").first()
    if not road:
        return JsonResponse({"error": "road not found"}, status=404)

    features: List[Dict[str, Any]] = []

    road_feature = _as_feature(road.geometry, {"role": "road", "id": road.id})
    if road_feature:
        features.append(road_feature)

    sections = RoadSection.objects.filter(road_id=road.id).only("id", "geometry", "road_id")
    for section in sections:
        geometry = _section_geometry(section)
        if not geometry:
            continue
        role = "section_current" if section_id and str(section.id) == str(section_id) else "section"
        feature = _as_feature(geometry, {"role": role, "id": section.id, "road_id": section.road_id})
        if feature:
            features.append(feature)

    if section_id:
        segments = RoadSegment.objects.filter(section_id=section_id).select_related("section", "section__road")
        for segment in segments:
            geometry = _segment_geometry(segment)
            if not geometry:
                continue
            role = "segment_current" if segment_id and str(segment.id) == str(segment_id) else "segment"
            feature = _as_feature(geometry, {"role": role, "id": segment.id, "section_id": segment.section_id})
            if feature:
                features.append(feature)

    structures = StructureInventory.objects.only(
        "id",
        "road_id",
        "section_id",
        "location_point",
        "location_line",
        "geometry_type",
    )
    if section_id:
        structures = structures.filter(section_id=section_id)
    else:
        structures = structures.filter(road_id=road.id)

    for structure in structures:
        geom = structure.location_point or structure.location_line
        if not geom:
            continue
        role = "structure_current" if structure_id and str(structure.id) == str(structure_id) else "structure"
        feature = _as_feature(
            geom,
            {
                "role": role,
                "id": structure.id,
                "road_id": structure.road_id,
                "section_id": structure.section_id,
            },
        )
        if feature:
            features.append(feature)

    return JsonResponse({"type": "FeatureCollection", "features": features})
