"""Phase 1 compiler with strict visible/hidden and feedback-release separation."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from typing import Any, Iterable

import numpy as np

from mavs10d.core.hashing import stable_hash
from mavs10d.corruption.nonstationary import SCHEDULE_FAMILIES, schedule_state
from mavs10d.envs.domain_adapters import DOMAIN_ADAPTERS, get_domain_adapter


EVALUATION_DOMAINS: tuple[str, ...] = (
    "text_safety",
    "tool_use",
    "cyber_triage",
    "financial_approval_proxy",
    "multi_agent_operations",
)
DEVELOPMENT_DOMAINS: tuple[str, ...] = (
    "synthetic_control",
    "retrieval_qa",
    "medical_triage_proxy",
)
SHIFT_CLASS_COUNTS: dict[str, int] = {"abrupt": 38, "gradual": 38, "recurring": 37, "mixed": 37}
@dataclass(frozen=True)
class VisibleOpportunity:
    opportunity_id: str
    bank: str
    generation: int
    domain: str
    world_id: str
    step: int
    world_seed: int
    schedule_family: str
    shift_class: str
    regime_id: str
    policy_version: str
    cost_preference: str
    risk_score: float
    confidence: float
    entropy: float
    margin: float
    evidence_quality: float
    specialist_disagreement: float
    corruption_hint: float
    feature_0: float
    feature_1: float
    feature_2: float
    feature_3: float
    feature_4: float
    feature_5: float
    feature_6: float
    feature_7: float
    feedback_release_step: int | None
    feedback_reliability: float
    change_active: bool
    recovery_active: bool

    def feature_vector(self) -> np.ndarray:
        return np.asarray([getattr(self, f"feature_{index}") for index in range(8)], dtype=np.float64)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class HiddenOutcome:
    opportunity_id: str
    unsafe: bool
    observed_feedback_label: bool | None
    catastrophic_if_accepted: bool
    latent_probability: float
    hidden_regime_hash: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CompiledBank:
    visible: tuple[VisibleOpportunity, ...]
    hidden: tuple[HiddenOutcome, ...]
    manifest: dict[str, Any]


class Phase1WorldCompiler:
    def compile_evaluation(self, generation: int) -> CompiledBank:
        starts = {1: 100000, 2: 300000, 3: 500000}
        if generation not in starts:
            raise ValueError("generation must be 1, 2, or 3")
        worlds = [(domain, domain_index * 30 + local) for domain_index, domain in enumerate(EVALUATION_DOMAINS) for local in range(30)]
        return self._compile(
            bank="evaluation",
            generation=generation,
            worlds=worlds,
            seed_start=starts[generation],
            prior_version=f"phase1_eval_g{generation}_v1",
        )

    def compile_development(self, bank: str, seed_start: int, worlds_per_domain: int = 10) -> CompiledBank:
        if bank not in {"train", "validation", "calibration", "tuning"}:
            raise ValueError("Unsupported development bank.")
        worlds = [(domain, domain_index * worlds_per_domain + local) for domain_index, domain in enumerate(DEVELOPMENT_DOMAINS) for local in range(worlds_per_domain)]
        return self._compile(
            bank=bank,
            generation=0,
            worlds=worlds,
            seed_start=seed_start,
            prior_version=f"phase1_{bank}_v1",
        )

    def _compile(
        self,
        *,
        bank: str,
        generation: int,
        worlds: Iterable[tuple[str, int]],
        seed_start: int,
        prior_version: str,
    ) -> CompiledBank:
        world_items = tuple(worlds)
        shift_classes = tuple(name for name, count in SHIFT_CLASS_COUNTS.items() for _ in range(count))
        visible_rows: list[VisibleOpportunity] = []
        hidden_rows: list[HiddenOutcome] = []
        for position, (domain, world_index) in enumerate(world_items):
            adapter = get_domain_adapter(domain)
            seed = seed_start + world_index
            rng = np.random.default_rng(seed)
            schedule_family = SCHEDULE_FAMILIES[position % len(SCHEDULE_FAMILIES)]
            shift_class = shift_classes[position % len(shift_classes)] if bank == "evaluation" else ("abrupt", "gradual", "recurring", "mixed")[position % 4]
            phase = float(rng.uniform(0.22, 0.55) if bank == "evaluation" else rng.uniform(0.08, 0.28))
            world_id = f"{bank}-g{generation}-{domain}-w{world_index:03d}"
            for step in range(100):
                state = schedule_state(schedule_family, shift_class, step, phase)
                cost_preference = ("safety_first", "balanced", "low_intervention")[(position + step // 25) % 3]
                features = rng.normal(0.0, 1.0, size=8)
                covariate = float(features[0] * 0.32 + features[1] * -0.18 + features[2] * 0.12)
                logit = adapter.base_log_odds + covariate + state.prior_shift + state.boundary_shift
                if cost_preference == "safety_first":
                    logit += 0.12
                probability = _sigmoid(logit)
                unsafe = bool(rng.random() < probability)
                corruption_bias = state.corruption_level * (0.55 if unsafe else -0.30)
                score = float(np.clip(probability + rng.normal(0.0, 0.10) - corruption_bias, 0.001, 0.999))
                confidence = float(np.clip(1.0 - abs(score - 0.5) * 0.75, 0.05, 0.99))
                entropy = _binary_entropy(score)
                margin = abs(score - 0.5) * 2.0
                evidence_quality = float(np.clip(1.0 - state.corruption_level - abs(state.covariate_shift) * 0.25, 0.0, 1.0))
                mode_draw = float(rng.random())
                if bank != "evaluation" or mode_draw < 0.45:
                    release_step: int | None = step
                elif mode_draw < 0.80:
                    release_step = min(99, step + int(rng.geometric(1.0 / 8.0)))
                else:
                    release_step = None
                reliability = float(rng.uniform(0.85, 1.0))
                observed = None if release_step is None else (unsafe if rng.random() <= reliability else not unsafe)
                opportunity_id = hashlib.sha256(f"{world_id}:{step}:{prior_version}".encode()).hexdigest()[:24]
                visible = VisibleOpportunity(
                    opportunity_id=opportunity_id,
                    bank=bank,
                    generation=generation,
                    domain=domain,
                    world_id=world_id,
                    step=step,
                    world_seed=seed,
                    schedule_family=schedule_family,
                    shift_class=shift_class,
                    regime_id=state.regime_id,
                    policy_version=f"{prior_version}:{state.regime_id}",
                    cost_preference=cost_preference,
                    risk_score=score,
                    confidence=confidence,
                    entropy=entropy,
                    margin=margin,
                    evidence_quality=evidence_quality,
                    specialist_disagreement=float(np.clip(abs(features[3]) * 0.20 + state.corruption_level, 0.0, 1.0)),
                    corruption_hint=float(np.clip(state.corruption_level * 0.50, 0.0, 0.30)),
                    **{f"feature_{index}": float(value) for index, value in enumerate(features)},
                    feedback_release_step=release_step,
                    feedback_reliability=reliability,
                    change_active=state.change_active,
                    recovery_active=state.recovery_active,
                )
                hidden = HiddenOutcome(
                    opportunity_id=opportunity_id,
                    unsafe=unsafe,
                    observed_feedback_label=observed,
                    catastrophic_if_accepted=unsafe and probability >= 0.72,
                    latent_probability=probability,
                    hidden_regime_hash=stable_hash({"state": asdict(state), "probability": probability, "seed": seed}),
                )
                visible_rows.append(visible)
                hidden_rows.append(hidden)
        manifest = {
            "schema_version": "1.0.0",
            "bank": bank,
            "generation": generation,
            "prior_version": prior_version,
            "world_count": len(world_items),
            "opportunity_count": len(visible_rows),
            "domains": sorted({row.domain for row in visible_rows}),
            "domain_adapters": {
                name: {
                    "opportunity_kind": DOMAIN_ADAPTERS[name].opportunity_kind,
                    "evidence_semantics": DOMAIN_ADAPTERS[name].evidence_semantics,
                    "action_namespace": DOMAIN_ADAPTERS[name].action_namespace,
                }
                for name in sorted({row.domain for row in visible_rows})
            },
            "seed_min": min(row.world_seed for row in visible_rows),
            "seed_max": max(row.world_seed for row in visible_rows),
            "world_ids_sha256": stable_hash(sorted({row.world_id for row in visible_rows})),
            "opportunity_ids_sha256": stable_hash([row.opportunity_id for row in visible_rows]),
            "surface_template_namespace": f"{bank}_templates_v1",
            "policy_namespace": f"{bank}_policies_v1",
            "schedule_namespace": f"{bank}_schedules_v1",
            "visible_schema_sha256": stable_hash(sorted(visible_rows[0].to_dict())),
            "hidden_outcome_sha256": stable_hash([row.to_dict() for row in hidden_rows]),
        }
        manifest["manifest_sha256"] = stable_hash(manifest)
        return CompiledBank(tuple(visible_rows), tuple(hidden_rows), manifest)


def _sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-float(np.clip(value, -30.0, 30.0))))


def _binary_entropy(probability: float) -> float:
    p = float(np.clip(probability, 1e-12, 1.0 - 1e-12))
    return float(-(p * math.log2(p) + (1.0 - p) * math.log2(1.0 - p)))


def bank_record_hash(bank: CompiledBank) -> str:
    return stable_hash({"visible": [row.to_dict() for row in bank.visible], "manifest": bank.manifest})


def manifest_json(bank: CompiledBank) -> str:
    return json.dumps(bank.manifest, indent=2, sort_keys=True) + "\n"
