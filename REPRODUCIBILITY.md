# Reproducibility

The accepted release is `perception_closure_v04_phase10_20260718_r3`, bound to source commit `33d806a42bf87c12a62b4d2724274dc957112a80`.

```text
python -m pip install -e .[dev]
python -m pytest -q
python scripts/run_v04_reproduction.py --component all
python scripts/verify_v04_release.py
```

The reduced reproduction creates an ephemeral environment from `configs/phases/phase10_requirements.lock`, executes committed source with locked determinism controls, and deletes the environment afterward. Full scientific metrics remain those of the sealed Phase 9 banks.

The frozen verifier checks required artifacts, signatures, public key, claims, result index, artifact graph, and seal bindings. The Phase 10 cleaner refuses to alter a sealed namespace. See `results/perception_closure_v04/phase10/REPRODUCE.md` and `Path.md` for component commands and exact evidence.
