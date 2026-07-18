# Reproduce MAVS Self-Learning Version 0.4

The following commands use the exact Phase 10 dependency lock and create an ephemeral clean environment:

```text
python scripts/run_v04_reproduction.py --component phase6
python scripts/run_v04_reproduction.py --component phase7
python scripts/run_v04_reproduction.py --component phase8
python scripts/run_v04_reproduction.py --component phase9
python scripts/run_v04_reproduction.py --component phase10
python scripts/run_v04_reproduction.py --component manifests
```

Complete release audit and claim generation:

```text
node scripts/run_phase10.mjs
```

A reduced Phase 9 replay is a reproducibility check; complete scientific metrics remain bound to the full sealed Phase 9 banks.
