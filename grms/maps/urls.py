from django.urls import path

from .views import map_context

app_name = "grms_maps"

urlpatterns = [
    path("context/", map_context, name="map_context"),
]
