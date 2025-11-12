"""URL configuration for the GRMS API."""

from django.urls import include, path
from rest_framework import routers
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from . import views


router = routers.DefaultRouter()
router.register(r"roads", views.RoadViewSet)
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
    path("api/", include(router.urls)),
    path("api/auth/login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/prioritize/", views.run_prioritization, name="run_prioritization"),
]

