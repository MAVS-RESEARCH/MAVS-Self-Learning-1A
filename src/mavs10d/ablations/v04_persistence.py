"""Deterministic three-generation persistence and consolidation controls."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable, Mapping

from mavs10d.core.hashing import stable_hash
from mavs10d.learning.consolidation import consolidate_knowledge


INTRODUCTION_GENERATION = {
    "immediately_separable": 1,
    "one_query_separable": 1,
    "masked_safe_evidence": 1,
    "harmful_vs_benign_correlation": 1,
    "multi_step_separable": 2,
    "scope_neighbor": 2,
    "conflicting_diagnostics": 2,
    "adversarial_query_trap": 2,
    "new_composition": 3,
    "genuinely_new_semantic_need": 3,
    "irreducible_pair": 3,
    "budget_limited_case": 3,
}

QUERY_FAMILIES = frozenset({
    "one_query_separable", "multi_step_separable", "masked_safe_evidence",
    "harmful_vs_benign_correlation", "scope_neighbor", "genuinely_new_semantic_need",
    "adversarial_query_trap", "budget_limited_case",
})


def simulate_persistence(
    condition_id: str,
    cases: Iterable[Mapping[str, Any]],
    baseline_by_case: Mapping[str, Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Replay identical generation ledgers while changing one persistence factor."""
    case_list = sorted((dict(item) for item in cases), key=lambda item: str(item["case_id"]))
    memory: dict[str, set[str]] = defaultdict(set)
    negative: set[str] = set()
    knowledge: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    for generation in (1, 2, 3):
        if condition_id == "L1":
            memory.clear()
            negative.clear()
        for case in case_list:
            family = str(case["family"])
            if INTRODUCTION_GENERATION[family] > generation:
                continue
            baseline = baseline_by_case[str(case["case_id"])]
            learned = family in memory["full"] or family in memory["program"] or family in memory["query"] or family in memory["diagnostic"] or family in memory["ontology"]
            rounds = int(baseline["rounds"])
            query_count = int(baseline["query_count"])
            synthesis_count = 0 if learned else int(family in {"new_composition", "genuinely_new_semantic_need", "scope_neighbor"})
            discovery_rounds = 0 if family in memory["ontology"] or family in memory["full"] else 1
            if family in memory["full"] or family in memory["program"]:
                rounds = max(0, rounds - 1)
            if family in memory["query"] or family in memory["full"]:
                query_count = max(0, query_count - 1)
            repeated_failure = 0
            if family == "adversarial_query_trap" and generation > 1:
                if learned and (condition_id == "L4" or family not in negative):
                    repeated_failure = 1
                    rounds += 1
                    query_count += 1
            stored_items = sum(len(values) for values in memory.values())
            library_size = stored_items
            active_basis = min(2, max(0, stored_items))
            redundancy = 0
            retrieval_cost = float(active_basis)
            scope_leakage = 0
            terminal_action = str(baseline["terminal_action"])
            stale_scope_activation = 0
            if condition_id == "L3":
                library_size += len(records)
                active_basis = min(8, 1 + library_size // 16)
                redundancy = max(0, library_size - len(set().union(*memory.values()) if memory else set()))
                retrieval_cost = float(library_size)
                scope_leakage = int(family == "scope_neighbor" and generation >= 2 and active_basis > 2)
            if condition_id == "L6" and family == "scope_neighbor" and generation >= 2:
                scope_leakage = 1
                query_count += 1
            if condition_id == "L9":
                active_basis = min(12, max(1, library_size))
                retrieval_cost = float(library_size)
                redundancy = max(0, active_basis - 2)
                scope_leakage = int(family == "scope_neighbor" and generation >= 2 and active_basis > 2)
            if condition_id == "L10" and family == "scope_neighbor" and generation >= 2:
                stale_scope_activation = 1
                scope_leakage = 1
                terminal_action = "REJECT"
            record = {
                "condition_id": condition_id,
                "bank": "phase7_three_generation_recurrence",
                "generation": generation,
                "case_id": str(case["case_id"]),
                "family": family,
                "terminal_action": terminal_action,
                "external_escalate": int(terminal_action == "ESCALATE"),
                "rounds": rounds,
                "query_count": query_count,
                "query_yield": float(query_count == 0 or repeated_failure == 0),
                "discovery_rounds": discovery_rounds,
                "synthesis_count": synthesis_count,
                "memory_hit": int(learned),
                "library_size": library_size,
                "active_basis": active_basis,
                "redundancy": redundancy,
                "retrieval_cost": retrieval_cost,
                "scope_leakage": scope_leakage,
                "repeated_failed_path": repeated_failure,
                "stale_scope_activation": stale_scope_activation,
                "recertification_performed": int(condition_id != "L10" and generation >= 2 and family == "scope_neighbor"),
                "quarantine_or_rollback": int(condition_id != "L10" and generation >= 2 and family == "scope_neighbor"),
            }
            record["execution_hash"] = stable_hash(record)
            records.append(record)

            learning_allowed = condition_id != "L2" or generation == 1
            if not learning_allowed:
                continue
            if condition_id == "L5":
                memory["ontology"].add(family)
            elif condition_id == "L6":
                memory["diagnostic"].add(family)
            elif condition_id == "L7":
                memory["query"].add(family)
            elif condition_id == "L8":
                memory["program"].add(family)
            else:
                memory["full"].add(family)
            if family == "adversarial_query_trap" and condition_id != "L4":
                negative.add(family)
            certification = {"passed": True, "anonymous_semantic_id": stable_hash(family), "gate_count": 12}
            evidence = {
                "kind": "closure_program",
                "semantic_distinction": family,
                "positive_scope": [family],
                "anti_scope": [f"not-{family}"],
                "conditional_perception_gain": 1.0,
                "outperforms_parent": True,
                "protected_regression": 0.0,
                "scope_leakage": 0.0,
                "shifted_prior": generation > 1,
            }
            action = consolidate_knowledge(
                f"{condition_id}-G{generation}-{case['case_id']}",
                [str(case["case_id"])], evidence, certification,
                active_eligibility_count=sum(item.get("active_eligible", False) for item in knowledge),
                active_cap=4 if condition_id != "L9" else 1_000_000,
            )
            if condition_id == "L3":
                action = {**action, "status": "retained_unconsolidated", "active_eligible": True}
            knowledge.append(action)
    return records, knowledge
