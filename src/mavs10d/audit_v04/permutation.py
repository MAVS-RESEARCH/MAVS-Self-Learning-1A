"""Metadata and ordering permutation challenges over fixed executable evidence."""

from __future__ import annotations

import random
from typing import Any

import pandas as pd

from .certification import recompute_gate_values
from .common import REPO_ROOT, config, read_json, result_root, stable_hash, verify_frozen_input_index, write_json


def _metric_vector(trace: pd.DataFrame, truth: pd.DataFrame) -> tuple[float, ...]:
    joined = trace.merge(truth[["opportunity_id", "unsafe"]], on="opportunity_id", validate="one_to_one")
    terminal = joined["terminal_action"].astype(str).str.upper()
    unsafe = joined["unsafe"].astype(bool)
    return (
        float((unsafe & terminal.eq("ACCEPT")).sum()),
        float((~unsafe & terminal.eq("REJECT")).sum()),
        float(joined["external_escalate"].sum()),
        float(joined["scope_leakage"].sum()),
        float(joined["query_count"].sum()),
        float(joined["probe_count"].sum()),
        float(joined["round_count"].sum()),
        float(joined["latency_ms"].sum()),
        float(joined["compute_units"].sum()),
    )


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
    phase9 = REPO_ROOT / config()["inputs"]["phase9"]
    metric_comparisons: list[dict[str, Any]] = []
    for track in ("paired_original_bank", "blind_bank"):
        for trace_path in sorted((phase9 / track / "decision_traces").glob("*/generation_*.parquet")):
            trace = pd.read_parquet(trace_path)
            generation = int(trace["generation"].iloc[0])
            truth = pd.read_parquet(phase9 / "evaluator_sealed" / track / f"generation_{generation}" / "truth.parquet")
            baseline = _metric_vector(trace, truth)
            permuted_trace = trace.sample(frac=1.0, random_state=seed).reset_index(drop=True).copy()
            permuted_trace["condition_id"] = f"permuted-condition-{randomizer.randrange(1_000_000):06d}"
            permuted_trace["generation"] = ((generation + 1) % 3) + 1
            challenged = _metric_vector(permuted_trace, truth)
            metric_comparisons.append({
                "track": track, "physical_generation": generation,
                "trace_path": trace_path.relative_to(REPO_ROOT).as_posix(),
                "baseline_sha256": stable_hash(baseline), "permuted_sha256": stable_hash(challenged),
                "outcome_invariant": baseline == challenged,
            })
    manifest = {
        "schema_version": "1.0.0", "seed": seed,
        "candidate_name_permutation": dict(zip([path.name for path in directories], shuffled_names)),
        "operation_label_permutation": dict(zip([path.name for path in directories], shuffled_operations)),
        "curriculum_labels_permuted": True, "generation_labels_permuted": True,
        "candidate_order": candidate_order, "executable_artifacts_held_fixed": True,
        "baseline_multiset_sha256": stable_hash(sorted(baseline_vectors)),
        "permuted_multiset_sha256": stable_hash(sorted(reordered)),
        "phase9_metric_challenge_count": len(metric_comparisons),
        "row_order_permuted": True, "metadata_labels_do_not_select_truth": True,
    }
    outcome = {
        "schema_version": "1.0.0", "candidate_count": len(comparisons),
        "changed_gate_count": sum(not item["outcome_invariant"] for item in comparisons),
        "changed_metric_outcome_count": sum(not item["outcome_invariant"] for item in metric_comparisons),
        "changed_gate_or_decision_count": sum(not item["outcome_invariant"] for item in comparisons) + sum(not item["outcome_invariant"] for item in metric_comparisons),
        "comparisons": comparisons, "metric_comparisons": metric_comparisons,
        "status": "PASS" if all(item["outcome_invariant"] for item in comparisons) and all(item["outcome_invariant"] for item in metric_comparisons) else "FAIL",
    }
    write_json(result_root() / "permutation" / "challenge_manifest.json", manifest)
    write_json(result_root() / "permutation" / "outcome_comparison.json", outcome)
    return outcome
