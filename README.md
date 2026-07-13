# MAVS Chapter 10D

This repository implements the Chapter 10D dynamic validation plan for MAVS-GC. The Phase 1 code establishes the method-neutral benchmark foundation: typed contracts, config loading, deterministic seeds, registry wiring, JSONL audit traces, a runner, validation scripts, and a deterministic smoke experiment.

## Phase 1 Commands

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

