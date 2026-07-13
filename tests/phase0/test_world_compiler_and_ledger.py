from __future__ import annotations

import hashlib
import random
from pathlib import Path

import numpy as np
import pytest
import yaml

from mavs10d.core.hashing import file_sha256, stable_hash
from mavs10d.core.seeds import HierarchicalSeeds
from mavs10d.envs.world_compiler import IndependentReferenceCompiler, InheritedStaticCompiler, RandomizedWorldCompiler
from mavs10d.envs.world_ledger import ManifestSigner, public_ledger_rows, verify_signed_manifest, write_generation_ledger


DEFAULTS = yaml.safe_load(Path("configs/worlds/generator_defaults.yaml").read_text(encoding="utf-8"))


def test_hierarchical_seeds_are_deterministic_and_do_not_mutate_global_rng() -> None:
    random.seed(91)
    np.random.seed(92)
    python_before = random.getstate()
    numpy_before = np.random.get_state()
    seeds = HierarchicalSeeds(100000)
    first = seeds.derive(generation=1, world=2, episode=3, step=4, method=5)
    second = seeds.derive(generation=1, world=2, episode=3, step=4, method=5)
    assert first == second
    assert random.getstate() == python_before
    numpy_after = np.random.get_state()
    assert numpy_after[0] == numpy_before[0]
    assert np.array_equal(numpy_after[1], numpy_before[1])


def test_compiler_enforces_counts_horizons_and_visible_hidden_identity() -> None:
    compiled = RandomizedWorldCompiler(100000, DEFAULTS).compile_partition(
        generation=1, partition="generated_world", decisions=2000, world_offset=0
    )
    compiled.validate(2000)
    assert sum(world.horizon for world in compiled.worlds) == 2000
    assert all(80 <= world.horizon <= 320 for world in compiled.worlds)
    assert len({row.opportunity_id for row in compiled.visible_opportunities}) == 2000


def test_independent_generator_uses_disjoint_implementation_and_output() -> None:
    primary = RandomizedWorldCompiler(100000, DEFAULTS).compile_partition(
        generation=1, partition="holdout", decisions=400, world_offset=0
    )
    independent = IndependentReferenceCompiler(100000, DEFAULTS).compile_partition(
        generation=1, partition="holdout", decisions=400, world_offset=0
    )
    assert primary.worlds[0].generator_version != independent.worlds[0].generator_version
    assert stable_hash([row.to_dict() for row in primary.visible_opportunities]) != stable_hash(
        [row.to_dict() for row in independent.visible_opportunities]
    )


def test_inherited_static_allocation_executes_chapter10d_adapter() -> None:
    compiled = InheritedStaticCompiler(100000, DEFAULTS).compile_partition(
        generation=1, partition="inherited_static", decisions=100, world_offset=0
    )
    assert compiled.worlds[0].generator_version.startswith("chapter10d_static_accuracy_adapter")
    assert all(row.domain == "static_accuracy_adapter" for row in compiled.visible_opportunities)
    assert all(row.feedback_release_step == row.seed_tuple.step * 0 + index for index, row in enumerate(compiled.hidden_opportunities))


def test_ledger_is_byte_deterministic_signed_and_hidden_fields_are_absent(tmp_path: Path) -> None:
    compiled = RandomizedWorldCompiler(100000, DEFAULTS).compile_partition(
        generation=1, partition="test", decisions=400, world_offset=0
    )
    signer = ManifestSigner(hashlib.sha256(b"test-key").digest(), "test")
    kwargs = dict(
        generation=1,
        partitions=(("test", compiled),),
        config_hashes={"test": "0" * 64},
        generator_package_hash="1" * 64,
        signer=signer,
    )
    first = write_generation_ledger(output_directory=tmp_path / "first", **kwargs)
    second = write_generation_ledger(output_directory=tmp_path / "second", **kwargs)
    assert file_sha256(first.ledger_path) == file_sha256(second.ledger_path)
    assert verify_signed_manifest(first.manifest_path, signer)["opportunity_count"] == 400
    rows = public_ledger_rows(first.ledger_path)
    assert "unsafe_label" not in rows[0]


def test_manifest_tampering_is_detected(tmp_path: Path) -> None:
    signer = ManifestSigner(hashlib.sha256(b"test-key").digest(), "test")
    path = tmp_path / "manifest.json"
    path.write_text('{"body":{"value":1},"signature":"' + signer.sign({"value": 1}) + '"}', encoding="utf-8")
    assert verify_signed_manifest(path, signer) == {"value": 1}
    path.write_text(path.read_text(encoding="utf-8").replace('"value":1', '"value":2'), encoding="utf-8")
    with pytest.raises(ValueError, match="signature"):
        verify_signed_manifest(path, signer)
