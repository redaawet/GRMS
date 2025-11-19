from django.urls import path, include

from grms.admin import grms_admin_site

urlpatterns = [
    path('admin/', grms_admin_site.urls),
    path('', include('grms.urls')),
]
