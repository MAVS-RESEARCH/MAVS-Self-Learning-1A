.PHONY: phase0 clean inherited-test inherited-smoke

RUN_ID ?= phase0_local

phase0:
	node scripts/run_phase0.mjs --run-id $(RUN_ID)

clean:
	python scripts/clean_results.py --all-runs

inherited-test:
	python -m pytest -q tests/unit tests/integration

inherited-smoke:
	python scripts/run_experiment.py --config configs/experiments/synthetic_smoke.yaml
	python scripts/validate_traces.py --input results/raw/synthetic_smoke.jsonl
