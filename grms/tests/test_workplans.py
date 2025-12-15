from decimal import Decimal

import pytest

from grms import models
from grms.services.planning.workplans import (
    BUCKET_FIELDS,
    compute_annual_workplan_rows,
    compute_section_workplan_rows,
)
from grms.services.workplan_costs import compute_global_costs_by_road


@pytest.mark.django_db
def test_segment_and_structure_needs_bucketed_correctly():
    road = models.Road.objects.create(
        road_identifier="RTR-1",
        road_name_from="A",
        road_name_to="B",
        design_standard="DC1",
        admin_zone=models.AdminZone.objects.create(name="Zone", region="Region"),
        total_length_km=Decimal("10"),
        surface_type="Earth",
        managing_authority="Federal",
        geometry=[[0, 0], [1, 0]],
    )
    socio = models.RoadLinkTypeLookup.objects.create(name="Link", code="L1", score=1)
    models.RoadSocioEconomic.objects.create(road=road, population_served=1000, road_link_type=socio)
    # Skip strict validation for test data
    models.RoadSection.full_clean = lambda self, *args, **kwargs: None  # type: ignore
    section = models.RoadSection.objects.create(
        road=road,
        start_chainage_km=Decimal("0"),
        end_chainage_km=Decimal("1"),
        length_km=Decimal("1"),
        surface_type="Earth",
    )
    segment = models.RoadSegment.objects.create(
        section=section,
        station_from_km=Decimal("0"),
        station_to_km=Decimal("1"),
        cross_section="Cutting",
        terrain_transverse="Flat",
        terrain_longitudinal="Flat",
    )

    # Work items
    rm_item = models.InterventionWorkItem.objects.create(
        category=models.InterventionCategory.objects.create(name="Cat"),
        work_code="01",
        description="RM",
        unit="km",
        unit_cost=Decimal("100"),
    )
    pm_item = models.InterventionWorkItem.objects.create(
        category=rm_item.category,
        work_code="02",
        description="PM",
        unit="km",
        unit_cost=Decimal("200"),
    )
    rehab_item = models.InterventionWorkItem.objects.create(
        category=rm_item.category,
        work_code="05",
        description="Rehab",
        unit="km",
        unit_cost=Decimal("300"),
    )
    road_bneck_item = models.InterventionWorkItem.objects.create(
        category=rm_item.category,
        work_code="101",
        description="Road bottleneck",
        unit="km",
        unit_cost=Decimal("400"),
    )
    struct_item = models.InterventionWorkItem.objects.create(
        category=rm_item.category,
        work_code="103",
        description="Structure bottleneck",
        unit="m",
        unit_cost=Decimal("500"),
    )

    need = models.SegmentInterventionNeed.objects.create(segment=segment, fiscal_year=2025)
    models.SegmentInterventionNeedItem.objects.create(need=need, intervention_item=rm_item)
    models.SegmentInterventionNeedItem.objects.create(need=need, intervention_item=pm_item)
    models.SegmentInterventionNeedItem.objects.create(need=need, intervention_item=rehab_item)
    models.SegmentInterventionNeedItem.objects.create(need=need, intervention_item=road_bneck_item)
    models.SegmentInterventionRecommendation.objects.create(
        segment=segment, mci_value=Decimal("0"), recommended_item=rm_item
    )
    models.SegmentInterventionRecommendation.objects.create(
        segment=segment, mci_value=Decimal("0"), recommended_item=pm_item
    )
    models.SegmentInterventionRecommendation.objects.create(
        segment=segment, mci_value=Decimal("0"), recommended_item=rehab_item
    )
    models.SegmentInterventionRecommendation.objects.create(
        segment=segment, mci_value=Decimal("0"), recommended_item=road_bneck_item
    )

    models.StructureInventory.full_clean = lambda self, *args, **kwargs: None  # type: ignore
    structure = models.StructureInventory.objects.create(
        road=road,
        section=section,
        geometry_type=models.StructureInventory.POINT,
        structure_category="Bridge",
        station_km=Decimal("0"),
    )
    sneed = models.StructureInterventionNeed.objects.create(structure=structure, fiscal_year=2025)
    models.StructureInterventionNeedItem.objects.create(need=sneed, intervention_item=struct_item)
    models.StructureInterventionRecommendation.objects.create(
        structure=structure,
        structure_type=models.StructureConditionInterventionRule.StructureType.BRIDGE,
        condition_code=1,
        recommended_item=struct_item,
    )

    models.RoadRankingResult.objects.create(
        road=road,
        fiscal_year=2025,
        road_class_or_surface_group="unpaved",
        population_served=Decimal("1"),
        benefit_factor=Decimal("1"),
        cost_of_improvement=Decimal("1"),
        road_index=Decimal("10"),
        rank=1,
    )

    rows, totals, header_context = compute_section_workplan_rows(road, 2025)

    assert len(rows) == 1
    row = rows[0]
    assert row.rm_cost == Decimal("100")  # 1 km * 100
    assert row.pm_cost == Decimal("200")
    assert row.rehab_cost == Decimal("300")
    assert row.road_bneck_cost == Decimal("400")
    assert row.structure_bneck_cost == Decimal("500")
    assert row.year_cost == sum(getattr(row, field) for field in BUCKET_FIELDS)
    assert totals["year_cost"] == row.year_cost
    assert header_context["rank_no"] == 1

    annual_rows, annual_totals, _ = compute_annual_workplan_rows(2025)
    assert len(annual_rows) == 1
    annual_row = annual_rows[0]
    assert annual_row["rm_cost"] == row.rm_cost
    assert annual_row["pm_cost"] == row.pm_cost
    assert annual_row["rehab_cost"] == row.rehab_cost
    assert annual_row["road_bneck_cost"] == row.road_bneck_cost
    assert annual_row["structure_bneck_cost"] == row.structure_bneck_cost
    assert annual_row["year_cost"] == totals["year_cost"]
    assert annual_totals["year_cost"] == annual_row["year_cost"]
    assert annual_row["rank"] == 1

    global_rows, _, = compute_global_costs_by_road()
    cost_row = next(entry for entry in global_rows if entry["road"] == road)
    assert annual_row["rm_cost"] == cost_row["rm_cost"]
    assert annual_row["pm_cost"] == cost_row["pm_cost"]
    assert annual_row["rehab_cost"] == cost_row["rehab_cost"]
    assert annual_row["road_bneck_cost"] == cost_row["road_bneck_cost"]
    assert annual_row["structure_bneck_cost"] == cost_row["structure_bneck_cost"]
    assert annual_row["year_cost"] == cost_row["total_cost"]


