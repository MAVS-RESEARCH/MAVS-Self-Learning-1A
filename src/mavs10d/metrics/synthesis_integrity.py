"""Phase 6 integrity metrics and exact lifecycle reconciliation."""

from __future__ import annotations

from collections import Counter
from typing import Any


def lifecycle_metrics(records: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(record["lifecycle"] for record in records)
    proposed = len(records)
    terminal = sum(counts[name] for name in ("integrity_rejected", "certification_rejected", "quarantined", "promoted"))
    return {
        "proposed": proposed,
        "integrity_rejected": counts["integrity_rejected"],
        "certification_rejected": counts["certification_rejected"],
        "quarantined": counts["quarantined"],
        "promoted": counts["promoted"],
        "replayed": sum(bool(record.get("replay_passed")) for record in records),
        "reconciled": proposed == terminal,
    }


def phase9_integrity_metrics(traces: "Any") -> dict[str, Any]:
    """Summarize serialized synthesis/certification continuity without name semantics."""

    return {
        "canonical_ast_count": int(traces["canonical_ast_count"].max()),
        "template_count": int(traces["template_count"].max()),
        "semantic_hash_count": int(traces["semantic_hash_count"].max()),
        "behavioral_equivalence_classes": int(traces["behavioral_class_count"].max()),
        "constant_count": int(traces["constant_count"].sum()), "noop_count": int(traces["noop_count"].sum()),
        "name_only_count": int(traces["name_only_count"].sum()), "parent_identical_count": int(traces["parent_identical_count"].sum()),
        "operation_noncompliance_count": int((~traces["operation_compliant"].astype(bool)).sum()),
        "search_provenance_incomplete_count": int((~traces["search_provenance_complete"].astype(bool)).sum()),
        "independent_gate_failure_count": int((~traces["phase6_gate_vector_passed"].astype(bool)).sum()),
        "certifier_blindness_failure_count": int((~traces["certifier_blind"].astype(bool)).sum()),
        "permutation_failure_count": int((~traces["permutation_invariant"].astype(bool)).sum()),
        "witness_reproduction_failure_count": int((~traces["witness_reproduced"].astype(bool)).sum()),
        "firewall_attack_detected_count": int(traces["firewall_attack_detected"].astype(bool).sum()),
    }
