"""Auditable anti-scopes, failed paths, and prohibited interactions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class NegativeKnowledge:
    anti_scopes: set[str] = field(default_factory=set)
    failed_programs: set[str] = field(default_factory=set)
    low_yield_queries: set[str] = field(default_factory=set)
    prohibited_compositions: set[frozenset[str]] = field(default_factory=set)
    failure_signatures: list[dict[str, Any]] = field(default_factory=list)

    def action_block_reason(self, action: dict[str, Any]) -> str | None:
        if action.get("action_id") in self.low_yield_queries:
            return "negative_knowledge_low_yield"
        if action.get("program_id") in self.failed_programs:
            return "negative_knowledge_failed_program"
        primitives = frozenset(map(str, action.get("primitive_ids", [])))
        if primitives and primitives in self.prohibited_compositions:
            return "negative_knowledge_prohibited_composition"
        if any(scope in self.anti_scopes for scope in action.get("scope_ids", [])):
            return "negative_knowledge_anti_scope"
        return None

    def record_low_yield(self, action_id: str, realized_contraction: float) -> None:
        if realized_contraction <= 0.0:
            self.low_yield_queries.add(action_id)

    def record_failure(self, case_id: str, reason: str, action_ids: list[str]) -> None:
        self.failure_signatures.append({"case_id": case_id, "reason": reason, "action_ids": list(action_ids)})

    def to_records(self) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        records.extend({"kind": "anti_scope", "key": item} for item in sorted(self.anti_scopes))
        records.extend({"kind": "failed_program", "key": item} for item in sorted(self.failed_programs))
        records.extend({"kind": "low_yield_query", "key": item} for item in sorted(self.low_yield_queries))
        records.extend({"kind": "prohibited_composition", "key": "|".join(sorted(item))} for item in sorted(self.prohibited_compositions, key=lambda value: sorted(value)))
        records.extend({"kind": "failure_signature", "key": item["case_id"], "detail": item} for item in self.failure_signatures)
        return records
