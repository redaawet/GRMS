from __future__ import annotations

from decimal import Decimal
from typing import Optional

from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from grms import models
from grms.gis.geojson import feature, feature_collection, to_4326
from grms.utils import (
    _extract_coordinates,
    _haversine_km,
    geos_length_km,
    geometry_length_km,
    make_point,
    slice_linestring_by_chainage,
    utm_to_wgs84,
)


def _as_float(value: Optional[Decimal]) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def _warning_if_missing(geom):
    return {"warning": "missing_geometry"} if geom is None else {}


def _normalize_line_geom(geom):
    if not geom:
        return None
    if isinstance(geom, dict):
        if geom.get("type") == "MultiLineString":
            coords = geom.get("coordinates") or []
            flat = [pt for line in coords for pt in line]
            return {"type": "LineString", "coordinates": flat, "srid": geom.get("srid")}
        return geom
    geom_type = getattr(geom, "geom_type", None)
    if geom_type == "MultiLineString":
        merged = None
        if hasattr(geom, "linemerge"):
            merged = geom.linemerge()
        elif hasattr(geom, "unary_union"):
            merged = geom.unary_union() if callable(geom.unary_union) else geom.unary_union
        if merged:
            geom = merged
            geom_type = getattr(geom, "geom_type", None)
        if geom_type == "MultiLineString":
            parts = list(geom) if hasattr(geom, "__iter__") else []
            if parts:
                geom = max(parts, key=lambda part: getattr(part, "length", 0))
    return geom


def _section_geometry(section: models.RoadSection, road_geom):
    if section.geometry:
        return _normalize_line_geom(section.geometry)
    start_km = _as_float(section.start_chainage_km)
    end_km = _as_float(section.end_chainage_km)
    if road_geom and start_km is not None and end_km is not None:
        sliced = slice_linestring_by_chainage(road_geom, start_km, end_km)
        if sliced:
            return _normalize_line_geom(sliced.get("geometry"))
    return None


def _segment_geometry(segment: models.RoadSegment, section_geom):
    start_km = _as_float(segment.station_from_km)
    end_km = _as_float(segment.station_to_km)
    if section_geom and start_km is not None and end_km is not None:
        sliced = slice_linestring_by_chainage(section_geom, start_km, end_km)
        if sliced:
            return _normalize_line_geom(sliced.get("geometry"))
    return None


def _interpolate_point_on_line(geom, station_km: float):
    if not geom:
        return None
    if hasattr(geom, "interpolate"):
        total_km = geos_length_km(geom)
        if total_km <= 0:
            return None
        fraction = min(1.0, max(0.0, float(station_km) / float(total_km)))
        return geom.interpolate(fraction, normalized=True)

    coordinates = _extract_coordinates(geom)
    if len(coordinates) < 2:
        return None
    total_km = geometry_length_km(geom)
    if total_km <= 0:
        return None
    target_km = min(float(station_km), total_km)
    cumulative = 0.0
    for start, end in zip(coordinates[:-1], coordinates[1:]):
        segment_km = _haversine_km(start, end)
        if cumulative + segment_km >= target_km:
            fraction = (target_km - cumulative) / segment_km if segment_km else 0.0
            lon = start[0] + (end[0] - start[0]) * fraction
            lat = start[1] + (end[1] - start[1]) * fraction
            return {"type": "Point", "coordinates": [lon, lat], "srid": 4326}
        cumulative += segment_km
    lon, lat = coordinates[-1]
    return {"type": "Point", "coordinates": [lon, lat], "srid": 4326}


def _structure_geometry(structure: models.StructureInventory, line_geom):
    geom = structure.location_point or structure.location_line
    if geom:
        geom = to_4326(geom)
        if (
            isinstance(geom, dict)
            and geom.get("type") == "Point"
            and isinstance(geom.get("coordinates"), (list, tuple))
            and len(geom.get("coordinates")) >= 2
        ):
            lon, lat = geom["coordinates"][:2]
            if (abs(lon) > 180 or abs(lat) > 90) and structure.utm_zone:
                try:
                    lat, lng = utm_to_wgs84(float(lon), float(lat), zone=int(structure.utm_zone))
                    geom = make_point(lat, lng)
                except Exception:
                    pass
        return geom

    lat = _as_float(getattr(structure, "location_latitude", None))
    lng = _as_float(getattr(structure, "location_longitude", None))
    if lat is not None and lng is not None:
        return make_point(lat, lng)

    if structure.easting_m is not None and structure.northing_m is not None:
        try:
            zone = int(getattr(structure, "utm_zone", None) or 37)
            lat, lng = utm_to_wgs84(float(structure.easting_m), float(structure.northing_m), zone=zone)
            return make_point(lat, lng)
        except Exception:
            pass

    station_km = _as_float(structure.station_km)
    if station_km is None and structure.start_chainage_km is not None and structure.end_chainage_km is not None:
        station_km = _as_float((structure.start_chainage_km + structure.end_chainage_km) / 2)
    if station_km is not None and line_geom:
        derived = _interpolate_point_on_line(line_geom, station_km)
        return to_4326(derived)

    return None


@staff_member_required
def road_sections_geojson(request, road_id: int, current_section_id: Optional[int] = None):
    road = get_object_or_404(models.Road, pk=road_id)
    road_geom = _normalize_line_geom(to_4326(road.geometry))
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
    road_geom = _normalize_line_geom(to_4326(section.road.geometry))
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
    road_geom = _normalize_line_geom(to_4326(road.geometry))
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
        geom = _structure_geometry(structure, section_geom or road_geom)
        role = (
            "structure_current"
            if current_structure_id and structure.id == current_structure_id
            else "structure"
        )
        features.append(feature(geom, role, structure.id, _warning_if_missing(geom)))

    return JsonResponse(feature_collection(features))
