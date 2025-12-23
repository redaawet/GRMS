from traffic.models import TrafficQC


def test_traffic_dataset_fixture_runs_qc(traffic_test_dataset):
    survey = traffic_test_dataset["survey"]
    counts = traffic_test_dataset["counts"]

    assert survey.road == traffic_test_dataset["road"]
    assert len(counts) == survey.count_records.count()

    issues = TrafficQC.objects.filter(traffic_survey=survey)
    assert issues.exists(), "Auto-QC should create at least one gating issue (e.g., missing cycles)."
    assert all(issue.traffic_survey_id == survey.pk for issue in issues)
