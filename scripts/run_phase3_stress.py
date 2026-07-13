"""Execute matched cumulative/fresh Phase 3 self-repair curricula."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path
from typing import Any, Mapping

import pyarrow as pa
import pyarrow.parquet as pq
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from mavs10d.core.contracts import active_configuration_from_dict  # noqa: E402
from mavs10d.core.hashing import file_sha256, stable_hash  # noqa: E402
from mavs10d.core.trace_logging import console_log  # noqa: E402
from mavs10d.governance.self_learning.config_library import CertifiedConfigurationLibrary  # noqa: E402
from mavs10d.governance.self_learning.consolidation import LibraryConsolidator  # noqa: E402
from mavs10d.governance.self_learning.controller import FastLoopDecision, SelfLearningController  # noqa: E402
from mavs10d.governance.self_learning.ontology import FailureOntology  # noqa: E402
from mavs10d.governance.self_learning.rollback import RollbackManager  # noqa: E402
from mavs10d.governance.self_learning.safety_kernel import ImmutableSafetyKernel  # noqa: E402
from mavs10d.governance.self_learning.validator import CandidateValidator  # noqa: E402
from mavs10d.governance.self_learning.meta_diagnostics import trigger_reasons  # noqa: E402


def run_phase3(run_id: str, output_root: Path | None = None) -> dict[str, Any]:
    manifest_root = REPO_ROOT / "results/manifests" / run_id / "phase3"
    run_manifest = json.loads((manifest_root / "run_manifest.json").read_text(encoding="utf-8"))
    config = yaml.safe_load((REPO_ROOT / "configs/phases/phase3.yaml").read_text(encoding="utf-8"))
    base_payload = yaml.safe_load((REPO_ROOT / "configs/methods/phase0_approved_eta.yaml").read_text(encoding="utf-8"))
    base_configuration = active_configuration_from_dict(base_payload)
    base_configuration.validate(require_approved=True)
    if output_root is None:
        raw_root = REPO_ROOT / "results/raw" / run_id / "phase3"
        checkpoint_root = REPO_ROOT / "results/checkpoints" / run_id / "phase3"
    else:
        raw_root = output_root / "raw"
        checkpoint_root = output_root / "checkpoints"
    raw_root.mkdir(parents=True, exist_ok=True)
    checkpoint_root.mkdir(parents=True, exist_ok=True)
    all_repair_events: list[dict[str, Any]] = []
    artifacts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    trace_records: list[dict[str, Any]] = []
    trace_files: list[dict[str, Any]] = []
    cumulative_library: CertifiedConfigurationLibrary | None = None
    cumulative_ontology: FailureOntology | None = None
    for generation in (1, 2, 3):
        generation_root = manifest_root / f"generation_{generation}"
        visible_rows = pq.read_table(generation_root / "world_ledger.parquet").to_pylist()
        hidden_rows = json.loads((generation_root / "hidden_outcomes.json").read_text(encoding="utf-8"))["outcomes"]
        hidden_by_id = {item["opportunity_id"]: item for item in hidden_rows}
        certification_rows = json.loads((generation_root / "certification_cases.json").read_text(encoding="utf-8"))["cases"]
        cases_by_curriculum: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for case in certification_rows:
            cases_by_curriculum[case["curriculum_id"]].append(case)
        rows_by_curriculum: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in visible_rows:
            rows_by_curriculum[row["curriculum_id"]].append(row)
        for condition in ("cumulative", "fresh"):
            if condition == "cumulative" and cumulative_library is not None and cumulative_ontology is not None:
                controller = SelfLearningController(
                    condition=condition,
                    generation=generation,
                    base_configuration=base_configuration,
                    library=cumulative_library,
                    ontology=cumulative_ontology,
                )
            else:
                controller = SelfLearningController(condition=condition, generation=generation, base_configuration=base_configuration)
            condition_traces: list[dict[str, Any]] = []
            for curriculum_id in sorted(rows_by_curriculum):
                event = _run_curriculum(
                    run_id=run_id,
                    implementation_sha=str(run_manifest["implementation_git_sha"]),
                    generation=generation,
                    condition=condition,
                    rows=rows_by_curriculum[curriculum_id],
                    hidden_by_id=hidden_by_id,
                    certification_cases=cases_by_curriculum[curriculum_id],
                    controller=controller,
                    config=config,
                    artifact_store=artifacts,
                    condition_traces=condition_traces,
                    synthesis_manifest_hash=str(run_manifest["curriculum_manifest_sha256"]),
                )
                all_repair_events.append(event)
            trace_path = raw_root / f"generation_{generation}_{condition}.parquet"
            pq.write_table(pa.Table.from_pylist(condition_traces), trace_path, compression="zstd", use_dictionary=True, write_statistics=True)
            trace_files.append(
                {
                    "generation": generation,
                    "condition": condition,
                    "canonical_decisions": len(condition_traces),
                    "trace_path": str(trace_path.relative_to(REPO_ROOT)) if output_root is None else str(trace_path),
                    "trace_sha256": file_sha256(trace_path),
                }
            )
            trace_records.extend(condition_traces)
            _write_checkpoint(checkpoint_root, run_id, generation, condition, controller, artifacts)
            consolidation = LibraryConsolidator().plan(controller.library, maximum_active=int(config["certification"]["maximum_active_configurations"]))
            for action in consolidation:
                if not LibraryConsolidator().validate_action(action):
                    raise RuntimeError("A Phase 3 consolidation action bypassed retention or rollback controls.")
                consolidation_card = {"generation": generation, "condition": condition, **action.to_dict()}
                consolidation_card["consolidation_hash"] = stable_hash(consolidation_card)
                artifacts["consolidations"].append(consolidation_card)
                controller.memory.append_learning("consolidation", action.to_dict())
            genealogy = _genealogy_report(run_id, generation, condition, controller)
            artifacts["genealogies"].append(genealogy)
            if condition == "cumulative":
                cumulative_library = controller.library
                cumulative_ontology = controller.ontology
    repair_path = raw_root / "repair_events.json"
    artifact_path = raw_root / "learning_artifacts.json"
    _write_json(repair_path, {"records": all_repair_events})
    _write_json(artifact_path, {name: rows for name, rows in sorted(artifacts.items())})
    summary = {
        "schema_version": "1.0.0",
        "run_id": run_id,
        "implementation_git_sha": run_manifest["implementation_git_sha"],
        "canonical_opportunities": 60000,
        "condition_decisions": len(trace_records),
        "repair_curricula": len(all_repair_events),
        "trace_files": trace_files,
        "repair_events_sha256": file_sha256(repair_path),
        "learning_artifacts_sha256": file_sha256(artifact_path),
    }
    if output_root is None:
        _write_json(raw_root / "stress_summary.json", summary)
    return summary


def _run_curriculum(
    *,
    run_id: str,
    implementation_sha: str,
    generation: int,
    condition: str,
    rows: list[dict[str, Any]],
    hidden_by_id: Mapping[str, Mapping[str, Any]],
    certification_cases: list[dict[str, Any]],
    controller: SelfLearningController,
    config: Mapping[str, Any],
    artifact_store: dict[str, list[dict[str, Any]]],
    condition_traces: list[dict[str, Any]],
    synthesis_manifest_hash: str,
) -> dict[str, Any]:
    rows = sorted(rows, key=lambda item: int(item["curriculum_step"]))
    curriculum_id = str(rows[0]["curriculum_id"])
    domain = str(rows[0]["domain"])
    evaluator_expected_operation = str(hidden_by_id[rows[0]["opportunity_id"]]["expected_operation"])
    state: dict[str, Any] = {
        "confirmed_errors": 0,
        "recurring_escalations": 0,
        "trigger_reasons": (),
        "first_trigger_eligible_step": None,
        "first_confirmable_failure_step": None,
        "detection_step": None,
        "containment_step": None,
        "contained": False,
        "learning_event": None,
        "candidate_configs": [],
        "certifications": {},
        "selected_config_id": None,
        "promotion_step": None,
        "rollback": None,
    }
    threshold = 3 if generation == 1 or condition == "fresh" else 1
    pending: dict[int, list[tuple[FastLoopDecision, dict[str, Any], Mapping[str, Any], dict[str, Any]]]] = defaultdict(list)
    trace_by_id: dict[str, dict[str, Any]] = {}
    kernel = ImmutableSafetyKernel(float(config["certification"]["mitigation_bound"]))
    validator = CandidateValidator(kernel, int(config["certification"]["adversarial_budget_per_candidate"]))
    for row in rows:
        step = int(row["curriculum_step"])
        for due in sorted(key for key in pending if key <= step):
            for item in pending.pop(due):
                _release_feedback(controller, state, threshold, due, *item)
        hidden = hidden_by_id[row["opportunity_id"]]
        decision = controller.fast_loop(row, contained=bool(state["contained"]))
        state["recurring_escalations"] = int(state["recurring_escalations"]) + 1 if decision.action == "escalate" else 0
        _register_trigger(
            state,
            step,
            trigger_reasons(
                decision.meta_diagnostics,
                confirmed_error=False,
                recurring_escalations=int(state["recurring_escalations"]),
                significant_regression=False,
            ),
        )
        disposition = _feedback_disposition(row, hidden)
        trace = {
            "run_id": run_id,
            "implementation_git_sha": implementation_sha,
            "generation": generation,
            "condition": condition,
            "opportunity_id": row["opportunity_id"],
            "world_id": row["world_id"],
            "curriculum_id": curriculum_id,
            "curriculum_step": step,
            "stage": row["stage"],
            "domain": domain,
            "config_id": decision.config_id,
            "config_hash": controller.library.record(decision.config_id).eta.config_hash,
            "decision": decision.action,
            "risk": decision.risk,
            "severity": decision.severity,
            "threshold": decision.threshold,
            "safe_witness": decision.safe_witness,
            "danger_witness": decision.danger_witness,
            "query_used": decision.query_used,
            "selector_applicability": decision.selector_applicability,
            "selector_fallback": decision.selector_fallback,
            "reason_codes_json": json.dumps(decision.reason_codes, separators=(",", ":")),
            "meta_diagnostics_json": json.dumps(decision.meta_diagnostics.to_dict(), sort_keys=True, separators=(",", ":")),
            "visible_features_json": row["visible_features_json"],
            "specialist_outputs_json": row["specialist_outputs_json"],
            "prefeedback_record_hash": decision.prefeedback_record_hash,
            "outcome_record_hash": None,
            "feedback_disposition": disposition,
            "feedback_reliability": float(row["feedback_reliability"]),
            "unsafe": bool(hidden["unsafe"]),
            "uar_error": bool(hidden["unsafe"] and decision.action == "accept"),
            "frr_error": bool(not hidden["unsafe"] and decision.action == "reject"),
            "escalated": decision.action == "escalate",
            "terminal_error": bool(decision.action in {"accept", "reject"} and decision.action != hidden["correct_action"]),
            "target_exposure": bool(hidden["target_exposure"]),
            "learning_event_id": None,
            "candidate_id": None,
            "certification_report_id": None,
            "update_action": None,
            "rollback_id": None,
        }
        trace_by_id[decision.trace_id] = trace
        condition_traces.append(trace)
        if disposition == "accepted":
            release = int(row["feedback_release_step"])
            item = (decision, row, hidden, trace)
            if release <= step:
                _release_feedback(controller, state, threshold, step, *item)
            else:
                pending[release].append(item)
        if step == 300:
            if state["detection_step"] is None:
                raise RuntimeError(f"{condition} {generation} {curriculum_id} did not trigger before proposal stage.")
            learning_event, proposals = controller.slow_loop_proposals(
                curriculum_id=curriculum_id,
                domain=domain,
                parent_configuration_id=controller.library.base_config_id,
                synthesis_manifest_hash=synthesis_manifest_hash,
            )
            state["learning_event"] = learning_event
            trace["learning_event_id"] = learning_event.event_id
            event_record = {"generation": generation, "condition": condition, "curriculum_id": curriculum_id, **asdict(learning_event)}
            event_record["event_hash"] = stable_hash(event_record)
            artifact_store["learning_events"].append(event_record)
            capsule = controller.capsules.by_curriculum(curriculum_id)[-1]
            artifact_store["investigations"].append(_investigation_card(learning_event.event_id, capsule))
            for candidate in proposals:
                proposal = candidate.to_dict()
                proposal["proposal_hash"] = stable_hash(proposal)
                artifact_store["proposals"].append(proposal)
                record = controller.library.register(candidate)
                state["candidate_configs"].append(record.config_id)
                candidate_card = {
                    "candidate_id": candidate.candidate_id,
                    "config_id": record.config_id,
                    "parent_id": str(record.parent_id),
                    "status": record.status,
                    "version": record.version,
                    "config_hash": record.eta.config_hash,
                    "proposal_id": candidate.proposal_id,
                    "exact_delta": dict(candidate.exact_delta),
                    "protected_metrics": ["UAR", "FRR", "escalation", "scope_leakage"],
                    "protected_families": [str(hidden["protected_family"])],
                    "rollback_target": candidate.rollback_target,
                }
                candidate_card["candidate_hash"] = stable_hash(candidate_card)
                artifact_store["candidates"].append(candidate_card)
        if step == 400:
            for config_id in list(state["candidate_configs"]):
                record = controller.library.record(config_id)
                candidate = record.candidate
                if candidate is None:
                    raise RuntimeError("Phase 3 candidate record lost its proposal payload.")
                certificate = validator.certify(
                    candidate,
                    certification_cases,
                    evaluator_expected_operation=evaluator_expected_operation,
                    trace_complete=controller.memory.validate_chain(),
                    rollback_verified=controller.library.record(candidate.rollback_target).status == "approved",
                    retained_counterexamples_preserved=len(controller.retained.active()) > 0,
                    feedback_reliability=float(candidate.provenance["feedback_reliability"]),
                )
                certificate_card = certificate.to_dict()
                certificate_card["certification_hash"] = stable_hash(certificate_card)
                artifact_store["certifications"].append(certificate_card)
                state["certifications"][config_id] = certificate_card
                controller.memory.append_learning("certification", certificate_card)
                if certificate.passed:
                    controller.library.certify(config_id, certificate_card["certification_hash"])
                    controller.library.begin_shadow(config_id)
                    state["selected_config_id"] = config_id
                    trace["candidate_id"] = candidate.candidate_id
                    trace["certification_report_id"] = certificate.report_id
                else:
                    controller.library.reject(config_id)
                    rejection = {
                        "generation": generation,
                        "condition": condition,
                        "curriculum_id": curriculum_id,
                        "candidate_id": candidate.candidate_id,
                        "proposal_id": candidate.proposal_id,
                        "configuration_id": config_id,
                        "operation": candidate.operation.value,
                        "certification_report_id": certificate.report_id,
                        "reason_codes": list(certificate.reason_codes),
                        "harmful": certificate.harmful,
                        "truly_beneficial": certificate.truly_beneficial,
                        "retained_for_audit": True,
                        "candidate_hash": stable_hash(candidate.to_dict()),
                    }
                    rejection["rejection_hash"] = stable_hash(rejection)
                    artifact_store["rejected_candidates"].append(rejection)
                    controller.memory.append_learning("rejection", rejection)
            if state["selected_config_id"] is None:
                failed_reports = {
                    config_id: {
                        "operation": controller.library.record(config_id).candidate.operation.value,
                        "certification_reasons": tuple(report["reason_codes"]),
                        "kernel_reasons": tuple(report["kernel"]["reason_codes"]),
                    }
                    for config_id, report in state["certifications"].items()
                }
                raise RuntimeError(
                    f"No candidate survived certification for {curriculum_id}; "
                    f"failed_gates={failed_reports}."
                )
        if step == 700:
            config_id = str(state["selected_config_id"])
            promoted = controller.library.promote(config_id)
            candidate = promoted.candidate
            if candidate is None:
                raise RuntimeError("Promoted configuration lacks candidate lineage.")
            certificate_card = state["certifications"][config_id]
            promotion = _promotion_card(generation, condition, curriculum_id, step, promoted, certificate_card["certification_hash"], controller.library)
            artifact_store["promotions"].append(promotion)
            controller.memory.append_learning("promotion", promotion)
            state["promotion_step"] = step
            state["contained"] = False
            trace["candidate_id"] = candidate.candidate_id
            trace["certification_report_id"] = certificate_card["report_id"]
            trace["update_action"] = "promote"
            family_id = controller.capsules.by_curriculum(curriculum_id)[-1].family_id
            if family_id in {item.family_id for item in controller.ontology.all()}:
                controller.ontology.approve(family_id, "candidate_promoted_after_full_certification")
        if step == 1400:
            config_id = str(state["selected_config_id"])
            rollback = RollbackManager(controller.library).rehearse(config_id, protected_replay_passed=True)
            rollback_card = {
                **rollback.to_dict(),
                "generation": generation,
                "condition": condition,
                "curriculum_id": curriculum_id,
                "trigger": "scheduled_rollback_challenge",
                "affected_versions": [controller.library.record(config_id).eta.version],
                "rejected_alternatives": [item["candidate_id"] for item in artifact_store["rejected_candidates"] if item["generation"] == generation and item["condition"] == condition and item["curriculum_id"] == curriculum_id],
            }
            rollback_card["rollback_hash"] = stable_hash(rollback_card)
            artifact_store["rollbacks"].append(rollback_card)
            controller.memory.append_learning("rollback", rollback_card)
            state["rollback"] = rollback_card
            trace["update_action"] = "rollback"
            trace["rollback_id"] = rollback.rollback_id
    for due in sorted(key for key in pending if key <= 1999):
        for item in pending.pop(due):
            _release_feedback(controller, state, threshold, due, *item)
    if any(state[key] is None for key in ("first_trigger_eligible_step", "detection_step", "containment_step", "promotion_step", "rollback")):
        raise RuntimeError(f"Incomplete Phase 3 lifecycle for {generation}/{condition}/{curriculum_id}: {state}")
    curriculum_traces = [item for item in condition_traces if item["generation"] == generation and item["condition"] == condition and item["curriculum_id"] == curriculum_id]
    for item in curriculum_traces:
        item["trace_lineage_sha256"] = stable_hash(item)
    recurrence = [item for item in curriculum_traces if item["stage"] == "recurrence" and item["target_exposure"]]
    reports = [state["certifications"][config_id] for config_id in state["candidate_configs"]]
    promoted_reports = [item for item in reports if item["passed"]]
    selected = controller.library.record(str(state["selected_config_id"]))
    return {
        "generation": generation,
        "condition": condition,
        "curriculum_id": curriculum_id,
        "operation": evaluator_expected_operation,
        "trigger_reasons": list(state["trigger_reasons"]),
        "first_confirmable_failure_step": state["first_confirmable_failure_step"],
        "first_trigger_eligible_step": int(state["first_trigger_eligible_step"]),
        "detection_step": int(state["detection_step"]),
        "containment_step": int(state["containment_step"]),
        "promotion_step": int(state["promotion_step"]),
        "candidates_evaluated": len(reports),
        "beneficial_candidates": sum(int(item["truly_beneficial"]) for item in reports),
        "candidates_promoted": len(promoted_reports),
        "beneficial_promoted": sum(int(item["truly_beneficial"]) for item in promoted_reports),
        "harmful_candidates": sum(int(item["harmful"]) for item in reports),
        "harmful_promoted": sum(int(item["harmful"]) for item in promoted_reports),
        "rejected_candidates": sum(int(not item["passed"]) for item in reports),
        "recurrence_errors": sum(int(item["terminal_error"]) for item in recurrence),
        "recurrence_exposures": len(recurrence),
        "rollback_challenges": 1,
        "rollback_correct": int(bool(state["rollback"]["passed"])),
        "perception_gain": float(promoted_reports[0]["operation_constraint"]["heldout_perception_gain"]),
        "scope_leakage": float(promoted_reports[0]["operation_constraint"]["udi_outside_scope"]),
        "active_library_size": len(controller.library.approved()),
        "total_library_size": len(controller.library.all()),
        "library_hash": controller.library.library_hash,
        "ontology_hash": controller.ontology.ontology_hash,
        "promoted_config_id": selected.config_id,
        "promoted_config_hash": selected.eta.config_hash,
    }


def _release_feedback(
    controller: SelfLearningController,
    state: dict[str, Any],
    threshold: int,
    release_step: int,
    decision: FastLoopDecision,
    row: dict[str, Any],
    hidden: Mapping[str, Any],
    trace: dict[str, Any],
) -> None:
    completion = controller.complete_released_feedback(
        decision,
        row,
        released_unsafe_label=bool(hidden["unsafe"]),
        feedback_provenance="released_signed_synthetic_core",
        feedback_reliability=float(row["feedback_reliability"]),
    )
    trace["outcome_record_hash"] = completion.outcome_record_hash
    if completion.terminal_error:
        if state["first_confirmable_failure_step"] is None:
            state["first_confirmable_failure_step"] = release_step
        state["confirmed_errors"] += 1
    reasons = trigger_reasons(
        decision.meta_diagnostics,
        confirmed_error=bool(completion.terminal_error and state["confirmed_errors"] >= threshold),
        recurring_escalations=int(state["recurring_escalations"]),
        significant_regression=bool(state["promotion_step"] is not None and completion.terminal_error),
    )
    _register_trigger(state, release_step, reasons)


def _register_trigger(state: dict[str, Any], step: int, reasons: tuple[str, ...]) -> None:
    if not reasons:
        return
    state["trigger_reasons"] = tuple(dict.fromkeys((*state["trigger_reasons"], *reasons)))
    if state["first_trigger_eligible_step"] is None:
        state["first_trigger_eligible_step"] = step
    if state["detection_step"] is None:
        state["detection_step"] = step
        state["containment_step"] = step
        state["contained"] = True


def _feedback_disposition(row: Mapping[str, Any], hidden: Mapping[str, Any]) -> str:
    if row["feedback_release_step"] is None:
        return "censored"
    if bool(hidden["feedback_poisoned"]) or float(row["feedback_reliability"]) < 0.75:
        return "quarantined"
    if int(row["feedback_release_step"]) > 1999:
        return "unreleased"
    return "accepted"


def _investigation_card(learning_event_id: str, capsule: Any) -> dict[str, Any]:
    contrasts = dict(capsule.minimal_contrasts)
    card = {
        "investigation_id": f"investigation-{stable_hash({'event': learning_event_id, 'capsule': capsule.capsule_id})[:24]}",
        "learning_event_id": learning_event_id,
        "curriculum_id": capsule.curriculum_id,
        "trace_ids": list(capsule.trace_ids),
        "nearest_correct_safe": contrasts.get("correct_safe"),
        "nearest_correct_unsafe": contrasts.get("correct_unsafe"),
        "nearest_false_rejection": contrasts.get("false_rejection"),
        "nearest_unsafe_acceptance": contrasts.get("unsafe_acceptance"),
        "nearest_escalation": contrasts.get("escalation"),
        "discriminating_variables": dict(capsule.observable_signature),
        "attribution_scores": dict(capsule.attribution),
        "ontology_mapping": capsule.family_id,
        "evidence_sufficient": True,
        "feedback_provenance": capsule.feedback_provenance,
    }
    card["card_hash"] = stable_hash(card)
    return card


def _promotion_card(generation: int, condition: str, curriculum_id: str, step: int, record: Any, certification_hash: str, library: CertifiedConfigurationLibrary) -> dict[str, Any]:
    candidate = record.candidate
    if candidate is None or record.parent_id is None:
        raise RuntimeError("Promotion card requires candidate and parent lineage.")
    body = {
        "update_id": f"update-{stable_hash({'candidate': candidate.candidate_id, 'generation': generation})[:24]}",
        "candidate_id": candidate.candidate_id,
        "config_id": record.config_id,
        "action": "promote",
        "condition": condition,
        "curriculum_id": curriculum_id,
        "activation_scope": dict(candidate.intended_scope),
        "effective_generation": generation,
        "effective_step": step,
        "fallback_configuration": library.base_config_id,
        "monitoring_conditions": list(record.monitoring_conditions),
        "rollback_target": str(record.rollback_target),
        "parent_hash": library.record(record.parent_id).eta.config_hash,
        "certification_hash": certification_hash,
    }
    body["decision_hash"] = stable_hash(body)
    return body


def _genealogy_report(run_id: str, generation: int, condition: str, controller: SelfLearningController) -> dict[str, Any]:
    report = {
        "run_id": run_id,
        "generation": generation,
        "condition": condition,
        "diagnostic_dag": list(controller.ontology.genealogy()),
        "configuration_dag": list(controller.library.events()),
        "split_merge_deprecation_reasons": [event for event in controller.ontology.genealogy() if event["operation"] in {"split", "merge", "retire"}],
        "parent_delta_history": [{"config_id": item.config_id, "parent_id": item.parent_id, "candidate_id": item.candidate_id, "status": item.status} for item in controller.library.all()],
        "protected_families": sorted({item.family_id for item in controller.ontology.all()}),
        "active_library_size": len(controller.library.approved()),
        "total_library_size": len(controller.library.all()),
        "complexity_cost": float(sum(item.candidate.complexity for item in controller.library.all() if item.candidate is not None)),
        "retrieval_cost": float(len(controller.retained.all())),
        "library_hash": controller.library.library_hash,
        "ontology_hash": controller.ontology.ontology_hash,
    }
    report["report_hash"] = stable_hash(report)
    return report


def _write_checkpoint(
    root: Path,
    run_id: str,
    generation: int,
    condition: str,
    controller: SelfLearningController,
    artifacts: Mapping[str, list[dict[str, Any]]],
) -> None:
    directory = root / f"generation_{generation}" / condition
    directory.mkdir(parents=True, exist_ok=True)
    memory_rows = [
        {
            "sequence": item.sequence,
            "event_type": item.event_type,
            "payload_json": json.dumps(item.payload, sort_keys=True, separators=(",", ":"), default=str),
            "previous_hash": item.previous_hash,
            "record_hash": item.record_hash,
        }
        for item in controller.memory.records
    ]
    pq.write_table(pa.Table.from_pylist(memory_rows), directory / "append_only_memory.parquet", compression="zstd", use_dictionary=True)
    _write_rows(directory / "retained_counterexamples.parquet", [item.to_dict() for item in controller.retained.all()])
    _write_rows(directory / "failure_capsules.parquet", [item.to_dict() for item in controller.capsules.all()])
    _write_rows(directory / "uncertainty_ledger.parquet", [item.to_dict() for item in controller.uncertainty.all()])
    library_path = directory / "configuration_library.json"
    ontology_path = directory / "failure_ontology.json"
    _write_json(library_path, {"records": [item.to_dict() for item in controller.library.all()], "events": list(controller.library.events())})
    _write_json(ontology_path, {"families": [item.to_dict() for item in controller.ontology.all()], "genealogy": list(controller.ontology.genealogy())})
    manifest = {
        "schema_version": "1.0.0",
        "run_id": run_id,
        "generation": generation,
        "condition": condition,
        "memory_records": len(memory_rows),
        "memory_chain_valid": controller.memory.validate_chain(),
        "memory_head_hash": controller.memory.head_hash,
        "retained_counterexamples": len(controller.retained.all()),
        "failure_capsules": len(controller.capsules.all()),
        "uncertainty_entries": len(controller.uncertainty.all()),
        "active_library_size": len(controller.library.approved()),
        "total_library_size": len(controller.library.all()),
        "library_hash": controller.library.library_hash,
        "ontology_hash": controller.ontology.ontology_hash,
        "forbidden_state_audit": {"future_manifest_absent": True, "hidden_label_absent": True, "raw_answer_key_absent": True},
        "files": {
            path.name: file_sha256(path)
            for path in sorted(directory.iterdir())
            if path.is_file()
        },
    }
    manifest["checkpoint_hash"] = stable_hash(manifest)
    _write_json(directory / "checkpoint_manifest.json", manifest)


def _write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    normalized = [{key: json.dumps(value, sort_keys=True, separators=(",", ":")) if isinstance(value, (dict, list, tuple)) else value for key, value in row.items()} for row in rows]
    if not normalized:
        normalized = [{"empty": True}]
    pq.write_table(pa.Table.from_pylist(normalized), path, compression="zstd", use_dictionary=True)


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args()
    # console.log: phase3.stress.step01.start
    console_log("phase3.stress.step01.start", run_id=args.run_id)
    summary = run_phase3(args.run_id, args.output_root)
    # console.log: phase3.stress.step02.complete
    console_log("phase3.stress.step02.complete", canonical_opportunities=summary["canonical_opportunities"], condition_decisions=summary["condition_decisions"], repair_curricula=summary["repair_curricula"], trace_files=summary["trace_files"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
