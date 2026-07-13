# Chapter 10D Upstream Provenance

## Immutable source

- Repository: `https://github.com/MAVS-RESEARCH/MAVS-Chapter-10D.git`
- Commit: `a1bfd52b59aaba69b2c041a5e7da0ee263125c1f`
- Upstream commit timestamp: `2026-07-05T14:27:43+05:00`
- Upstream commit subject: `Complete Phase 6 minimum validation run`
- Import date: `2026-07-13`
- Import mechanism: `git archive` of the named commit, restricted to the allowed paths below.

## Import boundary

The provenance-only import contains the upstream `.gitattributes`, `.gitignore`,
`LICENSE`, `README.md`, `configs/`, `data/`, `pyproject.toml`, `scripts/`, `src/`,
and `tests/` paths. It changes no imported behavior.

The following paths were intentionally excluded:

- `.git/`, because target repository history is authoritative;
- `results/`, including 12,200 tracked upstream result files, because inherited
  results are prohibited evidence;
- upstream `WorkPlan.md`, because the target Self-Learning plan is authoritative;
- upstream `Path.md`, because the target evidence ledger is authoritative.

The ordered, newline-terminated `git ls-tree -r HEAD` records for the 141 eligible
entries have SHA-256
`28F09676AB6D636A3689196C14BB5AE52CE64E007046A9EFD74DF181D23DBF62`.
The machine-readable exclusion declaration is
`provenance/upstream_import_exclusions.json`.

## Pre-import qualification

The source was tested in an isolated clone before import:

| Gate | Command | Result |
|---|---|---|
| Unit/integration suite | `python -m pytest -q` | PASS; 78 tests |
| Original smoke | `python scripts/run_experiment.py --config configs/experiments/synthetic_smoke.yaml` | PASS; 8 records |
| Original trace validation | `python scripts/validate_traces.py --input results/raw/synthetic_smoke.jsonl` | PASS; 8 records |

The isolated smoke trace SHA-256 was
`D55F993CA34C3B652314CA76B35CDA07E787798793F75BC197997F85E10A37EC`.
That trace and all other isolated-clone outputs were excluded from the import.

Qualification runtime: CPython 3.13.7, NumPy 2.3.4, pandas 2.3.2,
PyArrow 21.0.0, PyYAML 6.0.2, and pytest 9.0.2.

## Claim boundary

Import qualification establishes only that the pinned Chapter 10D software
foundation reproduces its inherited tests and smoke path. It is not evidence of
Self-Learning performance, safety, robustness, or superiority.
