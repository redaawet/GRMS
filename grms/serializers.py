from rest_framework import serializers

from .models import (
    Road,
    RoadSection,
    RoadSegment,
    RoadSegmentConditionSurvey,
    StructureInventory,
)

class RoadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Road
        fields = '__all__'

class RoadSectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoadSection
        fields = '__all__'

class RoadSegmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoadSegment
        fields = '__all__'

class StructureInventorySerializer(serializers.ModelSerializer):
    class Meta:
        model = StructureInventory
        fields = '__all__'

class RoadSegmentConditionSurveySerializer(serializers.ModelSerializer):
    class Meta:
        model = RoadSegmentConditionSurvey
        fields = '__all__'
