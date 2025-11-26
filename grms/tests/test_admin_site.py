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

    def test_site_url_points_to_front_end_root(self):
        self.assertEqual(grms_admin_site.site_url, "/")

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

    def test_section_builder_includes_models_with_duplicate_names_across_apps(self):
        request = self.factory.get("/admin/")
        request.user = self.user

        original_get_app_list = grms_admin_site.get_app_list

        def fake_app_list(_request):
            return [
                {
                    "app_label": "app_one",
                    "models": [
                        {
                            "object_name": "SharedModel",
                            "name": "SharedModel",
                            "admin_url": "/admin/app_one/sharedmodel/",
                            "add_url": "/admin/app_one/sharedmodel/add/",
                            "view_only": False,
                        }
                    ],
                },
                {
                    "app_label": "app_two",
                    "models": [
                        {
                            "object_name": "SharedModel",
                            "name": "SharedModel",
                            "admin_url": "/admin/app_two/sharedmodel/",
                            "add_url": "/admin/app_two/sharedmodel/add/",
                            "view_only": False,
                        }
                    ],
                },
            ]

        grms_admin_site.get_app_list = fake_app_list
        self.addCleanup(setattr, grms_admin_site, "get_app_list", original_get_app_list)

        sections = grms_admin_site._build_sections(request)

        self.assertEqual(len(sections), 1)
        self.assertEqual(len(sections[0]["models"]), 2)
        identifiers = {(model.get("app_label"), model["object_name"]) for model in sections[0]["models"]}
        self.assertEqual(
            identifiers,
            {("app_one", "SharedModel"), ("app_two", "SharedModel")},
        )
