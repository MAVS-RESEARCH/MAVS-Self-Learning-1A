"""Exact A0-A49 registry and single-diff ablation factory."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Mapping

import yaml

from mavs10d.core.hashing import stable_hash


REPO_ROOT = Path(__file__).resolve().parents[3]
ABLATION_ROOT = REPO_ROOT / "configs" / "ablations"

AUTHORITATIVE_CONDITIONS: tuple[str, ...] = (
    "Full MAVS-SL reference.",
    "No learning: frozen best development configuration.",
    "Threshold-only learning: test whether diagnostic synthesis is unnecessary.",
    "Selector-only learning: fixed library, adaptive context selection only.",
    "Calibration-only: adapt diagnostic thresholds and weights only.",
    "No diagnostic creation: tune existing G, never expand it.",
    "No split/merge: prevent scope refinement.",
    "No meta-diagnostics: remove novelty, coverage-gap, scope, and masking monitors.",
    "No failure ontology: flat replay memory only.",
    "No failure capsules: remove compressed reusable mechanism memory.",
    "No counterfactual validation.",
    "No adversarial certification: replay and IID holdout only.",
    "No retained replay: measure catastrophic governance forgetting.",
    "No shadow phase: promote immediately after offline certification.",
    "No safety kernel: permit optimizer safety/recall tradeoffs.",
    "No rollback: measure persistence of damaging updates.",
    "No escalation: force binary decisions.",
    "Reject-on-unknown.",
    "Accept-on-unknown.",
    "No bounded mitigation: safe evidence cannot protect recall.",
    "Raw-correlation hard veto: reintroduce the pre-DS-CF failure.",
    "No safe witness.",
    "No danger witnesses: harm score acts alone.",
    "No provenance diagnostics.",
    "No delayed-feedback handling: treat missing labels as negative evidence.",
    "No feedback-reliability model: poisoned labels update governance normally.",
    "Homogeneous specialists: remove representation diversity.",
    "Perfectly shared representation: worst-case collapse stress.",
    "No configuration library: continually rewrite one global eta.",
    "No selector fallback: allow low-confidence configuration selection.",
    "Unlimited diagnostic growth: remove complexity/redundancy control.",
    "Tiny memory: severe replay compression.",
    "Random proposal engine: control for search budget alone.",
    "Oracle failure-family labels: attribution upper bound, not a competitor.",
    "No inter-generation persistence: reset all learned state between G1/G2/G3.",
    "Diagnostics-only persistence: retain G and scopes; reset ontology, capsules, selector, and library.",
    "Ontology-only persistence: retain classes/signatures; rebuild diagnostics/configurations.",
    "Configuration-library-only persistence: retain approved configs; reset failure memory and genealogy.",
    "No consolidation: carry every diagnostic/configuration without pruning, merging, or deprecation.",
    "No diagnostic genealogy: keep active functions but remove lineage and historical scope evidence.",
    "No negative-transfer detector.",
    "No prior-generation retention replay: certify later updates on current evidence only.",
    "Frozen after Generation 1: learn only in G1.",
    "Fresh selector each generation: retain diagnostics/configs, reset context selection.",
    "Raw-memory persistence: bounded raw cases/nearest-neighbor lookup without abstract capsules or synthesis.",
    "Surface-reset only: easy-transfer upper bound.",
    "Structural-reset stress.",
    "Adversarial library-targeting reset under fixed pre-registered budget.",
    "Unlimited participant memory: storage upper bound.",
    "Matched-memory cumulative baseline: same persistent-state byte budget as MAVS-SL.",
)


@dataclass(frozen=True)
class AblationState:
    learning_mode: str = "full"
    diagnostic_creation: bool = True
    scope_refinement: bool = True
    meta_diagnostics: bool = True
    failure_ontology: bool = True
    failure_capsules: bool = True
    counterfactual_validation: bool = True
    adversarial_certification: bool = True
    retained_replay: bool = True
    shadow_phase: bool = True
    safety_kernel: bool = True
    rollback: bool = True
    escalation: bool = True
    unknown_policy: str = "escalate"
    bounded_mitigation: bool = True
    correlation_policy: str = "scoped"
    safe_witness: bool = True
    danger_witness: bool = True
    provenance_diagnostics: bool = True
    delayed_feedback_handling: bool = True
    feedback_reliability: bool = True
    specialist_diversity: str = "heterogeneous"
    representation_sharing: str = "partial"
    configuration_library: bool = True
    selector_fallback: bool = True
    diagnostic_growth: str = "bounded"
    memory_budget: str = "mavs_sl"
    proposal_engine: str = "constrained"
    attribution_labels: str = "visible_inference"
    persistence: str = "full"
    consolidation: bool = True
    diagnostic_genealogy: bool = True
    negative_transfer_detector: bool = True
    prior_generation_retention_replay: bool = True
    learning_horizon: str = "all_generations"
    selector_reset: str = "retain"
    reset_filter: str = "all"


@dataclass(frozen=True)
class AblationSpec:
    file_id: str
    ablation_id: str
    exact_condition: str
    category: str
    competitive: bool
    oracle: bool
    changes: Mapping[str, Any]
    config_hash: str

    def state(self) -> AblationState:
        base = AblationState()
        unknown = set(self.changes) - set(asdict(base))
        if unknown:
            raise ValueError(f"Unknown ablation toggles for {self.ablation_id}: {sorted(unknown)}")
        state = replace(base, **dict(self.changes))
        observed = {key: value for key, value in asdict(state).items() if value != asdict(base)[key]}
        if observed != dict(self.changes):
            raise ValueError(f"Silent or ineffective ablation diff for {self.ablation_id}.")
        return state


def load_ablation_specs(root: Path = ABLATION_ROOT) -> tuple[AblationSpec, ...]:
    paths = sorted(root.glob("A[0-4][0-9].yaml"))
    expected_names = [f"A{index:02d}.yaml" for index in range(50)]
    if [path.name for path in paths] != expected_names:
        raise ValueError("Phase 5 requires exactly configs/ablations/A00.yaml through A49.yaml.")
    specs: list[AblationSpec] = []
    for index, path in enumerate(paths):
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        expected_id = f"A{index}"
        if payload["file_id"] != f"A{index:02d}" or payload["ablation_id"] != expected_id:
            raise ValueError(f"Ablation filename/ID mismatch: {path.name}")
        if payload["exact_condition"] != AUTHORITATIVE_CONDITIONS[index]:
            raise ValueError(f"Ablation condition mismatch: {expected_id}")
        changes = dict(payload.get("changes") or {})
        if index and len(changes) != 1:
            raise ValueError(f"{expected_id} must declare exactly one explicit top-level config diff.")
        if not index and changes:
            raise ValueError("A0 reference must have an empty diff.")
        unsigned = {key: value for key, value in payload.items() if key != "schema_version"}
        spec = AblationSpec(
            file_id=payload["file_id"], ablation_id=payload["ablation_id"],
            exact_condition=payload["exact_condition"], category=payload["category"],
            competitive=bool(payload["competitive"]), oracle=bool(payload["oracle"]),
            changes=changes, config_hash=stable_hash(unsigned),
        )
        spec.state()
        specs.append(spec)
    return tuple(specs)


def registry_manifest() -> dict[str, Any]:
    specs = load_ablation_specs()
    body = {
        "schema_version": "1.0.0", "count": len(specs),
        "ablations": [
            {
                "file_id": spec.file_id, "ablation_id": spec.ablation_id,
                "exact_condition": spec.exact_condition, "category": spec.category,
                "competitive": spec.competitive, "oracle": spec.oracle,
                "changes": dict(spec.changes), "config_hash": spec.config_hash,
                "resolved_state": asdict(spec.state()),
            }
            for spec in specs
        ],
    }
    return {**body, "registry_sha256": stable_hash(body)}
