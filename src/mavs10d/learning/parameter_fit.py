"""Real parameter search with complete lexicographic provenance."""

from __future__ import annotations

from typing import Any

import pandas as pd

from mavs10d.learning.structure_search import objective_vector


PARAMETER_RANGES: dict[str, tuple[float, ...]] = {
    "threshold": (0.25, 0.35, 0.45, 0.55, 0.65, 0.75),
    "weight": (0.6, 0.8, 1.0, 1.2, 1.4),
    "availability_floor": (0.25, 0.5, 0.75),
    "interaction": (0.25, 0.5, 0.75),
    "persistence_floor": (0.25, 0.5, 0.75),
    "masking_floor": (0.25, 0.5, 0.75),
    "trust_floor": (0.17, 0.25, 0.5, 0.75),
    "safe_ceiling": (0.25, 0.5, 0.75),
    "scope_lower": (0.15, 0.25, 0.35),
    "scope_upper": (0.65, 0.75, 0.85),
    "anti_scope_upper": (0.05, 0.10, 0.15),
}


def fit_parameters(candidate_id: str, ast: dict[str, Any], initial: dict[str, float], development: pd.DataFrame, seed: int, maximum_trials: int = 27) -> tuple[dict[str, float], list[dict[str, Any]]]:
    """Execute bounded one-factor and joint trials and select the lexicographic optimum."""
    referenced = sorted(_parameter_names(ast) | {"scope_lower", "anti_scope_upper"})
    search_names = [name for name in referenced if name in PARAMETER_RANGES]
    vectors: list[dict[str, float]] = [dict(initial)]
    for name in search_names:
        for value in PARAMETER_RANGES[name]:
            vector = dict(initial)
            vector[name] = value
            if vector not in vectors:
                vectors.append(vector)
    offset = 1
    while len(vectors) < maximum_trials and offset <= maximum_trials * 4:
        vector = dict(initial)
        for index, name in enumerate(search_names):
            values = PARAMETER_RANGES[name]
            vector[name] = values[(offset + index) % len(values)]
        if vector not in vectors:
            vectors.append(vector)
        offset += 1
    traces: list[dict[str, Any]] = []
    for trial, vector in enumerate(vectors[:maximum_trials]):
        objective = objective_vector(ast, vector, development)
        traces.append({"candidate_id": candidate_id, "trial": trial, "parameters": vector, "ranges": {name: list(PARAMETER_RANGES[name]) for name in search_names}, "split": "development", "seed": seed + trial, "objective_vector": objective, "protected_constraints_passed": objective[0] <= 0.35 and objective[1] <= 0.35, "selected": False, "selection_rationale": "not_selected"})
    if not traces:
        raise RuntimeError("Parameter search executed zero trials.")
    eligible = [index for index, trace in enumerate(traces) if trace["protected_constraints_passed"]] or list(range(len(traces)))
    winner = min(eligible, key=lambda index: tuple(traces[index]["objective_vector"]))
    traces[winner]["selected"] = True
    traces[winner]["selection_rationale"] = "lexicographic_minimum_over_executed_trials"
    return dict(traces[winner]["parameters"]), traces


def _parameter_names(node: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    if node.get("op") == "parameter":
        names.add(str(node["name"]))
    for child in node.get("children", []):
        names.update(_parameter_names(child))
    for key in ("left", "right"):
        if isinstance(node.get(key), dict):
            names.update(_parameter_names(node[key]))
    return names
