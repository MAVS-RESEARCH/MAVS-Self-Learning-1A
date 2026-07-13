# MAVS Self-Learning 1A

This repository extends the pinned MAVS Chapter 10D foundation with the staged
MAVS-Self-Learning 300K validation program. Phase 0 establishes clone provenance,
typed contracts, randomized world compilation, immutable signed ledgers,
visible/hidden separation, measurement identities, deterministic replay, and
non-competitive trivial/oracle diagnostic bounds.

Phase 0 trains no model and makes no Self-Learning performance or superiority
claim. See `CLAIMS.md`, `REPRODUCIBILITY.md`, `WorkPlan.md`, and the contemporaneous
evidence ledger in `Path.md`.

## Inherited regression commands

Install development dependencies:

```bash
python -m pip install -e .[dev]
```

Run the smoke experiment:

```bash
python scripts/run_experiment.py --config configs/experiments/synthetic_smoke.yaml
```

Validate the generated trace:

```bash
python scripts/validate_traces.py --input results/raw/synthetic_smoke.jsonl
```

Run tests:

```bash
python -m pytest
```

## Claim Discipline

Phase 1 is software infrastructure only. It does not test MAVS-GC performance, does not train models, and does not support any frontier-model, industrial-scale, universal robustness, or correlated-failure claims.

## Phase 0 command

```bash
node scripts/run_phase0.mjs --run-id phase0_20260713
```

