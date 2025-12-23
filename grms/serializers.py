"""Serializers for the GRMS REST API."""

from rest_framework import serializers

from traffic import models as traffic_models
from . import models, utils
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
            "sequence_on_road",
            "name",
            "start_chainage_km",
            "end_chainage_km",
            "length_km",
            "surface_type",
            "surface_thickness_cm",
            "admin_zone_override",
            "admin_woreda_override",
            "notes",
            "segments",
        ]
        read_only_fields = ("length_km",)


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
    lat = serializers.FloatField(required=False)
    lng = serializers.FloatField(required=False)
    easting = serializers.FloatField(required=False)
    northing = serializers.FloatField(required=False)

    def validate(self, attrs):
        lat = attrs.get("lat")
        lng = attrs.get("lng")
        easting = attrs.get("easting")
        northing = attrs.get("northing")

        if lat is not None and lng is not None:
            return {"lat": lat, "lng": lng}

        if easting is not None and northing is not None:
            lat, lon = utils.utm_to_wgs84(easting, northing, zone=37)
            return {"lat": lat, "lng": lon, "easting": easting, "northing": northing}

        raise serializers.ValidationError(
            "Provide latitude/longitude or easting/northing for each coordinate."
        )


class RoadRouteRequestSerializer(serializers.Serializer):
    start = CoordinateSerializer()
    end = CoordinateSerializer()
    travel_mode = serializers.CharField(default="DRIVING")

    def validate_travel_mode(self, value: str) -> str:
        mode = (value or "DRIVING").upper()
        if mode not in map_services.TRAVEL_MODES:
            raise serializers.ValidationError("Unsupported travel mode.")
        return mode


class LineStringGeometrySerializer(serializers.Serializer):
    coordinates = serializers.ListField(
        child=serializers.ListField(
            child=serializers.FloatField(),
            min_length=2,
            max_length=2,
        )
    )
    type = serializers.CharField(required=False)

    def validate(self, attrs):
        coords = attrs.get("coordinates")
        if not coords or len(coords) < 2:
            raise serializers.ValidationError("At least two coordinate pairs are required.")

        geom_type = attrs.get("type")
        if geom_type and geom_type != "LineString":
            raise serializers.ValidationError("Only LineString geometries are supported.")

        return {"coordinates": coords}


class StructureInventorySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.StructureInventory
        fields = (
            "id",
            "road",
            "section",
            "structure_category",
            "structure_name",
            "geometry_type",
            "station_km",
            "easting_m",
            "northing_m",
            "utm_zone",
            "location_latitude",
            "location_longitude",
            "location_point",
            "start_chainage_km",
            "end_chainage_km",
            "location_line",
            "comments",
            "attachments",
            "created_date",
            "modified_date",
        )


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
        model = traffic_models.TrafficCountRecord
        fields = "__all__"


class TrafficSurveySerializer(serializers.ModelSerializer):
    count_records = TrafficCountRecordSerializer(many=True, read_only=True)

    class Meta:
        model = traffic_models.TrafficSurvey
        fields = [
            "id",
            "road",
            "survey_year",
            "cycle_number",
            "count_start_date",
            "count_end_date",
            "count_days_per_cycle",
            "count_hours_per_day",
            "night_adjustment_factor",
            "override_night_factor",
            "method",
            "observer",
            "station_location",
            "weather_notes",
            "qa_status",
            "created_at",
            "approved_at",
            "count_records",
        ]


class TrafficCycleSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = traffic_models.TrafficCycleSummary
        fields = "__all__"


class TrafficSurveySummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = traffic_models.TrafficSurveySummary
        fields = "__all__"


class TrafficQCSerializer(serializers.ModelSerializer):
    class Meta:
        model = traffic_models.TrafficQc
        fields = "__all__"


class TrafficForPrioritizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = traffic_models.TrafficForPrioritization
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
    lt_code = serializers.SerializerMethodField()
    lt_type = serializers.SerializerMethodField()
    lt_score = serializers.SerializerMethodField()

    def get_lt_code(self, obj):
        return getattr(obj.road.socioeconomic.road_link_type, "code", None) if hasattr(obj.road, "socioeconomic") else None

    def get_lt_type(self, obj):
        return getattr(obj.road.socioeconomic.road_link_type, "name", None) if hasattr(obj.road, "socioeconomic") else None

    def get_lt_score(self, obj):
        return getattr(obj.road.socioeconomic.road_link_type, "score", None) if hasattr(obj.road, "socioeconomic") else None

    class Meta:
        model = models.PrioritizationResult
        fields = "__all__"


class AnnualWorkPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.AnnualWorkPlan
        fields = "__all__"
