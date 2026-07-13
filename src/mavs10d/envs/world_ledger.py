"""Immutable Parquet ledgers and signed manifest construction."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

import pyarrow as pa
import pyarrow.parquet as pq

from mavs10d.core.hashing import file_sha256, stable_hash, stable_json_dumps
from mavs10d.envs.world_compiler import CompiledPartition, HiddenOpportunity


@dataclass(frozen=True)
class LedgerArtifacts:
    ledger_path: Path
    hidden_manifest_path: Path
    manifest_path: Path
    ledger_sha256: str
    manifest_sha256: str
    opportunity_count: int


class ManifestSigner:
    """HMAC-SHA256 signer for deterministic Phase 0 integrity manifests."""

    algorithm = "HMAC-SHA256"

    def __init__(self, key: bytes, key_id: str) -> None:
        if len(key) < 32:
            raise ValueError("Manifest signing key must contain at least 32 bytes.")
        self._key = key
        self.key_id = key_id

    def sign(self, payload: Mapping[str, Any]) -> str:
        return hmac.new(
            self._key,
            stable_json_dumps(payload).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def verify(self, payload: Mapping[str, Any], signature: str) -> bool:
        return hmac.compare_digest(self.sign(payload), signature)


def write_generation_ledger(
    *,
    output_directory: Path,
    generation: int,
    partitions: Iterable[tuple[str, CompiledPartition]],
    config_hashes: Mapping[str, str],
    generator_package_hash: str,
    signer: ManifestSigner,
) -> LedgerArtifacts:
    partition_items = tuple(partitions)
    visible_rows: list[dict[str, Any]] = []
    hidden_rows: list[dict[str, Any]] = []
    world_rows: list[dict[str, Any]] = []
    latent_world_rows: list[dict[str, Any]] = []
    partition_counts: dict[str, int] = {}
    for partition_name, compiled in partition_items:
        compiled.validate(len(compiled.visible_opportunities))
        partition_counts[partition_name] = len(compiled.visible_opportunities)
        for row in compiled.visible_opportunities:
            visible_rows.append(
                {
                    **row.to_dict(),
                    "benchmark_partition": partition_name,
                    "visible_regime_features": stable_json_dumps(row.visible_regime_features),
                    "observation": stable_json_dumps(row.observation),
                }
            )
        hidden_rows.extend(
            {**row.to_dict(), "benchmark_partition": partition_name}
            for row in compiled.hidden_opportunities
        )
        world_rows.extend({**world.to_dict(), "benchmark_partition": partition_name} for world in compiled.worlds)
        latent_world_rows.extend(
            {**dict(parameters), "benchmark_partition": partition_name}
            for parameters in compiled.latent_world_parameters
        )
    opportunity_ids = [row["opportunity_id"] for row in visible_rows]
    if len(opportunity_ids) != len(set(opportunity_ids)):
        raise ValueError("Ledger contains duplicate opportunity IDs.")
    output_directory.mkdir(parents=True, exist_ok=True)
    ledger_path = output_directory / "world_ledger.parquet"
    hidden_path = output_directory / "hidden_world_manifest.json"
    manifest_path = output_directory / "generation_manifest.json"
    table = pa.Table.from_pylist(visible_rows)
    _write_parquet_immutable(ledger_path, table)
    hidden_body = {
        "schema_version": "1.0.0",
        "generation": generation,
        "opportunities": hidden_rows,
        "worlds": world_rows,
        "latent_world_parameters": latent_world_rows,
        "opportunity_count": len(hidden_rows),
    }
    hidden_envelope = _signed_envelope(hidden_body, signer)
    _write_json_immutable(hidden_path, hidden_envelope)
    manifest_body = {
        "schema_version": "1.0.0",
        "generation": generation,
        "opportunity_count": len(visible_rows),
        "partition_counts": partition_counts,
        "row_order_sha256": stable_hash(opportunity_ids),
        "schema_sha256": stable_hash(str(table.schema)),
        "ledger_sha256": file_sha256(ledger_path),
        "hidden_manifest_sha256": file_sha256(hidden_path),
        "hidden_parameters_sha256": stable_hash(
            {"opportunities": hidden_rows, "latent_world_parameters": latent_world_rows}
        ),
        "generator_package_sha256": generator_package_hash,
        "config_hashes": dict(sorted(config_hashes.items())),
        "signing_algorithm": signer.algorithm,
        "signer_key_id": signer.key_id,
    }
    manifest_envelope = _signed_envelope(manifest_body, signer)
    _write_json_immutable(manifest_path, manifest_envelope)
    return LedgerArtifacts(
        ledger_path=ledger_path,
        hidden_manifest_path=hidden_path,
        manifest_path=manifest_path,
        ledger_sha256=file_sha256(ledger_path),
        manifest_sha256=file_sha256(manifest_path),
        opportunity_count=len(visible_rows),
    )


def verify_signed_manifest(path: Path, signer: ManifestSigner) -> dict[str, Any]:
    envelope = json.loads(path.read_text(encoding="utf-8"))
    if set(envelope) != {"body", "signature"}:
        raise ValueError(f"Malformed signed manifest: {path}")
    if not signer.verify(envelope["body"], str(envelope["signature"])):
        raise ValueError(f"Manifest signature mismatch: {path}")
    return dict(envelope["body"])


def public_ledger_rows(path: Path) -> list[dict[str, Any]]:
    rows = pq.read_table(path).to_pylist()
    forbidden = {
        "unsafe_label",
        "hidden_regime",
        "corruption_families",
        "corruption_intensity",
        "feedback_release_step",
        "feedback_reliability",
        "policy_state",
        "hidden_state",
    }
    leaks = forbidden.intersection(rows[0] if rows else {})
    if leaks:
        raise ValueError(f"Public ledger contains evaluator-only fields: {sorted(leaks)}")
    return rows


def _signed_envelope(body: Mapping[str, Any], signer: ManifestSigner) -> dict[str, Any]:
    return {"body": body, "signature": signer.sign(body)}


def _write_json_immutable(path: Path, payload: Mapping[str, Any]) -> None:
    content = json.dumps(payload, indent=2, sort_keys=True, default=_json_default) + "\n"
    _write_bytes_immutable(path, content.encode("utf-8"))


def _write_parquet_immutable(path: Path, table: pa.Table) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    pq.write_table(table, temporary, compression="zstd", use_dictionary=False, write_statistics=True)
    content = temporary.read_bytes()
    temporary.unlink()
    _write_bytes_immutable(path, content)


def _write_bytes_immutable(path: Path, content: bytes) -> None:
    if path.exists():
        if path.read_bytes() != content:
            raise FileExistsError(f"Refusing to overwrite immutable artifact: {path}")
        return
    temporary = path.with_suffix(path.suffix + ".writing")
    temporary.write_bytes(content)
    os.replace(temporary, path)


def _json_default(value: Any) -> Any:
    if hasattr(value, "__dict__"):
        return asdict(value) if hasattr(value, "__dataclass_fields__") else value.__dict__
    if isinstance(value, tuple):
        return list(value)
    raise TypeError(f"Unsupported JSON value: {type(value).__name__}")
