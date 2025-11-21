"""REST API views for the GRMS backend."""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional

from django.db import transaction
from django.db.models import QuerySet
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response

from . import models, serializers
from .forms import RoadAlignmentForm, RoadBasicForm, RoadSectionBasicForm
from .services import map_services
from .utils import make_point, point_to_lat_lng, utm_to_wgs84


class RoadViewSet(viewsets.ModelViewSet):
    queryset: QuerySet[models.Road] = models.Road.objects.all()
    serializer_class = serializers.RoadSerializer


class AdminZoneViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.AdminZone.objects.all()
    serializer_class = serializers.AdminZoneSerializer


class AdminWoredaViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.AdminWoreda.objects.select_related("zone").all()
    serializer_class = serializers.AdminWoredaSerializer

    def get_queryset(self):  # pragma: no cover - trivial filtering logic
        queryset = super().get_queryset()
        zone_id = self.request.query_params.get("zone")
        if zone_id:
            queryset = queryset.filter(zone_id=zone_id)
        return queryset


class RoadSectionViewSet(viewsets.ModelViewSet):
    queryset = models.RoadSection.objects.select_related("road").all()
    serializer_class = serializers.RoadSectionSerializer


class RoadSegmentViewSet(viewsets.ModelViewSet):
    queryset = models.RoadSegment.objects.select_related("section", "section__road").all()
    serializer_class = serializers.RoadSegmentSerializer


class StructureInventoryViewSet(viewsets.ModelViewSet):
    queryset = models.StructureInventory.objects.select_related("road", "section").all()
    serializer_class = serializers.StructureInventorySerializer


class FurnitureInventoryViewSet(viewsets.ModelViewSet):
    queryset = models.FurnitureInventory.objects.select_related("road_segment", "road_segment__section").all()
    serializer_class = serializers.FurnitureInventorySerializer


class RoadConditionSurveyViewSet(viewsets.ModelViewSet):
    queryset = models.RoadConditionSurvey.objects.select_related("road_segment").order_by("-inspection_date")
    serializer_class = serializers.RoadConditionSurveySerializer


class RoadConditionDetailedSurveyViewSet(viewsets.ModelViewSet):
    queryset = models.RoadConditionDetailedSurvey.objects.select_related(
        "road_segment", "road_segment__section", "distress", "activity"
    ).order_by("-inspection_date")
    serializer_class = serializers.RoadConditionDetailedSurveySerializer


class FurnitureConditionSurveyViewSet(viewsets.ModelViewSet):
    queryset = models.FurnitureConditionSurvey.objects.select_related("furniture").order_by("-inspection_date")
    serializer_class = serializers.FurnitureConditionSurveySerializer


class FurnitureConditionDetailedSurveyViewSet(viewsets.ModelViewSet):
    queryset = models.FurnitureConditionDetailedSurvey.objects.select_related(
        "furniture", "distress", "activity"
    ).order_by("-inspection_date")
    serializer_class = serializers.FurnitureConditionDetailedSurveySerializer


class StructureConditionSurveyViewSet(viewsets.ModelViewSet):
    queryset = models.StructureConditionSurvey.objects.select_related("structure").order_by("-inspection_date")
    serializer_class = serializers.StructureConditionSurveySerializer


class StructureConditionDetailedSurveyViewSet(viewsets.ModelViewSet):
    queryset = models.StructureConditionDetailedSurvey.objects.select_related(
        "structure", "structure__road", "distress", "activity"
    ).order_by("-inspection_date")
    serializer_class = serializers.StructureConditionDetailedSurveySerializer


class BridgeConditionSurveyViewSet(viewsets.ModelViewSet):
    queryset = models.BridgeConditionSurvey.objects.select_related("structure_survey").all()
    serializer_class = serializers.BridgeConditionSurveySerializer


class CulvertConditionSurveyViewSet(viewsets.ModelViewSet):
    queryset = models.CulvertConditionSurvey.objects.select_related("structure_survey").all()
    serializer_class = serializers.CulvertConditionSurveySerializer


