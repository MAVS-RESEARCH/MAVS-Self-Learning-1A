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

