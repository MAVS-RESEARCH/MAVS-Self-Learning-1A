from mavs10d.governance.severity import aggregate_severity


def test_severity_is_monotone_in_diagnostic_flags() -> None:
    low = aggregate_severity(
        {
            "disagreement": 0.10,
            "evidence_missingness": 0.0,
            "policy_conflict": 0.10,
            "corruption_signal": 0.10,
            "provenance_concentration": 0.10,
            "shared_source_suspicion": 0.0,
            "confidence_inflation": 0.0,
            "specialist_collapse_indicator": 0.0,
        }
    )
    high = aggregate_severity(
        {
            "disagreement": 0.10,
            "evidence_missingness": 1.0,
            "policy_conflict": 0.90,
            "corruption_signal": 0.70,
            "provenance_concentration": 0.90,
            "shared_source_suspicion": 1.0,
            "confidence_inflation": 0.40,
            "specialist_collapse_indicator": 1.0,
        }
    )

    assert high.normalized_severity >= low.normalized_severity
    assert high.raw_severity >= low.raw_severity

