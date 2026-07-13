from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from mavs10d.envs.world_compiler import RandomizedWorldCompiler
from mavs10d.core.access_control import participant_file_guard
from scripts.run_phase0_stress import _method_functions


def test_visible_contract_does_not_serialize_hidden_fields() -> None:
    defaults = yaml.safe_load(Path("configs/worlds/generator_defaults.yaml").read_text(encoding="utf-8"))
    compiled = RandomizedWorldCompiler(100000, defaults).compile_partition(
        generation=1, partition="leakage", decisions=100, world_offset=0
    )
    forbidden = {"unsafe_label", "hidden_regime", "corruption_families", "feedback_release_step"}
    for row in compiled.visible_opportunities:
        assert forbidden.isdisjoint(row.to_dict())


@pytest.mark.parametrize("method_id", ["accept_all", "reject_all", "escalate_all", "random"])
def test_non_oracle_bounds_execute_without_hidden_payload(method_id: str) -> None:
    visible = {"seed_commitment": "0" * 64}
    assert _method_functions()[method_id](visible, None) in {"accept", "reject", "escalate"}


@pytest.mark.parametrize("method_id", ["oracle_label", "oracle_regime"])
def test_oracle_bounds_fail_closed_without_evaluator_payload(method_id: str) -> None:
    with pytest.raises(PermissionError):
        _method_functions()[method_id]({"seed_commitment": "0" * 64}, None)


def test_participant_file_guard_denies_hidden_manifest_reads(tmp_path: Path) -> None:
    hidden = tmp_path / "hidden_world_manifest.json"
    hidden.write_text('{"hidden":true}', encoding="utf-8")
    with participant_file_guard(hidden):
        with pytest.raises(PermissionError, match="evaluator-only"):
            hidden.read_text(encoding="utf-8")
    assert hidden.read_text(encoding="utf-8") == '{"hidden":true}'
