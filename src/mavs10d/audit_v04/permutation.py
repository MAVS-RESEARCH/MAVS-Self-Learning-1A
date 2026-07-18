"""Metadata and ordering permutation challenges over fixed executable evidence."""

from __future__ import annotations

import random
from typing import Any

import pandas as pd

from .certification import recompute_gate_values
from .common import REPO_ROOT, config, read_json, result_root, stable_hash, verify_frozen_input_index, write_json


def run_permutation_challenge() -> dict[str, Any]:
    verify_frozen_input_index()
    seed = int(config()["audit_sample"]["seed"])
    randomizer = random.Random(seed)
    p6 = REPO_ROOT / config()["inputs"]["phase6"]
    directories = sorted(path for path in (p6 / "candidates").iterdir() if path.is_dir())
    shuffled_names = [path.name for path in directories]
    randomizer.shuffle(shuffled_names)
    operation_labels = [read_json(path / "candidate.json")["lineage"]["operation"] for path in directories]
    shuffled_operations = operation_labels[:]
    randomizer.shuffle(shuffled_operations)
    candidate_order = list(range(len(directories)))
    randomizer.shuffle(candidate_order)
    comparisons: list[dict[str, Any]] = []
    baseline_vectors: list[tuple[str, tuple[tuple[str, float, bool], ...]]] = []
    permuted_vectors: list[tuple[str, tuple[tuple[str, float, bool], ...]]] = []
    for index, directory in enumerate(directories):
        candidate = read_json(directory / "candidate.json")
        trace = pd.read_parquet(directory / "certification_trace.parquet")
        witness = read_json(directory / "perception_extension_witness.json")
        baseline = recompute_gate_values(candidate, trace, witness)
        permuted = dict(candidate)
        permuted["candidate_id"] = shuffled_names[index]
        permuted["candidate_name"] = f"permuted-{index:03d}"
        permuted["lineage"] = {**candidate["lineage"], "operation": shuffled_operations[index], "curriculum": f"curriculum-{(index + 7) % len(directories)}", "generation": f"G{(index % 3) + 1}"}
        challenged = recompute_gate_values(permuted, trace, witness)
        baseline_vector = tuple((gate, baseline[gate][0], baseline[gate][1]) for gate in sorted(baseline))
        challenged_vector = tuple((gate, challenged[gate][0], challenged[gate][1]) for gate in sorted(challenged))
        baseline_vectors.append((candidate["candidate_id"], baseline_vector))
        permuted_vectors.append((candidate["candidate_id"], challenged_vector))
        comparisons.append({"candidate_id": candidate["candidate_id"], "permuted_name": shuffled_names[index], "permuted_operation": shuffled_operations[index], "outcome_invariant": baseline_vector == challenged_vector})
    reordered = [permuted_vectors[index] for index in candidate_order]
    manifest = {
        "schema_version": "1.0.0", "seed": seed,
        "candidate_name_permutation": dict(zip([path.name for path in directories], shuffled_names)),
        "operation_label_permutation": dict(zip([path.name for path in directories], shuffled_operations)),
        "curriculum_labels_permuted": True, "generation_labels_permuted": True,
        "candidate_order": candidate_order, "executable_artifacts_held_fixed": True,
        "baseline_multiset_sha256": stable_hash(sorted(baseline_vectors)),
        "permuted_multiset_sha256": stable_hash(sorted(reordered)),
    }
    outcome = {
        "schema_version": "1.0.0", "candidate_count": len(comparisons),
        "changed_gate_or_decision_count": sum(not item["outcome_invariant"] for item in comparisons),
        "comparisons": comparisons,
        "status": "PASS" if all(item["outcome_invariant"] for item in comparisons) else "FAIL",
    }
    write_json(result_root() / "permutation" / "challenge_manifest.json", manifest)
    write_json(result_root() / "permutation" / "outcome_comparison.json", outcome)
    return outcome

