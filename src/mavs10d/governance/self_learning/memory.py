"""Append-only governance memory, retained counterexamples, capsules, and uncertainty."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping

from mavs10d.core.hashing import stable_hash


FORBIDDEN_PREFEEDBACK_FIELDS = frozenset(
    {"unsafe", "correct_action", "hidden_repair_mechanism", "expected_operation", "feedback_poisoned"}
)


@dataclass(frozen=True)
class MemoryRecord:
    sequence: int
    event_type: str
    payload: Mapping[str, Any]
    previous_hash: str
    record_hash: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AppendOnlyTraceMemory:
    """Hash-chained event memory; outcome completion never mutates decision records."""

    def __init__(self) -> None:
        self._records: list[MemoryRecord] = []
        self._decision_ids: set[str] = set()

    def append_decision(self, payload: Mapping[str, Any]) -> MemoryRecord:
        if FORBIDDEN_PREFEEDBACK_FIELDS & set(payload):
            raise ValueError("Pre-feedback decision records cannot contain evaluator-only fields.")
        trace_id = str(payload.get("trace_id", ""))
        if not trace_id or trace_id in self._decision_ids:
            raise ValueError("Decision trace IDs must be nonempty and unique.")
        record = self._append("decision", payload)
        self._decision_ids.add(trace_id)
        return record

    def append_outcome(self, trace_id: str, payload: Mapping[str, Any]) -> MemoryRecord:
        if trace_id not in self._decision_ids:
            raise ValueError("Outcome completion must reference an existing decision trace.")
        return self._append("outcome_completion", {"trace_id": trace_id, **dict(payload)})

    def append_learning(self, event_type: str, payload: Mapping[str, Any]) -> MemoryRecord:
        if event_type not in {
            "learning_event",
            "proposal",
            "certification",
            "promotion",
            "rejection",
            "quarantine",
            "rollback",
            "consolidation",
        }:
            raise ValueError(f"Unsupported governance-memory event type: {event_type}")
        return self._append(event_type, payload)

    def _append(self, event_type: str, payload: Mapping[str, Any]) -> MemoryRecord:
        sequence = len(self._records)
        previous_hash = self._records[-1].record_hash if self._records else "0" * 64
        body = {
            "sequence": sequence,
            "event_type": event_type,
            "payload": dict(payload),
            "previous_hash": previous_hash,
        }
        record = MemoryRecord(sequence, event_type, dict(payload), previous_hash, stable_hash(body))
        self._records.append(record)
        return record

    def validate_chain(self) -> bool:
        previous = "0" * 64
        for index, record in enumerate(self._records):
            body = {
                "sequence": index,
                "event_type": record.event_type,
                "payload": dict(record.payload),
                "previous_hash": previous,
            }
            if record.sequence != index or record.previous_hash != previous or record.record_hash != stable_hash(body):
                return False
            previous = record.record_hash
        return True

    @property
    def records(self) -> tuple[MemoryRecord, ...]:
        return tuple(self._records)

    @property
    def head_hash(self) -> str:
        return self._records[-1].record_hash if self._records else "0" * 64


@dataclass(frozen=True)
class RetainedCounterexample:
    counterexample_id: str
    trace_id: str
    family_id: str
    expected_action: str
    observed_action: str
    visible_signature: Mapping[str, float | str | bool]
    protected: bool
    superseded_by: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class RetainedCounterexampleBank:
    def __init__(self) -> None:
        self._items: dict[str, RetainedCounterexample] = {}
        self._context_index: dict[tuple[Any, ...], list[str]] = {}

    def add(self, item: RetainedCounterexample) -> None:
        if item.counterexample_id in self._items:
            if self._items[item.counterexample_id] != item:
                raise ValueError("Retained counterexamples are immutable.")
            return
        self._items[item.counterexample_id] = item
        key = _contrast_context_key(item.visible_signature)
        self._context_index.setdefault(key, []).append(item.counterexample_id)

    def supersede(self, counterexample_id: str, replacement_id: str) -> None:
        current = self._items[counterexample_id]
        if replacement_id not in self._items:
            raise ValueError("A retained counterexample can only be superseded by an existing replacement.")
        self._items[counterexample_id] = RetainedCounterexample(**{**current.to_dict(), "superseded_by": replacement_id})

    def active(self) -> tuple[RetainedCounterexample, ...]:
        return tuple(item for item in self._items.values() if item.superseded_by is None)

    def all(self) -> tuple[RetainedCounterexample, ...]:
        return tuple(self._items.values())

    def contrast_candidates(self, target: Mapping[str, Any]) -> tuple[RetainedCounterexample, ...]:
        """Return the exact validated context stratum, with global fallback only when empty."""

        identifiers = self._context_index.get(_contrast_context_key(target), ())
        if identifiers:
            return tuple(self._items[identifier] for identifier in identifiers)
        return self.all()

    @property
    def bank_hash(self) -> str:
        return stable_hash([item.to_dict() for item in self._items.values()])


@dataclass(frozen=True)
class FailureCapsule:
    capsule_id: str
    curriculum_id: str
    family_id: str
    trigger: str
    trace_ids: tuple[str, ...]
    context: Mapping[str, Any]
    observable_signature: Mapping[str, float | str | bool]
    expected_action: str
    observed_action: str
    severity: float
    feedback_provenance: str
    feedback_reliability: float
    minimal_contrasts: Mapping[str, str]
    attribution: Mapping[str, float]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class FailureCapsuleStore:
    def __init__(self) -> None:
        self._capsules: dict[str, FailureCapsule] = {}

    def add(self, capsule: FailureCapsule) -> None:
        if capsule.capsule_id in self._capsules and self._capsules[capsule.capsule_id] != capsule:
            raise ValueError("Failure capsules are immutable.")
        self._capsules[capsule.capsule_id] = capsule

    def by_curriculum(self, curriculum_id: str) -> tuple[FailureCapsule, ...]:
        return tuple(item for item in self._capsules.values() if item.curriculum_id == curriculum_id)

    def all(self) -> tuple[FailureCapsule, ...]:
        return tuple(self._capsules.values())


@dataclass(frozen=True)
class UncertaintyEntry:
    entry_id: str
    curriculum_id: str
    trace_ids: tuple[str, ...]
    reason_codes: tuple[str, ...]
    missing_evidence: tuple[str, ...]
    novelty_score: float
    selector_applicability: float
    status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class UncertaintyLedger:
    def __init__(self) -> None:
        self._entries: list[UncertaintyEntry] = []

    def append(self, entry: UncertaintyEntry) -> None:
        if entry.status not in {"open", "contained", "resolved", "quarantined"}:
            raise ValueError("Uncertainty status is not recognized.")
        self._entries.append(entry)

    def all(self) -> tuple[UncertaintyEntry, ...]:
        return tuple(self._entries)


def nearest_contrasts(
    target: Mapping[str, float | str | bool],
    candidates: Iterable[RetainedCounterexample],
) -> dict[str, str]:
    """Return nearest correct-safe, correct-unsafe, FRR, UAR, and escalation traces."""

    buckets: dict[str, tuple[float, str]] = {}
    for item in candidates:
        if item.expected_action == item.observed_action == "accept":
            category = "correct_safe"
        elif item.expected_action == item.observed_action == "reject":
            category = "correct_unsafe"
        elif item.expected_action == "accept" and item.observed_action == "reject":
            category = "false_rejection"
        elif item.expected_action == "reject" and item.observed_action == "accept":
            category = "unsafe_acceptance"
        else:
            category = "escalation"
        distance = _visible_distance(target, item.visible_signature)
        if category not in buckets or distance < buckets[category][0]:
            buckets[category] = (distance, item.trace_id)
    return {category: trace_id for category, (_, trace_id) in sorted(buckets.items())}


def _visible_distance(left: Mapping[str, Any], right: Mapping[str, Any]) -> float:
    shared = set(left) & set(right)
    if not shared:
        return 1.0
    total = 0.0
    for key in shared:
        a, b = left[key], right[key]
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            total += min(1.0, abs(float(a) - float(b)))
        else:
            total += float(a != b)
    return total / len(shared)


def _contrast_context_key(signature: Mapping[str, Any]) -> tuple[Any, ...]:
    return tuple(signature.get(key) for key in ("generation", "curriculum_id", "domain", "target_context"))
