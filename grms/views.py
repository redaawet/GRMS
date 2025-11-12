from rest_framework import viewsets, permissions
from .models import Road, RoadSection, RoadSegment, StructureInventory, RoadSegmentConditionSurvey
from .serializers import RoadSerializer, RoadSectionSerializer, RoadSegmentSerializer, StructureInventorySerializer, RoadSegmentConditionSurveySerializer

class RoadViewSet(viewsets.ModelViewSet):
    queryset = Road.objects.all()
    serializer_class = RoadSerializer
    permission_classes = [permissions.AllowAny]

class RoadSectionViewSet(viewsets.ModelViewSet):
    queryset = RoadSection.objects.all()
    serializer_class = RoadSectionSerializer
    permission_classes = [permissions.AllowAny]

class RoadSegmentViewSet(viewsets.ModelViewSet):
    queryset = RoadSegment.objects.all()
    serializer_class = RoadSegmentSerializer
    permission_classes = [permissions.AllowAny]

class StructureInventoryViewSet(viewsets.ModelViewSet):
    queryset = StructureInventory.objects.all()
    serializer_class = StructureInventorySerializer
    permission_classes = [permissions.AllowAny]

class RoadSegmentConditionSurveyViewSet(viewsets.ModelViewSet):
    queryset = RoadSegmentConditionSurvey.objects.all().order_by('-created_at')
    serializer_class = RoadSegmentConditionSurveySerializer
    permission_classes = [permissions.AllowAny]