@pytest.mark.django_db
def test_section_interventions_used_for_costs():
    road = models.Road.objects.create(
        road_identifier="RTR-2",
        road_name_from="A",
        road_name_to="B",
        design_standard="DC1",
        admin_zone=models.AdminZone.objects.create(name="Zone2", region="Region2"),
        total_length_km=Decimal("5"),
        surface_type="Gravel",
        managing_authority="Federal",
        geometry=[[0, 0], [1, 0]],
    )
    models.RoadRankingResult.objects.create(
        road=road,
        fiscal_year=2026,
        road_class_or_surface_group="paved",
        population_served=Decimal("1"),
        benefit_factor=Decimal("1"),
        cost_of_improvement=Decimal("1"),
        road_index=Decimal("10"),
        rank=1,
    )
    models.RoadSection.full_clean = lambda self, *args, **kwargs: None  # type: ignore
    section = models.RoadSection.objects.create(
        road=road,
        start_chainage_km=Decimal("0"),
        end_chainage_km=Decimal("1"),
        length_km=Decimal("1"),
        surface_type="Gravel",
    )
    intervention_lookup = models.InterventionLookup.objects.create(
        intervention_code="RM01",
        name="Routine",
        category="Road",
        unit_measure="km",
        default_unit_cost=Decimal("100"),
        effective_date="2020-01-01",
    )
    models.RoadSectionIntervention.objects.create(
        section=section,
        intervention=intervention_lookup,
        scope="Full Section",
        start_chainage_km=Decimal("0"),
        end_chainage_km=Decimal("1"),
        length_km=Decimal("1"),
        estimated_cost=Decimal("123.45"),
        intervention_year=2026,
    )

    rows, totals, _ = compute_section_workplan_rows(road, 2026)
    assert len(rows) == 1
    assert totals["rm_cost"] == Decimal("123.45")
    annual_rows, annual_totals, _ = compute_annual_workplan_rows(2026)
    assert len(annual_rows) == 1
    assert annual_rows[0]["rm_cost"] == Decimal("123.45")
    assert annual_totals["rm_cost"] == Decimal("123.45")


@pytest.mark.django_db
def test_budget_cap_applies_partial_last_road():
    zone = models.AdminZone.objects.create(name="Zone3", region="Region3")
    roads = []
    for idx, cost in enumerate((Decimal("100"), Decimal("80"), Decimal("60")), start=1):
        road = models.Road.objects.create(
            road_identifier=f"RTR-{idx}",
            road_name_from="A",
            road_name_to="B",
            design_standard="DC1",
            admin_zone=zone,
            total_length_km=Decimal("1"),
            surface_type="Earth",
            managing_authority="Federal",
            geometry=[[0, 0], [1, 0]],
        )
        models.RoadSection.full_clean = lambda self, *args, **kwargs: None  # type: ignore
        section = models.RoadSection.objects.create(
            road=road,
            start_chainage_km=Decimal("0"),
            end_chainage_km=Decimal("1"),
            length_km=Decimal("1"),
            surface_type="Earth",
        )
        intervention_lookup = models.InterventionLookup.objects.create(
            intervention_code="RM0%s" % idx,
            name="Routine",
            category="Road",
            unit_measure="km",
            default_unit_cost=Decimal("100"),
            effective_date="2020-01-01",
        )
        models.RoadSectionIntervention.objects.create(
            section=section,
            intervention=intervention_lookup,
            scope="Full Section",
            estimated_cost=cost,
            intervention_year=2027,
        )
        models.RoadRankingResult.objects.create(
            road=road,
            fiscal_year=2027,
            road_class_or_surface_group="unpaved",
            population_served=Decimal("1"),
            benefit_factor=Decimal("1"),
            cost_of_improvement=Decimal("1"),
            road_index=Decimal("10"),
            rank=idx,
        )
        roads.append(road)

    rows, totals, _ = compute_annual_workplan_rows(
        2027, budget_cap_birr=Decimal("190"), include_partial_last_road=True
    )

    assert len(rows) == 3
    assert rows[-1]["funding_status"] == "PARTIAL"
    assert rows[-1]["funded_amount"] == Decimal("10.00")
    assert rows[-1]["funded_percent"] == Decimal("16.67")
    assert totals["rm_cost"] == Decimal("190.00")
