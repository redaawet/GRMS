from django.contrib.admin.apps import AdminConfig


class GRMSAdminConfig(AdminConfig):
    default_site = "grms.admin.GRMSAdminSite"
