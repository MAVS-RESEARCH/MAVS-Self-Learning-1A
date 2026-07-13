from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from mavs10d.core.trace_logging import console_log


@dataclass(frozen=True)
class CorruptionPhase:
    name: str
    start: int
    end: int
    transforms: list[dict[str, Any]]
    corruption_level: float

    def contains(self, t: int) -> bool:
        return self.start <= t <= self.end

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "start": self.start,
            "end": self.end,
            "transforms": self.transforms,
            "corruption_level": self.corruption_level,
        }


@dataclass(frozen=True)
class PiecewiseCorruptionSchedule:
    schedule_id: str
    phases: tuple[CorruptionPhase, ...]

    def phase_at(self, t: int) -> CorruptionPhase:
        # console.log: phase2.schedule.phase_at.start
        console_log("phase2.schedule.phase_at.start", schedule_id=self.schedule_id, t=t)
        for phase in self.phases:
            if phase.contains(t):
                # console.log: phase2.schedule.phase_at.selected
                console_log(
                    "phase2.schedule.phase_at.selected",
                    schedule_id=self.schedule_id,
                    t=t,
                    phase=phase.name,
                )
                return phase
        if t < self.phases[0].start:
            return self.phases[0]
        return self.phases[-1]

    def phase_names(self) -> list[str]:
        return [phase.name for phase in self.phases]


def build_schedule_from_config(config: dict[str, Any]) -> PiecewiseCorruptionSchedule:
    schedule_type = str(config.get("type", "piecewise"))
    # console.log: phase2.schedule.build.start
    console_log("phase2.schedule.build.start", schedule_type=schedule_type)
    if schedule_type == "sweep":
        schedule = build_sweep_schedule(config)
    elif schedule_type == "piecewise":
        phases = tuple(_phase_from_mapping(item) for item in config.get("phases", []))
        if not phases:
            phases = default_phase_tuple(int(config.get("episode_steps", 20)))
        schedule = PiecewiseCorruptionSchedule(
            schedule_id=str(config.get("id", "piecewise_default")),
            phases=phases,
        )
    else:
        raise ValueError(f"Unsupported corruption schedule type: {schedule_type}")
    # console.log: phase2.schedule.build.complete
    console_log(
        "phase2.schedule.build.complete",
        schedule_id=schedule.schedule_id,
        phases=schedule.phase_names(),
    )
    return schedule


def default_phase_tuple(episode_steps: int) -> tuple[CorruptionPhase, ...]:
    width = max(1, episode_steps // 5)
    specs = [
        ("clean_start", 0.00, []),
        ("mild_noise", 0.15, [{"type": "ambiguity_injection", "p": 0.40}]),
        (
            "adversarial_burst",
            0.45,
            [
                {"type": "prompt_injection", "p": 0.55},
                {"type": "evidence_masking", "p": 0.35},
            ],
        ),
        (
            "correlated_failure",
            0.65,
            [{"type": "shared_wrong_premise", "p": 1.0, "severity": "placeholder"}],
        ),
        ("recovery", 0.10, [{"type": "residual_drift", "strength": 0.10}]),
    ]
    phases: list[CorruptionPhase] = []
    start = 0
    for index, (name, level, transforms) in enumerate(specs):
        end = episode_steps - 1 if index == len(specs) - 1 else start + width - 1
        phases.append(
            CorruptionPhase(
                name=name,
                start=start,
                end=end,
                transforms=list(transforms),
                corruption_level=level,
            )
        )
        start = end + 1
    return tuple(phases)


def holdout_schedule_names() -> tuple[str, str]:
    return (
        "adversarial_burst_plus_recovery_holdout",
        "correlated_late_collapse_holdout",
    )


def corruption_sweep_levels(
    start: float = 0.05, stop: float = 0.60, step: float = 0.05
) -> list[float]:
    values: list[float] = []
    current = start
    while current <= stop + 1e-9:
        values.append(round(current, 2))
        current += step
    return values


def build_sweep_schedule(config: dict[str, Any]) -> PiecewiseCorruptionSchedule:
    start = float(config.get("start", 0.05))
    stop = float(config.get("stop", 0.60))
    step = float(config.get("step", 0.05))
    steps_per_level = int(config.get("steps_per_level", 2))
    transforms = list(config.get("transforms", [{"type": "residual_drift"}]))
    phases: list[CorruptionPhase] = []
    for index, level in enumerate(corruption_sweep_levels(start, stop, step)):
        phase_transforms = [
            {**transform, "strength": transform.get("strength", level)}
            for transform in transforms
        ]
        phases.append(
            CorruptionPhase(
                name=f"sweep_{level:.2f}".replace(".", "_"),
                start=index * steps_per_level,
                end=(index + 1) * steps_per_level - 1,
                transforms=phase_transforms,
                corruption_level=level,
            )
        )
    return PiecewiseCorruptionSchedule(
        schedule_id=str(config.get("id", "stress_schedule_sweep")),
        phases=tuple(phases),
    )


def _phase_from_mapping(data: dict[str, Any]) -> CorruptionPhase:
    steps = list(data["steps"])
    if len(steps) != 2:
        raise ValueError("Phase steps must contain [start, end].")
    return CorruptionPhase(
        name=str(data["name"]),
        start=int(steps[0]),
        end=int(steps[1]),
        transforms=list(data.get("transforms", [])),
        corruption_level=float(data.get("corruption_level", 0.0)),
    )

