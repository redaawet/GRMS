from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from grms.admin import grms_admin_site


class GRMSAdminSiteTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="admin", email="admin@example.com", password="password"
        )
        self.client = Client()
        self.client.force_login(self.user)
        self.factory = RequestFactory()

    def test_dashboard_uses_custom_template_and_sections(self):
        response = self.client.get(reverse("admin:index"))
        self.assertEqual(response.status_code, 200)

        rendered_templates = {template.name for template in response.templates if template.name}
        self.assertIn("admin/grms_index.html", rendered_templates)

        sections = response.context["sections"]
        self.assertTrue(sections)
        self.assertTrue(any(section["title"] == "Inventories" for section in sections))
        self.assertTrue(
            any(model["object_name"] == "Road" for section in sections for model in section["models"])
        )

    def test_custom_admin_site_replaces_default_django_site(self):
        self.assertIs(admin.site, grms_admin_site)
        self.assertIs(admin.sites.site, grms_admin_site)

    def test_app_index_redirects_to_dashboard(self):
        response = self.client.get("/admin/auth/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], reverse("admin:index"))

    def test_section_builder_produces_unique_models(self):
        request = self.factory.get("/admin/")
        request.user = self.user

        sections = grms_admin_site._build_sections(request)
        models_seen = []
        for section in sections:
            for model in section["models"]:
                models_seen.append(model["object_name"])

        self.assertEqual(len(models_seen), len(set(models_seen)))

    def test_section_builder_appends_other_models_when_unassigned(self):
        request = self.factory.get("/admin/")
        request.user = self.user

        original_definitions = grms_admin_site.SECTION_DEFINITIONS
        custom_definitions = (
            {"title": "Only roads", "models": ("Roads",)},
        )
        grms_admin_site.SECTION_DEFINITIONS = custom_definitions
        self.addCleanup(setattr, grms_admin_site, "SECTION_DEFINITIONS", original_definitions)

        sections = grms_admin_site._build_sections(request)

        self.assertTrue(any(section["title"] == "Other models" for section in sections))
        other_section = next(section for section in sections if section["title"] == "Other models")
        self.assertTrue(any(model["object_name"] == "RoadSection" for model in other_section["models"]))