class OtherStructureConditionSurveyViewSet(viewsets.ModelViewSet):
    queryset = models.OtherStructureConditionSurvey.objects.select_related("structure_survey").all()
    serializer_class = serializers.OtherStructureConditionSurveySerializer


class TrafficSurveyViewSet(viewsets.ModelViewSet):
    queryset = models.TrafficSurvey.objects.select_related("road_segment", "road_segment__section").all()
    serializer_class = serializers.TrafficSurveySerializer


class TrafficCountRecordViewSet(viewsets.ModelViewSet):
    queryset = models.TrafficCountRecord.objects.select_related("traffic_survey", "road_segment").all()
    serializer_class = serializers.TrafficCountRecordSerializer


class TrafficCycleSummaryViewSet(viewsets.ModelViewSet):
    queryset = models.TrafficCycleSummary.objects.select_related("traffic_survey", "road_segment").all()
    serializer_class = serializers.TrafficCycleSummarySerializer


class TrafficSurveySummaryViewSet(viewsets.ModelViewSet):
    queryset = models.TrafficSurveySummary.objects.select_related("traffic_survey", "road_segment").all()
    serializer_class = serializers.TrafficSurveySummarySerializer


class TrafficQCViewSet(viewsets.ModelViewSet):
    queryset = models.TrafficQC.objects.select_related("traffic_survey", "road_segment").all()
    serializer_class = serializers.TrafficQCSerializer


class TrafficForPrioritizationViewSet(viewsets.ModelViewSet):
    queryset = models.TrafficForPrioritization.objects.select_related("road", "road_segment").all()
    serializer_class = serializers.TrafficForPrioritizationSerializer


class ActivityLookupViewSet(viewsets.ModelViewSet):
    queryset = models.ActivityLookup.objects.all()
    serializer_class = serializers.ActivityLookupSerializer
    permission_classes = [permissions.IsAuthenticated]


class InterventionLookupViewSet(viewsets.ModelViewSet):
    queryset = models.InterventionLookup.objects.all()
    serializer_class = serializers.InterventionLookupSerializer
    permission_classes = [permissions.IsAuthenticated]


class UnitCostViewSet(viewsets.ModelViewSet):
    queryset = models.UnitCost.objects.select_related("intervention").all()
    serializer_class = serializers.UnitCostSerializer


class StructureInterventionViewSet(viewsets.ModelViewSet):
    queryset = models.StructureIntervention.objects.select_related("structure", "intervention").all()
    serializer_class = serializers.StructureInterventionSerializer


class RoadSectionInterventionViewSet(viewsets.ModelViewSet):
    queryset = models.RoadSectionIntervention.objects.select_related("section", "intervention").all()
    serializer_class = serializers.RoadSectionInterventionSerializer


class BenefitFactorViewSet(viewsets.ModelViewSet):
    queryset = models.BenefitFactor.objects.select_related("road").all()
    serializer_class = serializers.BenefitFactorSerializer


class DistressTypeViewSet(viewsets.ModelViewSet):
    queryset = models.DistressType.objects.all()
    serializer_class = serializers.DistressTypeSerializer
    permission_classes = [permissions.IsAuthenticated]


class DistressConditionViewSet(viewsets.ModelViewSet):
    queryset = models.DistressCondition.objects.select_related("distress").all()
    serializer_class = serializers.DistressConditionSerializer
    permission_classes = [permissions.IsAuthenticated]


class DistressActivityViewSet(viewsets.ModelViewSet):
    queryset = models.DistressActivity.objects.select_related("condition", "activity").all()
    serializer_class = serializers.DistressActivitySerializer
    permission_classes = [permissions.IsAuthenticated]


class PrioritizationResultViewSet(viewsets.ModelViewSet):
    queryset = models.PrioritizationResult.objects.select_related("road", "section").order_by("priority_rank")
    serializer_class = serializers.PrioritizationResultSerializer


class AnnualWorkPlanViewSet(viewsets.ModelViewSet):
    queryset = models.AnnualWorkPlan.objects.select_related("road").all()
    serializer_class = serializers.AnnualWorkPlanSerializer


