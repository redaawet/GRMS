from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from grms.admin import grms_admin_site
from grms.menu import GROUP_ORDER


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
        self.assertIn("admin/index.html", rendered_templates)

        sections = response.context["sections"]
        self.assertTrue(sections)
        self.assertTrue(any(section["title"] == "Road Network" for section in sections))
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

        original_groups = grms_admin_site._get_menu_groups
        grms_admin_site._get_menu_groups = lambda: {"Only roads": (("Road", "Roads"),)}
        self.addCleanup(setattr, grms_admin_site, "_get_menu_groups", original_groups)

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

    def test_menu_groups_respect_expected_titles(self):
        menu_groups = grms_admin_site._get_menu_groups()
        self.assertTrue(menu_groups)
        for title in menu_groups.keys():
            self.assertIn(title, GROUP_ORDER)

    def test_registered_models_appear_once_in_menu_groups(self):
        menu_groups = grms_admin_site._get_menu_groups()
        menu_models = {
            model_name
            for models in menu_groups.values()
            for model_name, _ in models
        }

        registered_models = {model._meta.object_name for model in grms_admin_site._registry}
        self.assertTrue(registered_models.issubset(menu_models))

    def test_menu_group_labels_are_normalised(self):
        menu_groups = grms_admin_site._get_menu_groups()

        def find_entry(target_name):
            for group_title, models in menu_groups.items():
                for model_name, label in models:
                    if model_name == target_name:
                        return group_title, label
            return None, None

        distress_group, distress_label = find_entry("RoadConditionDetailedSurvey")
        self.assertEqual(distress_group, "Distress")
        self.assertEqual(distress_label, "Road distress")

        traffic_group, traffic_label = find_entry("TrafficForPrioritization")
        self.assertEqual(traffic_group, "Traffic")
        self.assertEqual(traffic_label, "Traffic priority")

        planning_group, planning_label = find_entry("BenefitCriterion")
        self.assertEqual(planning_group, "Maintenance & Planning")
        self.assertEqual(planning_label, "Benefit criteria")

    def test_condition_menu_includes_three_condition_surveys(self):
        request = self.factory.get("/admin/")
        request.user = self.user

        sections = grms_admin_site._build_sections(request)
        condition_section = next(
            section for section in sections if section["title"] == "Condition"
        )
        condition_models = {model["object_name"] for model in condition_section["models"]}

        self.assertEqual(
            condition_models,
            {
                "RoadConditionSurvey",
                "StructureConditionSurvey",
                "FurnitureConditionSurvey",
            },
        )
