"""URL configuration for the GRMS API."""

from django.urls import include, path
from rest_framework import routers
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from . import views
from .views.map_geojson import (
    road_sections_geojson,
    section_segments_geojson,
    structure_geojson,
)


router = routers.DefaultRouter()
router.register(r"roads", views.RoadViewSet)
router.register(r"admin-zones", views.AdminZoneViewSet)
router.register(r"admin-woredas", views.AdminWoredaViewSet)
router.register(r"sections", views.RoadSectionViewSet)
router.register(r"segments", views.RoadSegmentViewSet)
router.register(r"structures", views.StructureInventoryViewSet)
router.register(r"furniture", views.FurnitureInventoryViewSet)
router.register(r"road-surveys", views.RoadConditionSurveyViewSet)
router.register(r"road-detailed-surveys", views.RoadConditionDetailedSurveyViewSet)
router.register(r"furniture-surveys", views.FurnitureConditionSurveyViewSet)
router.register(r"furniture-detailed-surveys", views.FurnitureConditionDetailedSurveyViewSet)
router.register(r"structure-surveys", views.StructureConditionSurveyViewSet)
router.register(r"structure-detailed-surveys", views.StructureConditionDetailedSurveyViewSet)
router.register(r"bridge-surveys", views.BridgeConditionSurveyViewSet)
router.register(r"culvert-surveys", views.CulvertConditionSurveyViewSet)
router.register(r"other-structure-surveys", views.OtherStructureConditionSurveyViewSet)
router.register(r"traffic-surveys", views.TrafficSurveyViewSet)
router.register(r"traffic-counts", views.TrafficCountRecordViewSet)
router.register(r"traffic-cycle-summaries", views.TrafficCycleSummaryViewSet)
router.register(r"traffic-survey-summaries", views.TrafficSurveySummaryViewSet)
router.register(r"traffic-qc", views.TrafficQCViewSet)
router.register(r"traffic-prioritization", views.TrafficForPrioritizationViewSet)
router.register(r"activity-lookup", views.ActivityLookupViewSet)
router.register(r"interventions", views.InterventionLookupViewSet)
router.register(r"unit-costs", views.UnitCostViewSet)
router.register(r"structure-interventions", views.StructureInterventionViewSet)
router.register(r"section-interventions", views.RoadSectionInterventionViewSet)
router.register(r"benefit-factors", views.BenefitFactorViewSet)
router.register(r"distress-types", views.DistressTypeViewSet)
router.register(r"distress-conditions", views.DistressConditionViewSet)
router.register(r"distress-activities", views.DistressActivityViewSet)
router.register(r"prioritization-results", views.PrioritizationResultViewSet)
router.register(r"annual-work-plans", views.AnnualWorkPlanViewSet)


urlpatterns = [
    path("admin/dashboard/", views.dashboard_view, name="dashboard"),
    path("roads/create/basic", views.road_basic_info, name="road_basic_info"),
    path("roads/<int:road_id>/alignment", views.road_alignment, name="road_alignment"),
    path("roads/<int:road_id>", views.road_detail, name="road_detail"),
    path(
        "roads/<int:road_id>/sections/create/basic",
        views.section_basic_info,
        name="section_basic_info",
    ),
    path(
        "roads/<int:road_id>/sections/<int:section_id>/map",
        views.section_map_preview,
        name="section_map_preview",
    ),
    path(
        "maps/road/<int:road_id>/sections/",
        road_sections_geojson,
        name="map_road_sections",
    ),
    path(
        "maps/road/<int:road_id>/sections/<int:current_section_id>/",
        road_sections_geojson,
        name="map_road_sections_current",
    ),
    path(
        "maps/section/<int:section_id>/segments/",
        section_segments_geojson,
        name="map_section_segments",
    ),
    path(
        "maps/section/<int:section_id>/segments/<int:current_segment_id>/",
        section_segments_geojson,
        name="map_section_segments_current",
    ),
    path(
        "maps/road/<int:road_id>/structures/",
        structure_geojson,
        name="map_road_structures",
    ),
    path(
        "maps/road/<int:road_id>/section/<int:section_id>/structures/",
        structure_geojson,
        name="map_section_structures",
    ),
    path(
        "maps/road/<int:road_id>/structures/<int:current_structure_id>/",
        structure_geojson,
        name="map_road_structures_current",
    ),
    path(
        "maps/road/<int:road_id>/section/<int:section_id>/structures/<int:current_structure_id>/",
        structure_geojson,
        name="map_section_structures_current",
    ),
    path("api/auth/login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/roads/map-context/", views.road_map_context_default, name="road_map_context_default"),
    path("api/routes/preview/", views.preview_route, name="route_preview"),
    path("api/roads/<int:pk>/geometry/", views.update_road_geometry, name="road_geometry"),
    path("api/roads/<int:pk>/route/", views.update_road_route, name="road_route"),
    path("api/roads/<int:pk>/map-context/", views.road_map_context, name="road_map_context"),
    path("api/prioritize/", views.run_prioritization, name="run_prioritization"),
    path("api/", include(router.urls)),
]
