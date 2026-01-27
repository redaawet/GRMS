from decimal import Decimal
from pathlib import Path

import pytest
from django.core.management import call_command
from django.contrib.gis.geos import LineString

from grms.models import AdminZone, AdminWoreda, Road, RoadNameAlias, RoadSection, RoadSegment, StructureInventory
from traffic.models import TrafficSurveyOverall, TrafficSurveySummary


@pytest.mark.django_db
def test_import_inventory_command_is_idempotent():
    fixtures_dir = Path(__file__).resolve().parent / "fixtures" / "import_inventory"

    zone = AdminZone.objects.create(name="Zone 1")
    woreda = AdminWoreda.objects.create(name="Woreda 1", zone=zone)
    road = Road.objects.create(
        road_identifier="RTR-1",
        road_name_from="Alpha",
        road_name_to="Beta",
        design_standard="DC2",
        admin_zone=zone,
        admin_woreda=woreda,
        total_length_km=Decimal("1.0"),
        surface_type="Gravel",
        managing_authority="Regional",
        geometry=LineString((0, 0), (0, 0.01)),
    )
    RoadSection.objects.create(
        road=road,
        start_chainage_km=Decimal("0.0"),
        end_chainage_km=Decimal("1.0"),
        surface_type="Gravel",
        surface_thickness_cm=Decimal("20.0"),
    )

    call_command(
        "import_inventory",
        traffic=fixtures_dir / "traffic.csv",
        cross_section=fixtures_dir / "cross_section.csv",
        structures=fixtures_dir / "structures.csv",
    )

    assert RoadNameAlias.objects.count() == 1
    assert TrafficSurveyOverall.objects.count() == 1
    assert TrafficSurveySummary.objects.count() == 8
    assert RoadSegment.objects.count() == 1
    assert StructureInventory.objects.count() == 1

    call_command(
        "import_inventory",
        traffic=fixtures_dir / "traffic.csv",
        cross_section=fixtures_dir / "cross_section.csv",
        structures=fixtures_dir / "structures.csv",
    )

    assert RoadNameAlias.objects.count() == 1
    assert TrafficSurveyOverall.objects.count() == 1
    assert TrafficSurveySummary.objects.count() == 8
    assert RoadSegment.objects.count() == 1
    assert StructureInventory.objects.count() == 1
