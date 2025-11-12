"""REST API views for the GRMS backend."""

from __future__ import annotations

from decimal import Decimal
from typing import Dict, List

from django.db import transaction
from django.db.models import QuerySet
from rest_framework import permissions, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response

from . import models, serializers


class RoadViewSet(viewsets.ModelViewSet):
    queryset: QuerySet[models.Road] = models.Road.objects.all()
    serializer_class = serializers.RoadSerializer


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


class FurnitureConditionSurveyViewSet(viewsets.ModelViewSet):
    queryset = models.FurnitureConditionSurvey.objects.select_related("furniture").order_by("-inspection_date")
    serializer_class = serializers.FurnitureConditionSurveySerializer


class StructureConditionSurveyViewSet(viewsets.ModelViewSet):
    queryset = models.StructureConditionSurvey.objects.select_related("structure").order_by("-inspection_date")
    serializer_class = serializers.StructureConditionSurveySerializer


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


class PrioritizationResultViewSet(viewsets.ModelViewSet):
    queryset = models.PrioritizationResult.objects.select_related("road", "section").order_by("priority_rank")
    serializer_class = serializers.PrioritizationResultSerializer


class AnnualWorkPlanViewSet(viewsets.ModelViewSet):
    queryset = models.AnnualWorkPlan.objects.select_related("road").all()
    serializer_class = serializers.AnnualWorkPlanSerializer


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