def _map_region_for_road(road: models.Road) -> Dict[str, Any]:
    """Return a viewport centred on the road's admin area when available."""

    map_region = map_services.get_default_map_region()
    zone = getattr(road, "admin_zone", None)
    woreda = getattr(road, "admin_woreda", None)

    if zone or woreda:
        try:
            map_region = map_services.get_admin_area_viewport(
                zone.name if zone else None, woreda.name if woreda else None
            )
        except map_services.MapServiceError:
            map_region = map_services.get_default_map_region()

    return map_region


def _map_center_from_region(map_region: Dict[str, Any]) -> Dict[str, float]:
    center = map_region.get("center") or {}
    return {
        "lat": float(center.get("lat", 13.5)),
        "lng": float(center.get("lng", 39.5)),
        "zoom": float(center.get("zoom", 12)),
    }


def _latlng_from_request(data: Dict[str, Any], prefix: str) -> Optional[Dict[str, float]]:
    try:
        lat = float(data.get(f"{prefix}_latitude"))
        lng = float(data.get(f"{prefix}_longitude"))
    except (TypeError, ValueError):
        return None

    if lat is None or lng is None:
        return None

    return {"lat": lat, "lng": lng}


def _latlng_from_utm(data: Dict[str, Any], prefix: str) -> Optional[Dict[str, float]]:
    """Convert UTM inputs into a lat/lng pair for map previews."""

    try:
        easting = Decimal(data.get(f"{prefix}_easting"))
        northing = Decimal(data.get(f"{prefix}_northing"))
    except (TypeError, InvalidOperation):  # type: ignore[arg-type]
        return None

    if easting is None or northing is None:
        return None

    try:
        lat, lng = utm_to_wgs84(float(easting), float(northing), zone=37)
    except Exception:
        return None

    return {"lat": lat, "lng": lng}


@require_http_methods(["GET", "POST"])
def road_basic_info(request: Request):
    """First step of the road wizard – capture basic information."""

    form = RoadBasicForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        road = form.save()
        return redirect("road_alignment", road_id=road.id)

    progress_steps = [
        {"label": "Basic Info", "active": True, "complete": False},
        {"label": "Alignment", "active": False, "complete": False},
        {"label": "Completed", "active": False, "complete": False},
    ]

    return render(
        request,
        "roads/road_basic_form.html",
        {"form": form, "progress_steps": progress_steps},
    )


@require_http_methods(["GET", "POST"])
def road_alignment(request: Request, road_id: int):
    """Second step of the road wizard – capture alignment and preview map."""

    road = get_object_or_404(models.Road, pk=road_id)
    form = RoadAlignmentForm(request.POST or None, instance=road)

    start_point = point_to_lat_lng(getattr(road, "road_start_coordinates", None))
    end_point = point_to_lat_lng(getattr(road, "road_end_coordinates", None))
    map_region = _map_region_for_road(road)

    # Reflect typed coordinates on validation errors rather than defaulting to
    # the generic Tigray viewport. Fallback to UTM conversions when latitude/
    # longitude fields are empty.
    if request.method == "POST":
        start_from_form = _latlng_from_request(request.POST, "start") or _latlng_from_utm(request.POST, "start")
        end_from_form = _latlng_from_request(request.POST, "end") or _latlng_from_utm(request.POST, "end")
        if start_from_form:
            start_point = start_from_form
        if end_from_form:
            end_point = end_from_form

    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("road_detail", road_id=road.id)

    progress_steps = [
        {"label": "Basic Info", "active": False, "complete": True},
        {"label": "Alignment", "active": True, "complete": False},
        {"label": "Completed", "active": False, "complete": False},
    ]

    map_center = _map_center_from_region(map_region)
    if start_point:
        map_center.update({"lat": start_point["lat"], "lng": start_point["lng"], "zoom": 12})
    elif end_point:
        map_center.update({"lat": end_point["lat"], "lng": end_point["lng"], "zoom": 12})

    map_config = json.dumps(
        {
            "map_center": map_center,
            "map_bounds": map_region.get("bounds") or map_region.get("viewport"),
            "start": start_point,
            "end": end_point,
        }
    )

    return render(
        request,
        "roads/road_alignment_form.html",
        {"form": form, "road": road, "progress_steps": progress_steps, "map_config": map_config},
    )


