from django.urls import path, include
from rest_framework import routers
from .views import RoadViewSet, RoadSectionViewSet, RoadSegmentViewSet, StructureInventoryViewSet, RoadSegmentConditionSurveyViewSet

router = routers.DefaultRouter()
router.register(r'roads', RoadViewSet)
router.register(r'sections', RoadSectionViewSet)
router.register(r'segments', RoadSegmentViewSet)
router.register(r'structures', StructureInventoryViewSet)
router.register(r'surveys', RoadSegmentConditionSurveyViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
]
