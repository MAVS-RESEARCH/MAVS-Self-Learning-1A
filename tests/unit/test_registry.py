import pytest

from mavs10d.core.config import MethodConfig
from mavs10d.core.registry import ComponentRegistry, RiskThresholdMethod


def test_registry_exposes_all_workplan_categories() -> None:
    registry = ComponentRegistry()

    registry.register_baseline(
        "baseline_smoke",
        lambda config: RiskThresholdMethod(config),
    )
    registry.register_corruption_schedule(
        "schedule_smoke",
        lambda params: {"category": "schedule", **params},
    )
    registry.register_specialist(
        "specialist_smoke",
        lambda params: {"category": "specialist", **params},
    )
    registry.register_metric(
        "metric_smoke",
        lambda params: {"category": "metric", **params},
    )
    registry.register_report_builder(
        "report_smoke",
        lambda params: {"category": "report_builder", **params},
    )

    assert registry.baseline_types() == ["baseline_smoke"]
    assert registry.corruption_schedule_types() == ["schedule_smoke"]
    assert registry.specialist_types() == ["specialist_smoke"]
    assert registry.metric_types() == ["metric_smoke"]
    assert registry.report_builder_types() == ["report_smoke"]

    baseline = registry.create_baseline(
        MethodConfig(id="baseline", type="baseline_smoke", params={"threshold": 0.4})
    )
    assert baseline.method_id == "baseline"
    assert registry.create_corruption_schedule("schedule_smoke", {"seed": 1}) == {
        "category": "schedule",
        "seed": 1,
    }
    assert registry.create_specialist("specialist_smoke", {"name": "a"}) == {
        "category": "specialist",
        "name": "a",
    }
    assert registry.create_metric("metric_smoke", {"name": "uar"}) == {
        "category": "metric",
        "name": "uar",
    }
    assert registry.create_report_builder("report_smoke", {"name": "tables"}) == {
        "category": "report_builder",
        "name": "tables",
    }


def test_registry_rejects_duplicate_category_entries() -> None:
    registry = ComponentRegistry()
    registry.register_metric("metric_smoke", lambda params: params)

    with pytest.raises(ValueError, match="Metric already registered"):
        registry.register_metric("metric_smoke", lambda params: params)


def test_registry_unknown_category_errors_are_explicit() -> None:
    registry = ComponentRegistry()

    with pytest.raises(KeyError, match="Unknown corruption schedule type"):
        registry.create_corruption_schedule("missing")

    with pytest.raises(KeyError, match="Unknown specialist type"):
        registry.create_specialist("missing")

    with pytest.raises(KeyError, match="Unknown metric type"):
        registry.create_metric("missing")

    with pytest.raises(KeyError, match="Unknown report builder type"):
        registry.create_report_builder("missing")
