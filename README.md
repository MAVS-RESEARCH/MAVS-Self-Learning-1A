# MAVS Self-Learning 1A

Research implementation and validation package for Self-Learning MAVS with executable diagnostic synthesis and Perception Closure. The repository extends the pinned MAVS Chapter 10D foundation and contains the completed Phase 0-10 validation program.

## Current status

All phases are implemented, audited, committed, and frozen. The accepted Version 0.4 release is `perception_closure_v04_phase10_20260718_r3`.

- Phase 6: executable diagnostic synthesis, semantic/behavioral deduplication, blind certification, anti-gaming controls, and candidate lifecycle.
- Phase 7: live Perception-Closure runtime with explicit hypotheses, targeted evidence acquisition, sparse diagnostics, local closure, escalation exhaustion, and persistence.
- Phase 8: synthesis-integrity, runtime, persistence, and consolidation ablations.
- Phase 9: separate retrospective and sealed blind three-generation revalidation tracks.
- Phase 10: independent reproducibility, claim, result-isolation, signature, and release audit.

The Phase 10 audit passed all 25 WorkPlan clauses with zero findings. The complete repository regression passed 411 tests; the clean pinned environment passed 203 Phase 6/7/8/10 tests.

## Audited results

- 3,341 Phase 6-9 artifacts and all 40 candidates are hash-bound in the frozen input index.
- 600 certification gates and 6,624 Phase 9 metric values independently recompute with zero mismatch.
- 414 condition-generation metric permutation challenges and all candidate metadata permutations are invariant.
- 33,606,144 terminal/query/program/scope/certificate replay comparisons have zero mismatch.
- 6,210,384 terminal records have complete authority, lineage, and residual-escalation evidence.
- All 174 indexed legacy files remain byte-identical; Track A and Track B remain isolated.
- Seven Ed25519 signatures and the complete frozen artifact graph verify successfully.

On the sealed blind G2/G3 bank, cumulative learning preserves observed UAR and FRR at zero while reducing mean closure rounds relative to fresh learning:

| Generation | Cumulative rounds | Fresh rounds |
|---|---:|---:|
| G2 | 1.026467 | 1.912667 |
| G3 | 0.987600 | 1.905867 |

Scope leakage, anti-scope violations, forgetting, and negative transfer remain zero in these audited comparisons. These are finite-bank research results, not universal guarantees.

## Claim boundary

The generated Phase 10 claim ledger supports only:

- executable differentiated diagnostic synthesis within the audited Phase 6 grammar and banks;
- Perception Closure on the declared finite covered classes and budgets;
- cumulative three-generation transfer on the sealed Phase 9 blind bank.

Universal zero-error, zero-escalation outside the covered class, production deployment readiness, and general-domain performance are unsupported. Oracle conditions are evaluator-only diagnostic bounds and are excluded from competitive claims.

No opaque model is trained by the core system. Phase 10 performs no training, tuning, threshold selection, or bank repair; it reads sealed Phase 6-9 evidence and independently recomputes the registered gates.

## Reproduce and verify

Install development dependencies:

```bash
python -m pip install -e .[dev]
```

Run the complete test suite:

```bash
python -m pytest -q
```

Run the independent reduced reproduction package:

```bash
python scripts/run_v04_reproduction.py --component all
```

Verify the frozen release without modifying it:

```bash
python scripts/verify_v04_release.py
```

The complete Phase 10 orchestrator is:

```bash
node scripts/run_phase10.mjs
```

It refuses to overwrite the sealed release. Post-freeze work requires a new namespace/version.

## Evidence map

- `WorkPlan.md`: normative phased implementation and gate specification.
- `Path.md`: contemporaneous evidence ledger, rejected attempts, exact commands, console instrumentation, hashes, commits, and final verdict.
- `results/perception_closure_v04/phase10/reports/phase10_audit.json`: independent clause and gate audit.
- `results/perception_closure_v04/phase10/claims/claim_ledger.json`: mechanically generated claim statuses and permitted language.
- `results/perception_closure_v04/phase10/release/release_manifest.json`: frozen signed artifact graph.
- `results/perception_closure_v04/phase10/REPRODUCE.md`: component-level reproduction commands.
- `results/RESULTS_INDEX.md`: authoritative result pointers and legacy/current separation.

Rejected Phase 10 attempts are retained under `results/perception_closure_v04/phase10/diagnostic_runs/` as immutable, non-claim-eligible evidence. They are not part of the accepted release graph.
