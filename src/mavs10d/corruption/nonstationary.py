"""Deterministic Phase 1 schedules for bounded non-stationary evaluation."""

from __future__ import annotations

import math
from dataclasses import dataclass


SCHEDULE_FAMILIES: tuple[str, ...] = (
    "piecewise_hidden",
    "gradual_random_walk",
    "burst",
    "recurring_regime",
    "adversarial_response",
    "compositional",
    "recovery_trap",
)


@dataclass(frozen=True)
class ScheduleState:
    family: str
    shift_class: str
    regime_id: str
    prior_shift: float
    covariate_shift: float
    boundary_shift: float
    corruption_level: float
    recovery_active: bool
    change_active: bool


def schedule_state(family: str, shift_class: str, step: int, phase: float) -> ScheduleState:
    """Return bounded latent dynamics without consulting method behavior or feedback."""
    if family not in SCHEDULE_FAMILIES:
        raise ValueError(f"Unsupported Phase 1 schedule family: {family}")
    if not 0 <= step < 100:
        raise ValueError("Phase 1 schedule step must be in [0, 99].")
    amplitude = min(0.55, max(0.10, float(phase)))
    prior = covariate = boundary = corruption = 0.0
    recovery = False
    regime = "base"
    if family == "piecewise_hidden":
        active = 30 <= step < 70
        prior = amplitude if active else 0.0
        boundary = 0.6 * amplitude if active else 0.0
        regime = "hidden_shift" if active else ("recovery" if step >= 70 else "base")
        recovery = step >= 70
    elif family == "gradual_random_walk":
        progress = step / 99.0
        covariate = amplitude * (2.0 * progress - 1.0)
        prior = amplitude * math.sin(progress * math.pi) * 0.5
        regime = "gradual"
    elif family == "burst":
        active = (20 <= step < 30) or (58 <= step < 70)
        corruption = amplitude if active else 0.0
        prior = 0.4 * amplitude if active else 0.0
        regime = "burst" if active else "clean"
        recovery = (30 <= step < 40) or step >= 70
    elif family == "recurring_regime":
        active = (step // 20) % 2 == 1
        prior = amplitude if active else -0.25 * amplitude
        boundary = 0.5 * amplitude if active else 0.0
        regime = "recurring_high" if active else "recurring_low"
        recovery = not active and step > 20
    elif family == "adversarial_response":
        active = 35 <= step < 75
        covariate = amplitude * (0.6 + 0.4 * math.sin(step * 0.37)) if active else 0.0
        corruption = 0.7 * amplitude if active else 0.0
        regime = "bounded_response" if active else "clean"
        recovery = step >= 75
    elif family == "compositional":
        gradual = amplitude * step / 99.0
        active = 45 <= step < 68
        covariate = gradual
        boundary = 0.4 * amplitude if active else 0.0
        corruption = 0.5 * amplitude if active else 0.0
        regime = "composition" if active else "gradual_component"
        recovery = step >= 68
    else:  # recovery_trap
        active = 25 <= step < 65
        prior = amplitude if active else (0.12 if step >= 65 else 0.0)
        boundary = 0.5 * amplitude if active else 0.0
        regime = "corruption" if active else ("recovery_trap" if step >= 65 else "base")
        recovery = step >= 65
    change_active = any(abs(value) > 1e-12 for value in (prior, covariate, boundary, corruption))
    return ScheduleState(
        family=family,
        shift_class=shift_class,
        regime_id=regime,
        prior_shift=prior,
        covariate_shift=covariate,
        boundary_shift=boundary,
        corruption_level=corruption,
        recovery_active=recovery,
        change_active=change_active,
    )
