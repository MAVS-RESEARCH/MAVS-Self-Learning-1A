"""Validate Track A/B separation, hidden-field taint, and immutable bank seals."""

from __future__ import annotations

import argparse

import pandas as pd

from mavs10d.core.hashing import file_sha256
from mavs10d.revalidation.banks import hidden_fields
from phase9_common import PHASE9_ROOT, read_json, track_root, write_json


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--track", required=True); args = parser.parse_args()
    root = track_root(args.track); findings: list[dict[str, object]] = []
    seal = read_json(PHASE9_ROOT / "BANKS_SEALED.json")
    for generation in (1, 2, 3):
        manifest = read_json(root / f"manifests/generation_{generation}/generation_manifest.json")
        public_path = root / f"manifests/generation_{generation}/public_ledger.parquet"
        public = pd.read_parquet(public_path)
        overlap = sorted(set(public.columns) & hidden_fields())
        if overlap: findings.append({"gate": "public_hidden_overlap", "generation": generation, "fields": overlap})
        if file_sha256(public_path) != manifest["public_ledger_sha256"]: findings.append({"gate": "post_seal_bank_change", "generation": generation})
        response = pd.read_parquet(root / f"manifests/generation_{generation}/released_query_responses.parquet")
        allowed = {"opportunity_id", "query_response", "response_signature"}
        if set(response.columns) != allowed: findings.append({"gate": "response_field_contract", "generation": generation, "fields": sorted(response.columns)})
        release = read_json(root / f"integrity/generation_{generation}_evaluator_release.json")
        if not release["passed"] or release["forbidden_truth_fields_released"]: findings.append({"gate": "evaluator_release", "generation": generation})
        oracle = pd.read_parquet(root / f"integrity/oracle_quarantine/generation_{generation}/oracle_actions.parquet")
        if set(oracle.columns) != {"opportunity_id", "oracle_action", "oracle_signature"}: findings.append({"gate": "oracle_quarantine", "generation": generation})
    if args.track == "blind_bank":
        overlap = read_json(root / "integrity/preexecution_overlap_report.json")
        if not overlap["passed"]: findings.append({"gate": "blind_overlap", "checks": overlap["checks"]})
    report = {"schema_version": "1.0.0", "track_id": args.track, "bank_seal_signature": seal["signature"], "findings": findings, "finding_count": len(findings), "status": "PASS" if not findings else "FAIL"}
    write_json(root / "integrity/hidden_field_audit.json", report | {"passed": not findings})
    if findings: raise RuntimeError(f"Phase 9 firewall failed: {findings}")
    # console.log: phase9.firewall.complete
    print(f'{{"event":"phase9.firewall.complete","track":"{args.track}","findings":0}}')


if __name__ == "__main__": main()
