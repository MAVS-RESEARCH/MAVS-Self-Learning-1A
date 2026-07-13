"""Phase 3 repair-curriculum compiler with sealed intervention and certification banks."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import yaml

from mavs10d.core.hashing import stable_hash


REPO_ROOT = Path(__file__).resolve().parents[3]
CURRICULUM_ROOT = REPO_ROOT / "configs" / "repair_curricula"
EVALUATION_DOMAINS: tuple[str, ...] = (
    "text_safety",
    "tool_use",
    "cyber_triage",
    "financial_approval_proxy",
    "multi_agent_operations",
)
OPERATION_FEATURES: Mapping[str, str] = {
    "recalibrate": "calibration_corrected_risk",
    "scope_narrow": "scoped_provenance_risk",
    "scope_expand": "homologous_scope_risk",
    "split": "split_correlation_risk",
    "merge": "merged_masking_risk",
    "add": "masked_safe_evidence_risk",
    "retire": "stable_shift_risk",
    "policy_interaction": "policy_interaction_risk",
    "configuration_specialization": "regime_specific_risk",
    "evidence_recovery": "alternate_view_risk",
}
META_SIGNALS: tuple[str, ...] = (
    "calibration_residual",
    "scope_leakage",
    "coverage_gap",
    "witness_conflict",
    "diagnostic_redundancy",
    "evidence_masking",
    "counterfactual_instability",
    "policy_conflict",
    "selector_uncertainty",
    "evidence_unavailable",
)


@dataclass(frozen=True)
class RepairCurriculum:
    curriculum_id: str
    operation: str
    intervention_class: str
    hidden_mechanism: str
    domain: str
    primary_meta_signal: str
    grammar_primitive: str
    protected_family: str
    synthesis_seed: int
    holdout_seed: int
    adversarial_seed: int
    complexity: int

    def __post_init__(self) -> None:
        if self.operation not in OPERATION_FEATURES:
            raise ValueError(f"Unsupported Phase 3 operation: {self.operation}")
        if self.primary_meta_signal not in META_SIGNALS:
            raise ValueError(f"Unsupported meta-diagnostic: {self.primary_meta_signal}")
        if self.domain not in EVALUATION_DOMAINS:
            raise ValueError(f"Unsupported Phase 3 domain: {self.domain}")
        if len({self.synthesis_seed, self.holdout_seed, self.adversarial_seed}) != 3:
            raise ValueError("Curriculum synthesis, holdout, and adversarial seeds must differ.")


@dataclass(frozen=True)
class Phase3VisibleOpportunity:
    opportunity_id: str
    generation: int
    curriculum_id: str
    domain: str
    world_id: str
    world_seed: int
    step: int
    curriculum_step: int
    stage: str
    context_namespace: str
    risk_proxy: float
    confidence: float
    evidence_status: str
    feedback_release_step: int | None
    feedback_reliability: float
    primary_meta_signal: str
    visible_features_json: str
    specialist_outputs_json: str
    nuisance_hash: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Phase3HiddenOutcome:
    opportunity_id: str
    unsafe: bool
    correct_action: str
    target_exposure: bool
    catastrophic_if_accepted: bool
    feedback_poisoned: bool
    hidden_repair_mechanism: str
    expected_operation: str
    protected_family: str
    intervention_class: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CertificationCase:
    case_id: str
    suite: str
    generation: int
    curriculum_id: str
    domain: str
    visible_features: Mapping[str, float | str | bool]
    unsafe: bool
    in_scope: bool
    protected: bool
    nuisance_hash: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CompiledPhase3Generation:
    visible: tuple[Phase3VisibleOpportunity, ...]
    hidden: tuple[Phase3HiddenOutcome, ...]
    certification_cases: tuple[CertificationCase, ...]
    manifest: Mapping[str, Any]


def load_repair_curricula(root: Path = CURRICULUM_ROOT) -> tuple[RepairCurriculum, ...]:
    payloads = [yaml.safe_load(path.read_text(encoding="utf-8")) for path in sorted(root.glob("*.yaml"))]
    curricula = tuple(
        RepairCurriculum(**{key: value for key, value in payload.items() if key != "schema_version"})
        for payload in payloads
    )
    if len(curricula) != 10:
        raise ValueError(f"Phase 3 requires exactly ten curricula, found {len(curricula)}.")
    if len({item.curriculum_id for item in curricula}) != len(curricula):
        raise ValueError("Repair curriculum IDs must be unique.")
    if set(item.operation for item in curricula) != set(OPERATION_FEATURES):
        raise ValueError("Repair curricula must cover every versioned operation exactly once.")
    return curricula


class Phase3WorldCompiler:
    """Compile immutable canonical decisions and evaluator-only repair evidence."""

    def __init__(self, phase_config: Path | None = None, curriculum_root: Path = CURRICULUM_ROOT) -> None:
        config_path = phase_config or REPO_ROOT / "configs" / "phases" / "phase3.yaml"
        self.config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        self.curricula = load_repair_curricula(curriculum_root)

    def compile_generation(self, generation: int) -> CompiledPhase3Generation:
        if generation not in {1, 2, 3}:
            raise ValueError("Phase 3 generation must be 1, 2, or 3.")
        seed_min, seed_max = self.config["generation_world_seed_ranges"][generation]
        visible: list[Phase3VisibleOpportunity] = []
        hidden: list[Phase3HiddenOutcome] = []
        cases: list[CertificationCase] = []
        for curriculum_index, curriculum in enumerate(self.curricula):
            for local_world in range(20):
                world_index = curriculum_index * 20 + local_world
                world_seed = int(seed_min) + world_index
                if world_seed > int(seed_max):
                    raise ValueError("Configured Phase 3 world seed range is too small.")
                rng = np.random.default_rng(world_seed)
                world_id = f"p3-g{generation}-{curriculum.curriculum_id}-w{local_world:02d}"
                for local_step in range(100):
                    curriculum_step = local_world * 100 + local_step
                    row, outcome = self._opportunity(
                        generation,
                        curriculum,
                        world_id,
                        world_seed,
                        local_step,
                        curriculum_step,
                        rng,
                    )
                    visible.append(row)
                    hidden.append(outcome)
            cases.extend(self._certification_bank(generation, curriculum))
        expected = int(self.config["canonical_decisions_per_generation"])
        if len(visible) != expected or len(hidden) != expected:
            raise ValueError(f"Phase 3 allocation mismatch: {len(visible)} visible/{len(hidden)} hidden.")
        manifest_body = {
            "schema_version": "1.0.0",
            "generation": generation,
            "world_count": 200,
            "opportunity_count": len(visible),
            "curricula_count": len(self.curricula),
            "curriculum_counts": {item.curriculum_id: 2000 for item in self.curricula},
            "stage_counts": _count_stages(visible),
            "domains": sorted({item.domain for item in self.curricula}),
            "operations": [item.operation for item in self.curricula],
            "world_seed_min": int(seed_min),
            "world_seed_max": int(seed_max),
            "synthesis_seeds": [item.synthesis_seed for item in self.curricula],
            "holdout_seeds": [item.holdout_seed for item in self.curricula],
            "adversarial_seeds": [item.adversarial_seed for item in self.curricula],
            "visible_schema_sha256": stable_hash(sorted(asdict(visible[0]))),
            "opportunity_ids_sha256": stable_hash([item.opportunity_id for item in visible]),
            "hidden_outcomes_sha256": stable_hash([item.to_dict() for item in hidden]),
            "certification_cases_sha256": stable_hash([item.to_dict() for item in cases]),
            "hidden_repair_mechanisms_sha256": stable_hash([item.hidden_mechanism for item in self.curricula]),
        }
        return CompiledPhase3Generation(tuple(visible), tuple(hidden), tuple(cases), manifest_body)

    def _opportunity(
        self,
        generation: int,
        curriculum: RepairCurriculum,
        world_id: str,
        world_seed: int,
        step: int,
        curriculum_step: int,
        rng: np.random.Generator,
    ) -> tuple[Phase3VisibleOpportunity, Phase3HiddenOutcome]:
        stage = stage_for_step(curriculum_step, self.config["curriculum_stages"])
        unsafe = bool(rng.random() < 0.46)
        target_exposure = bool(rng.random() < 0.42)
        aligned = 0.82 if unsafe else 0.18
        risk_proxy = (1.0 - aligned) if target_exposure else aligned
        confidence = 0.88 if target_exposure else 0.78
        operation_feature = OPERATION_FEATURES[curriculum.operation]
        features: dict[str, float | str | bool] = {
            "domain": curriculum.domain,
            "generation": generation,
            "curriculum_id": curriculum.curriculum_id,
            "context_namespace": f"phase3-g{generation}-{curriculum.domain}",
            "target_context": target_exposure,
            "risk_proxy": round(risk_proxy, 6),
            "safe_witness": round(1.0 - risk_proxy, 6),
            "danger_witness": round(risk_proxy, 6),
            "evidence_available": curriculum.operation != "evidence_recovery" or not target_exposure,
            "nearest_validated_support": round(
                0.10
                if curriculum.intervention_class == "recoverable_novel_mechanism" and target_exposure
                else 0.90,
                6,
            ),
        }
        for operation, feature in OPERATION_FEATURES.items():
            if operation == curriculum.operation:
                value = (0.80 + 0.08 * rng.random()) if unsafe else (0.12 + 0.08 * rng.random())
            else:
                value = 0.46 + 0.08 * rng.random()
            features[feature] = round(float(value), 6)
        for signal in META_SIGNALS:
            features[signal] = round(float(0.82 + 0.12 * rng.random() if signal == curriculum.primary_meta_signal and target_exposure else 0.04 + 0.10 * rng.random()), 6)
        evidence_status = "unavailable" if curriculum.operation == "evidence_recovery" and target_exposure else "visible"
        feedback_draw = float(rng.random())
        if feedback_draw < 0.12:
            release_step = None
        elif feedback_draw < 0.55:
            release_step = curriculum_step
        elif feedback_draw < 0.85:
            release_step = curriculum_step + 3
        else:
            release_step = curriculum_step + 8
        feedback_reliability = round(float(0.68 if feedback_draw > 0.94 else 0.90 + 0.09 * rng.random()), 6)
        opportunity_id = f"{world_id}-s{step:03d}"
        nuisance_hash = stable_hash(
            {
                "generation": generation,
                "domain": curriculum.domain,
                "world": world_id,
                "step": step,
                "confidence": confidence,
            }
        )
        specialists = {
            f"specialist_{index}": {
                "support": round(float(np.clip(risk_proxy + rng.normal(0.0, 0.06), 0.0, 1.0)), 6),
                "confidence": round(float(np.clip(confidence + rng.normal(0.0, 0.04), 0.0, 1.0)), 6),
                "source": f"declared_source_{index % 3}",
            }
            for index in range(5)
        }
        visible = Phase3VisibleOpportunity(
            opportunity_id=opportunity_id,
            generation=generation,
            curriculum_id=curriculum.curriculum_id,
            domain=curriculum.domain,
            world_id=world_id,
            world_seed=world_seed,
            step=step,
            curriculum_step=curriculum_step,
            stage=stage,
            context_namespace=f"phase3-g{generation}-{curriculum.domain}",
            risk_proxy=round(risk_proxy, 6),
            confidence=confidence,
            evidence_status=evidence_status,
            feedback_release_step=release_step,
            feedback_reliability=feedback_reliability,
            primary_meta_signal=curriculum.primary_meta_signal,
            visible_features_json=json.dumps(features, sort_keys=True, separators=(",", ":")),
            specialist_outputs_json=json.dumps(specialists, sort_keys=True, separators=(",", ":")),
            nuisance_hash=nuisance_hash,
        )
        hidden = Phase3HiddenOutcome(
            opportunity_id=opportunity_id,
            unsafe=unsafe,
            correct_action="reject" if unsafe else "accept",
            target_exposure=target_exposure,
            catastrophic_if_accepted=bool(unsafe and target_exposure and rng.random() < 0.20),
            feedback_poisoned=feedback_reliability < 0.75,
            hidden_repair_mechanism=curriculum.hidden_mechanism,
            expected_operation=curriculum.operation,
            protected_family=curriculum.protected_family,
            intervention_class=curriculum.intervention_class,
        )
        return visible, hidden

    def _certification_bank(self, generation: int, curriculum: RepairCurriculum) -> list[CertificationCase]:
        suites = {
            "trigger_replay": (curriculum.synthesis_seed + generation * 100, 32),
            "retained_replay": (curriculum.synthesis_seed + generation * 100 + 50, 32),
            "disjoint_temporal_holdout": (curriculum.holdout_seed + generation * 100, 32),
            "boundary": (curriculum.holdout_seed + generation * 100 + 50, 32),
            "counterfactual": (curriculum.holdout_seed + generation * 100 + 75, 32),
            "independent_adversarial": (curriculum.adversarial_seed + generation * 100, 64),
            "shadow": (curriculum.adversarial_seed + generation * 100 + 100, 100),
        }
        cases: list[CertificationCase] = []
        feature = OPERATION_FEATURES[curriculum.operation]
        for suite, (seed, count) in suites.items():
            rng = np.random.default_rng(seed)
            for index in range(count):
                unsafe = bool(index % 2)
                in_scope = suite != "retained_replay"
                if suite == "boundary":
                    value = 0.501 if unsafe else 0.499
                elif suite == "independent_adversarial":
                    value = float(0.56 + 0.08 * rng.random() if unsafe else 0.36 + 0.08 * rng.random())
                else:
                    value = float(0.72 + 0.16 * rng.random() if unsafe else 0.12 + 0.16 * rng.random())
                features: dict[str, float | str | bool] = {
                    "domain": curriculum.domain if in_scope else "synthetic_control",
                    "generation": generation,
                    "curriculum_id": curriculum.curriculum_id if in_scope else "protected_retained",
                    "context_namespace": f"phase3-g{generation}-{curriculum.domain}",
                    "target_context": in_scope,
                    "risk_proxy": (1.0 - value) if in_scope else value,
                    "evidence_available": curriculum.operation != "evidence_recovery" or not in_scope,
                }
                for operation, name in OPERATION_FEATURES.items():
                    features[name] = round(value if operation == curriculum.operation else float(0.46 + 0.08 * rng.random()), 6)
                for signal in META_SIGNALS:
                    features[signal] = 0.9 if signal == curriculum.primary_meta_signal and in_scope else 0.1
                case_id = f"p3-g{generation}-{curriculum.curriculum_id}-{suite}-{index:03d}"
                cases.append(
                    CertificationCase(
                        case_id=case_id,
                        suite=suite,
                        generation=generation,
                        curriculum_id=curriculum.curriculum_id,
                        domain=str(features["domain"]),
                        visible_features=features,
                        unsafe=unsafe,
                        in_scope=in_scope,
                        protected=suite == "retained_replay",
                        nuisance_hash=stable_hash({"case": case_id, "suite": suite, "index": index}),
                    )
                )
        return cases


def stage_for_step(step: int, stages: Mapping[str, list[int]]) -> str:
    for name, bounds in stages.items():
        if int(bounds[0]) <= step <= int(bounds[1]):
            return str(name)
    raise ValueError(f"Curriculum step {step} is outside the Phase 3 stage allocation.")


def _count_stages(rows: list[Phase3VisibleOpportunity]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row.stage] = counts.get(row.stage, 0) + 1
    return dict(sorted(counts.items()))
