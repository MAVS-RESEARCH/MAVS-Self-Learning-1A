from __future__ import annotations

import sys
from pathlib import Path

import pytest

from mavs10d.core.runtime import PerceptionClosureRuntime


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from compile_phase7_microbenchmarks import compile_case  # noqa: E402
from phase7_common import load_yaml  # noqa: E402


@pytest.fixture()
def runtime() -> PerceptionClosureRuntime:
    return PerceptionClosureRuntime(load_yaml("configs/perception_closure_v04/runtime.yaml"))


@pytest.fixture()
def case_factory():
    return compile_case
