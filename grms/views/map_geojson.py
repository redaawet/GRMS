from __future__ import annotations

from decimal import Decimal
from typing import Optional

from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from grms import models
from grms.gis.geojson import feature, feature_collection, to_4326
from grms.utils import make_point, slice_geometry_by_chainage, slice_linestring_by_chainage, utm_to_wgs84


def _as_float(value: Optional[Decimal]) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def _warning_if_missing(geom):
    return {"warning": "missing_geometry"} if geom is None else {}


def _section_geometry(section: models.RoadSection, road_geom):
    if section.geometry:
        return section.geometry
    start_km = _as_float(section.start_chainage_km)
    end_km = _as_float(section.end_chainage_km)
    if road_geom and start_km is not None and end_km is not None:
        sliced = slice_linestring_by_chainage(road_geom, start_km, end_km)
        if not sliced:
            sliced_geom = slice_geometry_by_chainage(road_geom, start_km, end_km)
            if sliced_geom:
                return sliced_geom
        if sliced:
            return sliced.get("geometry")
    return None


def _segment_geometry(segment: models.RoadSegment, section_geom):
    start_km = _as_float(segment.station_from_km)
    end_km = _as_float(segment.station_to_km)
    if section_geom and start_km is not None and end_km is not None:
        sliced = slice_linestring_by_chainage(section_geom, start_km, end_km)
        if not sliced:
            sliced_geom = slice_geometry_by_chainage(section_geom, start_km, end_km)
            if sliced_geom:
                return sliced_geom
        if sliced:
            return sliced.get("geometry")
    return None


def _structure_geometry(structure: models.StructureInventory):
    if structure.location_point:
        return structure.location_point
    if structure.location_latitude is not None and structure.location_longitude is not None:
        return make_point(float(structure.location_latitude), float(structure.location_longitude))
    if structure.easting_m is not None and structure.northing_m is not None:
        try:
            lat, lng = utm_to_wgs84(float(structure.easting_m), float(structure.northing_m), zone=structure.utm_zone)
        except Exception:
            return None
        return make_point(lat, lng)
    return None


@staff_member_required
def road_sections_geojson(request, road_id: int, current_section_id: Optional[int] = None):
    road = get_object_or_404(models.Road, pk=road_id)
    road_geom = to_4326(road.geometry)
    features = [
        feature(road_geom, "road", road.id, _warning_if_missing(road_geom)),
    ]

    sections = models.RoadSection.objects.filter(road_id=road_id).order_by("sequence_on_road", "id")
    for section in sections:
        geom = to_4326(_section_geometry(section, road_geom))
        role = "section_current" if current_section_id and section.id == current_section_id else "section"
        features.append(feature(geom, role, section.id, _warning_if_missing(geom)))

    return JsonResponse(feature_collection(features))


@staff_member_required
def section_segments_geojson(request, section_id: int, current_segment_id: Optional[int] = None):
    section = get_object_or_404(models.RoadSection.objects.select_related("road"), pk=section_id)
    road_geom = to_4326(section.road.geometry)
    features = [
        feature(road_geom, "road", section.road_id, _warning_if_missing(road_geom)),
    ]

    section_geom = to_4326(_section_geometry(section, road_geom))
    features.append(feature(section_geom, "section_current", section.id, _warning_if_missing(section_geom)))

    segments = models.RoadSegment.objects.filter(section_id=section_id).order_by("sequence_on_section", "id")
    for segment in segments:
        geom = to_4326(_segment_geometry(segment, section_geom))
        role = "segment_current" if current_segment_id and segment.id == current_segment_id else "segment"
        features.append(feature(geom, role, segment.id, _warning_if_missing(geom)))

    return JsonResponse(feature_collection(features))


@staff_member_required
def structure_geojson(
    request,
    road_id: int,
    section_id: Optional[int] = None,
    current_structure_id: Optional[int] = None,
):
    road = get_object_or_404(models.Road, pk=road_id)
    road_geom = to_4326(road.geometry)
    features = [
        feature(road_geom, "road", road.id, _warning_if_missing(road_geom)),
    ]

    section_geom = None
    if section_id:
        section = get_object_or_404(models.RoadSection, pk=section_id, road_id=road_id)
        section_geom = to_4326(_section_geometry(section, road_geom))
        features.append(feature(section_geom, "section_current", section.id, _warning_if_missing(section_geom)))

    structures_qs = models.StructureInventory.objects.filter(road_id=road_id)
    if section_id:
        structures_qs = structures_qs.filter(section_id=section_id)

    for structure in structures_qs.order_by("id"):
        geom = to_4326(_structure_geometry(structure))
        role = (
            "structure_current"
            if current_structure_id and structure.id == current_structure_id
            else "structure"
        )
        features.append(feature(geom, role, structure.id, _warning_if_missing(geom)))

    return JsonResponse(feature_collection(features))
