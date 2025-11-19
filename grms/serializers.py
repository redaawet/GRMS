"""Serializers for the GRMS REST API."""

from rest_framework import serializers

from . import models
from .services import map_services


class RoadSegmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.RoadSegment
        fields = "__all__"


class RoadSectionSerializer(serializers.ModelSerializer):
    segments = RoadSegmentSerializer(many=True, read_only=True)

    class Meta:
        model = models.RoadSection
        fields = [
            "id",
            "road",
            "section_number",
            "start_chainage_km",
            "end_chainage_km",
            "length_km",
            "start_coordinates",
            "end_coordinates",
            "surface_type",
            "gravel_thickness_cm",
            "inspector_name",
            "inspection_date",
            "geometry",
            "attachments",
            "segments",
        ]


class RoadSerializer(serializers.ModelSerializer):
    sections = RoadSectionSerializer(many=True, read_only=True)

    class Meta:
        model = models.Road
        fields = "__all__"


class AdminZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.AdminZone
        fields = ["id", "name", "region"]


class AdminWoredaSerializer(serializers.ModelSerializer):
    zone_name = serializers.CharField(source="zone.name", read_only=True)

    class Meta:
        model = models.AdminWoreda
        fields = ["id", "name", "zone", "zone_name"]


class CoordinateSerializer(serializers.Serializer):
    lat = serializers.FloatField()
    lng = serializers.FloatField()


class RoadRouteRequestSerializer(serializers.Serializer):
    start = CoordinateSerializer()
    end = CoordinateSerializer()
    travel_mode = serializers.CharField(default="DRIVING")

    def validate_travel_mode(self, value: str) -> str:
        mode = (value or "DRIVING").upper()
        if mode not in map_services.TRAVEL_MODES:
            raise serializers.ValidationError("Unsupported travel mode.")
        return mode


class StructureInventorySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.StructureInventory
        fields = "__all__"


class BridgeDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.BridgeDetail
        fields = "__all__"


class CulvertDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.CulvertDetail
        fields = "__all__"


class FurnitureInventorySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.FurnitureInventory
        fields = "__all__"


class RoadConditionSurveySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.RoadConditionSurvey
        fields = "__all__"


class FurnitureConditionSurveySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.FurnitureConditionSurvey
        fields = "__all__"


class RoadConditionDetailedSurveySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.RoadConditionDetailedSurvey
        fields = "__all__"


class StructureConditionDetailedSurveySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.StructureConditionDetailedSurvey
        fields = "__all__"


class FurnitureConditionDetailedSurveySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.FurnitureConditionDetailedSurvey
        fields = "__all__"


class StructureConditionSurveySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.StructureConditionSurvey
        fields = "__all__"


class BridgeConditionSurveySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.BridgeConditionSurvey
        fields = "__all__"


class CulvertConditionSurveySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.CulvertConditionSurvey
        fields = "__all__"


class OtherStructureConditionSurveySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.OtherStructureConditionSurvey
        fields = "__all__"


class TrafficCountRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.TrafficCountRecord
        fields = "__all__"


class TrafficSurveySerializer(serializers.ModelSerializer):
    count_records = TrafficCountRecordSerializer(many=True, read_only=True)

    class Meta:
        model = models.TrafficSurvey
        fields = [
            "id",
            "road_segment",
            "survey_year",
            "cycle_number",
            "count_start_date",
            "count_end_date",
            "count_days_per_cycle",
            "count_hours_per_day",
            "night_adjustment_factor",
            "method",
            "observer",
            "location_override",
            "weather_notes",
            "qa_status",
            "created_at",
            "approved_at",
            "count_records",
        ]


class TrafficCycleSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.TrafficCycleSummary
        fields = "__all__"


class TrafficSurveySummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.TrafficSurveySummary
        fields = "__all__"


class TrafficQCSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.TrafficQC
        fields = "__all__"


class TrafficForPrioritizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.TrafficForPrioritization
        fields = "__all__"


class ActivityLookupSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ActivityLookup
        fields = "__all__"


class InterventionLookupSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.InterventionLookup
        fields = "__all__"


class UnitCostSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.UnitCost
        fields = "__all__"


class StructureInterventionSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.StructureIntervention
        fields = "__all__"


class RoadSectionInterventionSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.RoadSectionIntervention
        fields = "__all__"


class BenefitFactorSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.BenefitFactor
        fields = "__all__"


class DistressTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.DistressType
        fields = "__all__"


class DistressConditionSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.DistressCondition
        fields = "__all__"


class DistressActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.DistressActivity
        fields = "__all__"


class PrioritizationResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.PrioritizationResult
        fields = "__all__"


class AnnualWorkPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.AnnualWorkPlan
        fields = "__all__"