@require_http_methods(["GET"])
def road_detail(request: Request, road_id: int):
    """Simple road detail page shown after completing the wizard."""

    road = get_object_or_404(
        models.Road.objects.select_related("admin_zone", "admin_woreda"), pk=road_id
    )

    progress_steps = [
        {"label": "Basic Info", "active": False, "complete": True},
        {"label": "Alignment", "active": False, "complete": True},
        {"label": "Completed", "active": True, "complete": True},
    ]

    start_point = point_to_lat_lng(getattr(road, "road_start_coordinates", None))
    end_point = point_to_lat_lng(getattr(road, "road_end_coordinates", None))
    map_region = _map_region_for_road(road)
    map_center = _map_center_from_region(map_region)

    if start_point:
        map_center.update({"lat": start_point["lat"], "lng": start_point["lng"], "zoom": 12})
    elif end_point:
        map_center.update({"lat": end_point["lat"], "lng": end_point["lng"], "zoom": 12})

    return render(
        request,
        "roads/road_detail.html",
        {
            "road": road,
            "progress_steps": progress_steps,
            "map_config": json.dumps(
                {
                    "map_center": map_center,
                    "map_bounds": map_region.get("bounds") or map_region.get("viewport"),
                    "start": start_point,
                    "end": end_point,
                }
            ),
        },
    )


@require_http_methods(["GET", "POST"])
def section_basic_info(request: Request, road_id: int):
    """First step of the section wizard – capture basic information."""

    road = get_object_or_404(models.Road, pk=road_id)
    form = RoadSectionBasicForm(
        request.POST or None,
        road=road,
    )

    if request.method == "POST" and form.is_valid():
        section = form.save()
        return redirect("section_map_preview", road_id=road.id, section_id=section.id)

    progress_steps = [
        {"label": "Section Basic Info", "active": True, "complete": False},
        {"label": "Map Preview", "active": False, "complete": False},
        {"label": "Completed", "active": False, "complete": False},
    ]

    return render(
        request,
        "sections/section_basic_form.html",
        {"form": form, "road": road, "progress_steps": progress_steps},
    )


@require_http_methods(["GET", "POST"])
def section_map_preview(request: Request, road_id: int, section_id: int):
    """Second step of the section wizard – map preview only."""

    road = get_object_or_404(models.Road.objects.select_related("admin_zone", "admin_woreda"), pk=road_id)
    section = get_object_or_404(models.RoadSection, pk=section_id, road=road)

    if request.method == "POST":
        return redirect(f"/roads/{road.id}/sections/{section.id}/details")

    zone = section.admin_zone_override or road.admin_zone
    woreda = section.admin_woreda_override or road.admin_woreda

    woreda_for_lookup = woreda if woreda and zone and woreda.zone_id == zone.id else None

    map_region = map_services.get_admin_area_viewport_or_default(
        zone.name if zone else None, woreda_for_lookup.name if woreda_for_lookup else None
    )

    start = point_to_lat_lng(getattr(road, "road_start_coordinates", None))
    end = point_to_lat_lng(getattr(road, "road_end_coordinates", None))

    progress_steps = [
        {"label": "Section Basic Info", "active": False, "complete": True},
        {"label": "Map Preview", "active": True, "complete": False},
        {"label": "Completed", "active": False, "complete": False},
    ]

    return render(
        request,
        "sections/section_map_preview.html",
        {
            "road": road,
            "section": section,
            "progress_steps": progress_steps,
            "map_has_admin_boundary": bool(map_region.get("viewport")),
            "map_config": {
                "map_region": map_region,
                "admin_area": {
                    "zone": {"id": zone.id, "name": zone.name} if zone else None,
                    "woreda": {"id": woreda.id, "name": woreda.name} if woreda else None,
                    "has_boundary": bool(map_region.get("viewport")),
                },
                "road": {
                    "id": road.id,
                    "length_km": float(road.total_length_km) if road.total_length_km is not None else None,
                    "start": start,
                    "end": end,
                },
                "section": {
                    "start_chainage_km": float(section.start_chainage_km),
                    "end_chainage_km": float(section.end_chainage_km),
                    "surface_type": section.surface_type,
                    "length_km": float(section.length_km),
                },
            },
        },
    )


