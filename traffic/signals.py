from django.core.management import call_command
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import (
    TrafficCountRecord,
    TrafficQC,
    TrafficSurvey,
    TrafficSurveySummary,
    recompute_cycle_summaries_for_survey,
    recompute_survey_summary_for_survey,
    run_auto_qc_for_survey,
)


@receiver(post_save, sender=TrafficCountRecord)
def _recompute_on_count_save(sender, instance: TrafficCountRecord, **kwargs):
    survey = instance.traffic_survey
    if not survey:
        return
    run_auto_qc_for_survey(survey)
    recompute_cycle_summaries_for_survey(survey)
    recompute_survey_summary_for_survey(survey)


@receiver(post_save, sender=TrafficSurvey)
def _recompute_on_survey_approval(sender, instance: TrafficSurvey, **kwargs):
    if instance.qa_status != "Approved":
        return
    run_auto_qc_for_survey(instance)
    recompute_cycle_summaries_for_survey(instance)
    recompute_survey_summary_for_survey(instance)


@receiver(post_save, sender=TrafficSurveySummary)
def recompute_overall(sender, instance: TrafficSurveySummary, **kwargs):  # pragma: no cover - signal side effect
    call_command("compute_traffic_overall")
