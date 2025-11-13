from django.contrib import admin

from . import models


admin.site.register(models.AdminZone)
admin.site.register(models.AdminWoreda)
admin.site.register(models.Road)
admin.site.register(models.RoadSection)
admin.site.register(models.RoadSegment)
admin.site.register(models.StructureInventory)
admin.site.register(models.FurnitureInventory)
admin.site.register(models.QAStatus)
admin.site.register(models.AnnualWorkPlan)
admin.site.register(models.ActivityLookup)
admin.site.register(models.DistressType)
admin.site.register(models.DistressCondition)
admin.site.register(models.DistressActivity)
admin.site.register(models.RoadConditionSurvey)
admin.site.register(models.RoadConditionDetailedSurvey)
admin.site.register(models.StructureConditionDetailedSurvey)
admin.site.register(models.FurnitureConditionDetailedSurvey)
