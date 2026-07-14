"""Smallest nonredundant, scope-certified situation-specific programs."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from mavs10d.core.hashing import stable_hash


def build_program(
    case_id: str,
    round_index: int,
    selected_action: Mapping[str, Any],
    candidate_actions: Iterable[Mapping[str, Any]],
    max_basis: int,
) -> dict[str, Any]:
    if not selected_action.get("positive_scope", False) or selected_action.get("anti_scope", False):
        raise PermissionError("A case program requires a positive activation proof and absent anti-scope.")
    primitives = list(dict.fromkeys(map(str, selected_action.get("primitive_ids", [selected_action["action_id"]]))))
    if len(primitives) > max_basis:
        raise RuntimeError("Selected case program exceeds the sparse influential-basis limit.")
    behavioral = str(selected_action.get("behavioral_id", selected_action["action_id"]))
    redundant = sorted(
        str(item["action_id"])
        for item in candidate_actions
        if str(item["action_id"]) != str(selected_action["action_id"])
        and str(item.get("behavioral_id", item["action_id"])) == behavioral
    )
    interaction_ids = list(map(str, selected_action.get("interaction_certificate_ids", [])))
    payload = {
        "program_id": f"PG-{stable_hash({'case_id': case_id, 'round': round_index, 'action': selected_action['action_id']})[:20]}",
        "case_id": case_id,
        "round_index": round_index,
        "action_ids": [str(selected_action["action_id"])],
        "influential_basis": primitives,
        "redundant_suppressed": redundant,
        "scope_certified": True,
        "interaction_certificates": interaction_ids,
        "primary_causal_family": str(selected_action.get("causal_family", "registered_case_family")),
        "conditional_perception_gain": float(selected_action["expected_contraction"]),
    }
    payload["program_hash"] = stable_hash(payload)
    return payload
