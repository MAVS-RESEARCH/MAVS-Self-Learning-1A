# Phase 0 Reproducibility

## Authority and source

The governing documents and their SHA-256 values are recorded in `Path.md`.
Chapter 10D source provenance is fixed in `UPSTREAM_PROVENANCE.md`.

## Runtime

The qualified runtime is CPython 3.13.7 with NumPy 2.3.4, pandas 2.3.2,
PyArrow 21.0.0, PyYAML 6.0.2, jsonschema 4.x, and pytest 9.0.2. Install with:

```text
python -m pip install -e .[dev]
```

## Complete Phase 0 workflow

Run the commented JavaScript orchestrator. Every orchestration step emits a
machine-readable `console.log` checkpoint:

```text
node scripts/run_phase0.mjs --run-id phase0_20260713
```

The runner clears only the repository-owned `results/` tree, reproduces the
inherited smoke/test path, compiles three independently seeded 5,000-opportunity
ledgers, replays six non-competitive diagnostic bounds, validates all traces and
manifests, runs Phase 0 tests, and writes an audit report.

## Determinism and seeds

Seeds derive through `suite -> generation -> world -> episode -> step -> method`.
The new generator uses local NumPy `Generator` instances and does not modify
module-global Python or NumPy RNG state. G1/G2/G3 use distinct ranges from
`configs/suites/self_learning_300k.yaml`. Manifests hash row order, schema,
generator source, configs, hidden parameters, and ledger bytes, then apply an
HMAC-SHA256 integrity signature with a generation-specific deterministic Phase 0
key commitment. This signature is for reproducible tamper detection, not external
identity attestation.

## Result boundary

Only outputs created by the current run ID are admissible. The run manifest maps
logical artifacts to namespaced paths. Aggregation across a different run ID,
Git SHA, config hash, or ledger hash is prohibited.