@api_view(["GET", "POST"])
def update_road_route(request: Request, pk: int) -> Response:
    """Store or reuse road endpoints and retrieve the OpenStreetMap route."""

    road = get_object_or_404(models.Road, pk=pk)

    if request.method == "POST":
        serializer = serializers.RoadRouteRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        start = serializer.validated_data["start"]
        end = serializer.validated_data["end"]
        travel_mode = serializer.validated_data["travel_mode"]

        road.road_start_coordinates = make_point(start["lat"], start["lng"])
        road.road_end_coordinates = make_point(end["lat"], end["lng"])
        road.save(update_fields=["road_start_coordinates", "road_end_coordinates"])
    else:
        start = point_to_lat_lng(road.road_start_coordinates)
        end = point_to_lat_lng(road.road_end_coordinates)
        if not start or not end:
            return Response(
                {"detail": "Road is missing start or end coordinates."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = serializers.RoadRouteRequestSerializer(
            data={
                "start": start,
                "end": end,
                "travel_mode": request.query_params.get("travel_mode", "DRIVING"),
            }
        )
        serializer.is_valid(raise_exception=True)
        travel_mode = serializer.validated_data["travel_mode"]
        start = serializer.validated_data["start"]
        end = serializer.validated_data["end"]

    try:
        route = map_services.get_directions(
            start_lat=start["lat"],
            start_lng=start["lng"],
            end_lat=end["lat"],
            end_lng=end["lng"],
            travel_mode=travel_mode,
        )
    except map_services.MapServiceError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

    return Response(
        {"road": road.id, "start": start, "end": end, "travel_mode": travel_mode, "route": route},
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def preview_route(request: Request) -> Response:
    """Return a preview route for arbitrary coordinates without persisting data."""

    serializer = serializers.RoadRouteRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    coords = serializer.validated_data
    travel_mode = coords["travel_mode"]

    try:
        route = map_services.get_directions(
            start_lat=coords["start"]["lat"],
            start_lng=coords["start"]["lng"],
            end_lat=coords["end"]["lat"],
            end_lng=coords["end"]["lng"],
            travel_mode=travel_mode,
        )
    except map_services.MapServiceError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

    return Response(
        {
            "start": coords["start"],
            "end": coords["end"],
            "travel_mode": travel_mode,
            "route": route,
        }
    )


@api_view(["GET"])
def road_map_context(request: Request, pk: Optional[int] = None) -> Response:
    """Return context to display a Leaflet map for a road or default region."""

    road: Optional[models.Road] = None
    start = None
    end = None
    zone: Optional[models.AdminZone] = None
    woreda: Optional[models.AdminWoreda] = None

    if pk is not None:
        road = get_object_or_404(models.Road.objects.select_related("admin_zone", "admin_woreda"), pk=pk)
        start = point_to_lat_lng(road.road_start_coordinates)
        end = point_to_lat_lng(road.road_end_coordinates)
        zone = road.admin_zone
        woreda = road.admin_woreda

    zone_override = request.query_params.get("zone_id")
    woreda_override = request.query_params.get("woreda_id")

    if zone_override:
        zone = get_object_or_404(models.AdminZone, pk=zone_override)
    if woreda_override:
        woreda = get_object_or_404(models.AdminWoreda.objects.select_related("zone"), pk=woreda_override)
        if zone_override and woreda.zone_id != zone.id:
            return Response(
                {"detail": "Selected woreda does not belong to the selected zone."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        zone = woreda.zone
    elif woreda and zone and woreda.zone_id != zone.id:
        woreda = None

    woreda_for_lookup = woreda if woreda and zone and woreda.zone_id == zone.id else None

    map_region = map_services.get_admin_area_viewport_or_default(
        zone.name if zone else None, woreda_for_lookup.name if woreda_for_lookup else None
    )

    return Response(
        {
            "road": road.id if road else None,
            "zone": {"id": zone.id, "name": zone.name} if zone else None,
            "woreda": {"id": woreda.id, "name": woreda.name} if woreda else None,
            "start": start,
            "end": end,
            "road_length_km": float(road.total_length_km) if road and road.total_length_km else None,
            "map_region": map_region,
            "travel_modes": sorted(map_services.TRAVEL_MODES),
        }
    )


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def run_prioritization(request: Request) -> Response:
    """Execute the prioritisation algorithm and return the ordered results."""

    weights: Dict[str, float] = {
        "w1": float(request.data.get("weights", {}).get("w1", 0.40)),
        "w2": float(request.data.get("weights", {}).get("w2", 0.25)),
        "w3": float(request.data.get("weights", {}).get("w3", 0.15)),
        "w4": float(request.data.get("weights", {}).get("w4", 0.10)),
        "w5": float(request.data.get("weights", {}).get("w5", 0.10)),
    }
    fiscal_year = request.data.get("fiscal_year")

    traffic_values = models.TrafficForPrioritization.objects.all()
    if fiscal_year:
        traffic_values = traffic_values.filter(fiscal_year=fiscal_year)
    pcu_values = [float(item.value) for item in traffic_values.filter(value_type="PCU")]
    pcu_min = min(pcu_values) if pcu_values else 0.0
    pcu_max = max(pcu_values) if pcu_values else 0.0

    created_results: List[models.PrioritizationResult] = []
    with transaction.atomic():
        for road in models.Road.objects.all():
            latest_survey = (
                models.RoadConditionSurvey.objects.filter(road_segment__section__road=road)
                .order_by("-inspection_date")
                .first()
            )
            cs_norm = float(latest_survey.calculated_mci) if latest_survey and latest_survey.calculated_mci else 0.0

            traffic_qs = models.TrafficForPrioritization.objects.filter(road=road)
            if fiscal_year:
                traffic_qs = traffic_qs.filter(fiscal_year=fiscal_year)
            traffic_value = traffic_qs.filter(value_type="PCU").order_by("-fiscal_year").first()
            pcu = float(traffic_value.value) if traffic_value else 0.0
            if pcu_max != pcu_min:
                pcu_norm = 100.0 * (pcu - pcu_min) / (pcu_max - pcu_min)
                pcu_norm = max(0.0, min(100.0, pcu_norm))
            else:
                pcu_norm = 0.0

            benefit = models.BenefitFactor.objects.filter(road=road).first()
            has_ei = benefit and benefit.total_benefit_score is not None
            ei = float(benefit.total_benefit_score) if has_ei else 0.0

            sr = 0.0  # Placeholder – safety risk scoring can be supplied later
            tlm_norm = 0.0  # Placeholder – months since last maintenance when data is available

            priority_score = (
                weights["w1"] * cs_norm
                + weights["w2"] * pcu_norm
                + weights["w3"] * ei
                + weights["w4"] * sr
                + weights["w5"] * tlm_norm
            )

            models.PrioritizationResult.objects.filter(
                road=road,
                fiscal_year=fiscal_year or 0,
            ).delete()

            result = models.PrioritizationResult.objects.create(
                road=road,
                fiscal_year=fiscal_year or 0,
                population_served=road.population_served,
                benefit_score=Decimal(f"{ei:.2f}") if has_ei else None,
                improvement_cost=Decimal("0"),
                ranking_index=Decimal(f"{priority_score:.4f}"),
                priority_rank=0,
            )
            created_results.append(result)

        created_results.sort(key=lambda item: item.ranking_index, reverse=True)
        for rank, result in enumerate(created_results, start=1):
            result.priority_rank = rank
            result.save(update_fields=["priority_rank"])

    serializer = serializers.PrioritizationResultSerializer(created_results, many=True)
    return Response(serializer.data)

