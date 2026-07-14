from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
PHASE7_ROOT = REPO_ROOT / "results" / "perception_closure_v04" / "phase7" / "phase7_authoritative_20260714"


@pytest.fixture(scope="session")
def phase7_cases():
    return [json.loads(line) for line in (PHASE7_ROOT / "manifests" / "runtime_cases.jsonl").read_text(encoding="utf-8").splitlines() if line]


@pytest.fixture(scope="session")
def phase7_truth():
    return pd.read_parquet(PHASE7_ROOT / "manifests" / "auditor_truth.parquet")
