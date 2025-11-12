from django.contrib import admin

from .models import (
    AnnualWorkPlan,
    BridgeConditionSurvey,
    CulvertConditionSurvey,
    FurnitureConditionSurvey,
    FurnitureInventory,
    QAStatus,
    Road,
    RoadConditionSurvey,
    RoadSection,
    RoadSegment,
    StructureConditionSurvey,
    StructureInventory,
    TrafficSurvey,
)


@admin.register(Road)
class RoadAdmin(admin.ModelAdmin):
    list_display = ("id", "road_name_from", "road_name_to", "surface_type", "managing_authority")
    search_fields = ("road_name_from", "road_name_to", "admin_zone", "admin_woreda")
    list_filter = ("surface_type", "managing_authority")


@admin.register(RoadSection)
class RoadSectionAdmin(admin.ModelAdmin):
    list_display = ("id", "road", "section_number", "surface_type", "length_km")
    list_filter = ("surface_type",)
    search_fields = ("road__road_name_from", "road__road_name_to", "section_number")


@admin.register(RoadSegment)
class RoadSegmentAdmin(admin.ModelAdmin):
    list_display = ("id", "section", "station_from_km", "station_to_km", "cross_section")
    list_filter = ("cross_section", "terrain_transverse", "terrain_longitudinal")
    search_fields = (
        "section__road__road_name_from",
        "section__road__road_name_to",
        "section__section_number",
    )


@admin.register(StructureInventory)
class StructureInventoryAdmin(admin.ModelAdmin):
    list_display = ("id", "road", "structure_category", "station_km", "condition_code")
    list_filter = ("structure_category", "condition_code")
    search_fields = ("road__road_name_from", "road__road_name_to", "structure_type")


@admin.register(FurnitureInventory)
class FurnitureInventoryAdmin(admin.ModelAdmin):
    list_display = ("id", "road_segment", "furniture_type", "chainage_from_km", "chainage_to_km")
    list_filter = ("furniture_type",)
    search_fields = (
        "road_segment__section__road__road_name_from",
        "road_segment__section__road__road_name_to",
    )


@admin.register(QAStatus)
class QAStatusAdmin(admin.ModelAdmin):
    list_display = ("id", "status")
    search_fields = ("status",)


@admin.register(AnnualWorkPlan)
class AnnualWorkPlanAdmin(admin.ModelAdmin):
    list_display = ("id", "fiscal_year", "region", "woreda", "road", "status")
    list_filter = ("fiscal_year", "region", "status")
    search_fields = ("road__road_name_from", "road__road_name_to", "region", "woreda")


@admin.register(RoadConditionSurvey)
class RoadConditionSurveyAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "road_segment",
        "inspection_date",
        "calculated_mci",
        "is_there_bottleneck",
    )
    list_filter = ("inspection_date", "is_there_bottleneck")
    search_fields = (
        "road_segment__section__road__road_name_from",
        "road_segment__section__road__road_name_to",
    )


@admin.register(StructureConditionSurvey)
class StructureConditionSurveyAdmin(admin.ModelAdmin):
    list_display = ("id", "structure", "survey_year", "condition_rating", "qa_status")
    list_filter = ("survey_year", "condition_rating", "qa_status")
    search_fields = ("structure__road__road_name_from", "structure__road__road_name_to")


@admin.register(BridgeConditionSurvey)
class BridgeConditionSurveyAdmin(admin.ModelAdmin):
    list_display = ("structure_survey", "deck_condition", "abutment_condition", "pier_condition")
    list_filter = ("deck_condition", "abutment_condition", "pier_condition")


@admin.register(CulvertConditionSurvey)
class CulvertConditionSurveyAdmin(admin.ModelAdmin):
    list_display = ("structure_survey", "inlet_condition", "outlet_condition", "barrel_condition")
    list_filter = ("inlet_condition", "outlet_condition", "barrel_condition")


@admin.register(FurnitureConditionSurvey)
class FurnitureConditionSurveyAdmin(admin.ModelAdmin):
    list_display = ("id", "furniture", "survey_year", "condition_rating", "qa_status")
    list_filter = ("survey_year", "condition_rating", "qa_status")
    search_fields = (
        "furniture__road_segment__section__road__road_name_from",
        "furniture__road_segment__section__road__road_name_to",
    )


@admin.register(TrafficSurvey)
class TrafficSurveyAdmin(admin.ModelAdmin):
    list_display = ("id", "road_segment", "survey_year", "cycle_number", "qa_status")
    list_filter = ("survey_year", "cycle_number", "qa_status")
    search_fields = ("road_segment__section__road__road_name_from", "road_segment__section__road__road_name_to")

