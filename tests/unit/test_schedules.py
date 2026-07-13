from mavs10d.corruption.schedules import (
    build_schedule_from_config,
    corruption_sweep_levels,
    holdout_schedule_names,
)


def test_piecewise_schedule_phase_boundaries_are_exact() -> None:
    schedule = build_schedule_from_config(
        {
            "type": "piecewise",
            "id": "boundary_test",
            "phases": [
                {"name": "clean_start", "steps": [0, 1], "corruption_level": 0.0},
                {"name": "mild_noise", "steps": [2, 3], "corruption_level": 0.15},
                {
                    "name": "adversarial_burst",
                    "steps": [4, 5],
                    "corruption_level": 0.45,
                },
                {
                    "name": "correlated_failure",
                    "steps": [6, 7],
                    "corruption_level": 0.65,
                },
                {"name": "recovery", "steps": [8, 9], "corruption_level": 0.10},
            ],
        }
    )

    assert schedule.phase_at(0).name == "clean_start"
    assert schedule.phase_at(1).name == "clean_start"
    assert schedule.phase_at(2).name == "mild_noise"
    assert schedule.phase_at(4).name == "adversarial_burst"
    assert schedule.phase_at(6).name == "correlated_failure"
    assert schedule.phase_at(8).name == "recovery"
    assert schedule.phase_at(100).name == "recovery"


def test_default_schedule_supports_required_phase_names() -> None:
    schedule = build_schedule_from_config({"type": "piecewise", "episode_steps": 25})

    assert schedule.phase_names() == [
        "clean_start",
        "mild_noise",
        "adversarial_burst",
        "correlated_failure",
        "recovery",
    ]


def test_sweep_schedule_covers_005_to_060() -> None:
    levels = corruption_sweep_levels(start=0.05, stop=0.60, step=0.05)
    schedule = build_schedule_from_config(
        {
            "type": "sweep",
            "start": 0.05,
            "stop": 0.60,
            "step": 0.05,
            "steps_per_level": 2,
        }
    )

    assert levels[0] == 0.05
    assert levels[-1] == 0.60
    assert len(levels) == 12
    assert schedule.phase_at(0).corruption_level == 0.05
    assert schedule.phase_at(23).corruption_level == 0.60


def test_holdout_schedule_names_are_declared() -> None:
    assert holdout_schedule_names() == (
        "adversarial_burst_plus_recovery_holdout",
        "correlated_late_collapse_holdout",
    )

