from django.db import migrations, models


def populate_sequences(apps, schema_editor):
    RoadSection = apps.get_model("grms", "RoadSection")
    RoadSegment = apps.get_model("grms", "RoadSegment")

    sections_to_update = []
    for road_id in (
        RoadSection.objects.values_list("road_id", flat=True).distinct()
    ):
        ordered_sections = list(
            RoadSection.objects.filter(road_id=road_id).order_by("sequence_on_road", "id")
        )
        for idx, section in enumerate(ordered_sections, start=1):
            if not section.sequence_on_road:
                section.sequence_on_road = idx
            if not section.section_number:
                section.section_number = section.sequence_on_road
            sections_to_update.append(section)
    if sections_to_update:
        RoadSection.objects.bulk_update(sections_to_update, ["sequence_on_road", "section_number"])

    segments_to_update = []
    for section in RoadSection.objects.all().select_related("road"):
        segments = list(RoadSegment.objects.filter(section=section).order_by("id"))
        for idx, segment in enumerate(segments, start=1):
            segment.sequence_on_section = idx
            segment.segment_identifier = (
                f"{section.road.road_identifier}-S{section.sequence_on_road}-Sg{idx}"
            )
            segments_to_update.append(segment)
    if segments_to_update:
        RoadSegment.objects.bulk_update(
            segments_to_update, ["sequence_on_section", "segment_identifier"]
        )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("grms", "0047_intervention_needs"),
    ]

    operations = [
        migrations.AlterField(
            model_name="road",
            name="admin_woreda",
            field=models.ForeignKey(
                blank=True,
                help_text="Administrative Woreda (optional)",
                null=True,
                on_delete=models.deletion.PROTECT,
                related_name="roads",
                to="grms.adminworeda",
            ),
        ),
        migrations.RemoveField(
            model_name="road",
            name="link_type",
        ),
        migrations.AlterField(
            model_name="roadsection",
            name="section_number",
            field=models.PositiveIntegerField(
                editable=False, help_text="Section identifier within the road"
            ),
        ),
        migrations.AlterField(
            model_name="roadsection",
            name="sequence_on_road",
            field=models.PositiveIntegerField(
                default=0,
                editable=False,
                help_text="Ordered position of this section along the parent road",
            ),
        ),
        migrations.AddField(
            model_name="roadsegment",
            name="segment_identifier",
            field=models.CharField(
                blank=True,
                editable=False,
                help_text="Stable SRAD-compliant segment identifier",
                max_length=100,
            ),
        ),
        migrations.AddField(
            model_name="roadsegment",
            name="sequence_on_section",
            field=models.PositiveIntegerField(
                default=0,
                editable=False,
                help_text="Ordered position of this segment within the parent section",
            ),
        ),
        migrations.RunPython(populate_sequences, noop),
        migrations.AlterUniqueTogether(
            name="roadsegment",
            unique_together={("section", "sequence_on_section")},
        ),
    ]
