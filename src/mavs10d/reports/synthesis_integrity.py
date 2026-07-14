"""Factual Markdown reporting for Phase 6 synthesis integrity."""

from __future__ import annotations

from typing import Any


def render_report(metrics: dict[str, Any], audit: dict[str, Any]) -> str:
    lines = [
        "# Phase 6 Synthesis Integrity Report",
        "",
        "This report covers executable diagnostic synthesis integrity only. It makes no Phase 7 runtime or Phase 9 claim-bank claim.",
        "",
        "## Candidate lifecycle",
        "",
        f"- Proposed: {metrics['proposed']}",
        f"- Promoted: {metrics['promoted']}",
        f"- Integrity rejected: {metrics['integrity_rejected']}",
        f"- Certification rejected: {metrics['certification_rejected']}",
        f"- Quarantined: {metrics['quarantined']}",
        f"- Deterministically replayed: {metrics['replayed']}",
        f"- Lifecycle reconciliation: {'PASS' if metrics['reconciled'] else 'FAIL'}",
        "",
        "## Independent audit",
        "",
        f"- Status: {audit.get('status', 'PENDING')}",
        f"- Findings: {audit.get('finding_count', 'not yet computed')}",
        "",
    ]
    return "\n".join(lines)


def render_claims(metrics: dict[str, Any], audit_status: str) -> str:
    return "\n".join([
        "# Phase 6 Claims",
        "",
        "Claim scope: executable diagnostic synthesis and anti-gaming integrity only.",
        "",
        f"- Candidate lifecycle: {metrics['proposed']} proposed, {metrics['promoted']} promoted, {metrics['integrity_rejected']} integrity rejected, {metrics['certification_rejected']} certification rejected, {metrics['quarantined']} quarantined.",
        f"- Independent Phase 6 audit status: {audit_status}.",
        "- No live Perception-Closure runtime, multi-generation improvement, or final blind-bank claim is made.",
        "",
    ])
