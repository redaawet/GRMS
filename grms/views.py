from rest_framework import permissions, viewsets

from .models import (
    Road,
    RoadSection,
    RoadSegment,
    RoadSegmentConditionSurvey,
    StructureInventory,
)
from .serializers import (
    RoadSectionSerializer,
    RoadSegmentConditionSurveySerializer,
    RoadSegmentSerializer,
    RoadSerializer,
    StructureInventorySerializer,
)

class RoadViewSet(viewsets.ModelViewSet):
    queryset = Road.objects.all()
    serializer_class = RoadSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

class RoadSectionViewSet(viewsets.ModelViewSet):
    queryset = RoadSection.objects.all()
    serializer_class = RoadSectionSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

class RoadSegmentViewSet(viewsets.ModelViewSet):
    queryset = RoadSegment.objects.all()
    serializer_class = RoadSegmentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

class StructureInventoryViewSet(viewsets.ModelViewSet):
    queryset = StructureInventory.objects.all()
    serializer_class = StructureInventorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

class RoadSegmentConditionSurveyViewSet(viewsets.ModelViewSet):
    queryset = RoadSegmentConditionSurvey.objects.all().order_by('-created_at')
    serializer_class = RoadSegmentConditionSurveySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
