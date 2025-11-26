from django.urls import path, include

from grms.admin import grms_admin_site
from grms.views import save_road_geometry

urlpatterns = [
    path('admin/', grms_admin_site.urls),
    path("api/roads/<int:pk>/geometry/", save_road_geometry),
    path('', include('grms.urls')),
]
