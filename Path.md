# MAVS-Self-Learning 300K Implementation Path

## Document control

- Reset date: 2026-07-13
- Phase 0 start date: 2026-07-13
- Governing plan: `WorkPlan.md`
- Target repository: `MAVS-RESEARCH/MAVS-Self-Learning-1A`
- Clean planning checkpoint: commit `13629bb` (`docs: add self-learning implementation plan`)
- Current implementation state: Phase 0 in progress
- Current compliance state: Phase 0 not yet assessed

## Reset record

The prior one-pass implementation and its claimed compliance evidence are invalid and are not part of this repository. The replacement repository began with `LICENSE`, `WorkPlan.md`, and this newly created evidence ledger. It did not contain a Chapter 10D source tree when Phase 0 began.

The reset removed:

- the compact synthetic Self-Learning 300K program;
- all Self-Learning-specific phase, suite, method, and ablation configuration files;
- all provisional Self-Learning schemas, modules, scripts, and tests;
- the prior `Path.md` and its retrospective completion claims;
- the prior claim, reproducibility, baseline, and Makefile additions tied to that implementation;
- every generated artifact under `results/`;
- all test and Python cache directories.

No metric, benchmark, trace count, report, certification flag, or compliance verdict from the removed repository may be cited as evidence. Its history was not transferred into the replacement repository.

## Foundation status at Phase 0 start

No foundation code was present at Phase 0 start. Phase 0 must qualify and import `MAVS-RESEARCH/MAVS-Chapter-10D` at an immutable upstream SHA, excluding all upstream `results/` content and successor planning files. The provenance-only import must precede every behavioral change.

## Governing-source lock

| Source | SHA-256 | Review status |
|---|---|---|
| `WorkPlan.md` | `D136542DF07DB96B2CA5BD64F8BB2B630E2D713BCB77735A8117F8A313335E18` | Phase 0 clauses reviewed; uncommitted audited amendments present at start. |
| `MAVS_Self_Learning_300K_Three_Generation_Brutal_Validation_Spec.docx` | `FD25B7666DF6B7B47F28AF70264457035AA8269F0DF74CF08C9E8ED89EED1A8F` | Complete structural content reviewed before Phase 0. |
| `MAVS_Self_Learning_Architecture_and_Pareto_Comparison.docx.pdf` | `3797AEBE1528B26C06BDCEA6231A80D4D3EB937524C5F6EDBBE9F55D2EC2626E` | All 23 pages extracted and visually inspected before implementation. |

The architecture review fixed the Phase 0 semantic floor: deterministic fast-loop execution; complete provenance; typed decisions and evidence; the formal `M^SL=(M,H,O,D,L,V,K,C,S,Q)` separation; governed configuration selection; immutable trace/replay semantics; explicit intended scope; no direct candidate deployment; and a safety kernel that preserves hard-veto, mitigation, scope, trace, and rollback invariants. Where the validation specification names the governed selector as `S_t` while the architecture configuration tuple shows intended scope `Omega_t`, Phase 0 will serialize both selector identity and scope policy rather than dropping either contract.

## Phase 0 execution log

### P0-E000 - Authorization and scope lock

- Status: PASS.
- Evidence: user explicitly authorized Phase 0 and prohibited advancing to later phases.
- WorkPlan clauses: Sections 2, 4, 4.1, 7, 16, and 18.
- Scope decision: implement only clone qualification, measurement integrity, randomized world compilation, immutable ledgers/manifests, trace/update schemas, validators, Phase 0 metrics/bounds, and the 5,000-decision Phase 0 benchmark.

### P0-E001 - Initial repository inspection

- Command: `git status -sb; git remote -v; git log --oneline --decorate -5; Get-ChildItem -Force`.
- Exit status: 0.
- Observed state: `main` tracked `origin/main`; only `LICENSE`, `Path.md`, and `WorkPlan.md` existed; `WorkPlan.md` contained the prior audited amendments and was not committed.
- Corrective action: lock the amended WorkPlan and this Phase 0 start record in a documentation-only checkpoint before the first code-bearing provenance import.

### P0-E002 - Architecture PDF review and rendering fallback

- Primary render attempt: bundled `pdfinfo.cmd` and `pdftoppm.cmd`.
- Exit status: 1; the wrapper referenced an unavailable bundled Poppler path.
- Corrective action: used bundled `pypdfium2` to render all 23 pages at scale 1.5 and generated four contact sheets; used `pypdf` for complete text extraction.
- Result: PASS. All pages were present, readable, and free of observed clipping, overlap, broken tables, or missing content.
- Temporary evidence location: `tmp/pdfs/architecture/`; this directory is not a research result and will be removed before Phase 0 closure.

### P0-E003 - Immutable Chapter 10D foundation qualification

- Upstream: `https://github.com/MAVS-RESEARCH/MAVS-Chapter-10D.git`.
- Qualified commit: `a1bfd52b59aaba69b2c041a5e7da0ee263125c1f`.
- Eligible import: 141 Git tree entries after excluding `.git/`, all 12,200 tracked `results/` files, upstream `WorkPlan.md`, and upstream `Path.md`.
- Eligible Git-tree record SHA-256: `28F09676AB6D636A3689196C14BB5AE52CE64E007046A9EFD74DF181D23DBF62`. This digest is over the newline-terminated, ordered `git ls-tree -r HEAD` records remaining after the documented exclusions; it is not a digest of generated output.
- Runtime used for qualification: CPython 3.13.7.
- Original test command: `python -m pytest -q`.
- Original test result: PASS, 78 collected tests, exit status 0.
- Original smoke command: `python scripts/run_experiment.py --config configs/experiments/synthetic_smoke.yaml`.
- Original smoke result: PASS, 8 records, exit status 0.
- Original trace-validation command: `python scripts/validate_traces.py --input results/raw/synthetic_smoke.jsonl`.
- Original trace-validation result: PASS, 8 records, exit status 0.
- Qualification smoke trace SHA-256: `D55F993CA34C3B652314CA76B35CDA07E787798793F75BC197997F85E10A37EC`.
- Failed command retained as evidence: `python scripts/validate_trace.py --trace ...` failed because the inherited command is named `validate_traces.py` and accepts `--input`. The correct inherited command above then passed without modifying the upstream code.
- Qualification conclusion: PASS. The immutable foundation satisfies all three pre-import regression gates in WorkPlan Section 1.1. Temporary qualification results will not be imported.

### P0-E004 - Provenance-only foundation import

- Import method: `git archive` at the qualified upstream commit, explicitly restricted to `.gitattributes`, `.gitignore`, `LICENSE`, `README.md`, `configs/`, `data/`, `pyproject.toml`, `scripts/`, `src/`, and `tests/`.
- Imported behavior changes: none. Every imported source/config/test file is the upstream blob at the pinned commit.
- Excluded paths: `.git/`, `results/`, upstream `WorkPlan.md`, and upstream `Path.md`.
- Provenance evidence: `UPSTREAM_PROVENANCE.md` and `provenance/upstream_import_exclusions.json`.
- Result-tree assertion immediately after extraction: PASS; target `results/` did not exist.
- Runtime lock: CPython 3.13.7, NumPy 2.3.4, pandas 2.3.2, PyArrow 21.0.0, PyYAML 6.0.2, pytest 9.0.2.

### P0-E005 - Post-import inherited regression before behavioral changes

- Imported-target test command: `python -m pytest -q`.
- Result: PASS, 78 inherited tests, exit status 0.
- Imported-target smoke command: `python scripts/run_experiment.py --config configs/experiments/synthetic_smoke.yaml`.
- Result: PASS, 8 records, exit status 0.
- Imported-target validator command: `python scripts/validate_traces.py --input results/raw/synthetic_smoke.jsonl`.
- Result: PASS, zero trace errors, exit status 0.
- Imported-target smoke SHA-256: `6F7DF087220FCB377C39EB4888297E1258EB359F66B74F529ED8024C5D31D7EE`.
- Interpretation: the smoke hash differs from isolated upstream because the trace correctly embeds target commit `052b03eefd54e6f89d3bb9b59b0f0baa8549fe04`; functional record count and validation are unchanged.
- Gate decision: PASS. Behavioral Phase 0 implementation began only after this target-side gate.

### P0-E006 - Phase 0 contract, compiler, ledger, and measurement implementation

- Status: IMPLEMENTED; final acceptance run pending the code checkpoint.
- Typed contracts: `src/mavs10d/core/contracts.py` defines `SeedTuple`, `WorldSpec`, `VisibleOpportunity`, `LearningEvent`, `DiagnosticProposal`, `CandidateConfiguration`, `CertificationReport`, `UpdateDecision`, `ParticipantState`, `GovernanceComponent`, and `ActiveGovernanceConfiguration`.
- Active configuration: all twelve symbols `G_t`, `A_t`, `W_t`, `P_t`, `Theta_t`, `tau_hard_t`, `alpha_t`, `lambda_t`, `delta_t`, `theta_0_t`, `tau_G_t`, and `S_t` have exact, checked meanings. `omega_scope_policy` separately preserves the architecture authority's intended-scope contract. Proposed configurations fail closed when an approved fast-loop configuration is required.
- Randomness: `HierarchicalSeeds` derives suite/generation/world/episode/step/method seeds with SHA-256 domain separation and local NumPy generators. Tests prove that derivation does not mutate Python or NumPy global RNG state.
- World compilation: `world_compiler.py` implements the pre-registered domain, horizon, prevalence, feedback, policy, specialist, corruption, observability, cost, and temporal priors. It retains every latent world parameter in the signed hidden manifest and exposes only `VisibleOpportunity` fields to participants.
- Inherited allocation: `InheritedStaticCompiler` executes the pinned Chapter 10D `StaticAccuracyAdapterEnv` for ten 100-step episodes per generation, producing the required 1,000 inherited static decisions. These are not relabeled generated-world rows.
- Independent generator: `IndependentReferenceCompiler` uses a distinct implementation ID and RNG domain separator for leave-generator-out contract testing.
- Ledger integrity: `world_ledger.py` writes deterministic Zstandard Parquet ledgers and signed JSON envelopes. Manifests bind ledger bytes, row order, Arrow schema, generator source package, configs, hidden parameters, and the hidden-manifest file. Existing unequal artifacts cannot be overwritten.
- Leakage barrier: methods receive no hidden object; oracle access requires an evaluator payload; `participant_file_guard` denies direct Python file reads of registered hidden manifests during participant decisions. Leakage tests cover payload absence, oracle fail-closed behavior, and file denial.
- Corruption and schedules: added bounded deterministic composition and budgeted adversarial-response scheduling without hidden method inputs.
- Measurements: added exact burden, non-dominance/frontier, transfer-estimand, Wilson-interval, and primitive action-accounting implementations.
- Bounds: added accept-all, reject-all, escalate-all, deterministic-random, oracle-label, and oracle-regime implementations. All declare or are recorded as non-competitive diagnostics.
- Schemas: added the eight WorkPlan schemas plus `active_governance_configuration.schema.json`; Draft 2020-12 schema checks pass.
- Results discipline: `clean_results.py` resolves and verifies the repository-owned root before deletion and fails if generated files survive an all-run cleanup. New compile, stress, aggregation, reset, participant, trace, and update commands require or consume a safe run ID and namespaced run manifest.
- Provenance aggregation: `aggregate_phase0.py` refuses any trace whose run ID, Git SHA, Phase 0 config hash, or ledger hash differs from the selected run.
- Documentation: added `REPRODUCIBILITY.md`, `CLAIMS.md`, `Makefile`, updated `README.md`, and frozen Phase 0/suite/world/active-configuration YAML contracts.
- Model training: none. Phase 0 contains no optimizer, checkpoint, training split, or trained-model benchmark. This exactly follows the Phase 0 default and prevents training evidence from being confused with infrastructure evidence.

### P0-E007 - Phase 0 test package and rejected attempts

- Phase 0 test directories: `tests/phase0`, `tests/metamorphic`, `tests/leakage`, and `tests/statistical`.
- Current Phase 0-specific result: PASS, 27 tests.
- Current complete result: PASS, 105 tests (78 inherited plus 27 Phase 0-specific), exit status 0.
- Bytecode compilation: `python -m compileall -q src scripts tests`; PASS, exit status 0.
- Patch hygiene: `git diff --check`; PASS, exit status 0.
- Rejected attempt 1: the bundled Python runtime lacked pytest. No dependency assumption was made; the qualified CPython 3.13.7 environment was recorded and used.
- Rejected attempt 2: an incorrect singular inherited validator filename was attempted once; the inherited README/source established `validate_traces.py --input`, which passed without source modification.
- Rejected attempt 3: the first stress prototype called `git rev-parse` once per record and was terminated as computationally invalid. The implementation now resolves immutable provenance once per generation and passes it into record construction.
- Rejected attempt 4: the first cleanup of that terminated prototype encountered the still-running child process holding a trace handle. The exact process was identified and stopped, the scoped cleaner then removed only `phase0_dryrun`, and no provisional output was retained.
- Rejected attempt 5: the first world-manifest representation retained only a latent-state hash. Audit identified that this did not satisfy the requirement to store all latent parameters. The hidden manifest now stores the complete per-world latent record and hashes the combined hidden opportunity/world-parameter payload.
- Rejected attempt 6: the first 1,000-row static partition used the randomized compiler under an inherited label. Audit rejected this as semantically insufficient. The replacement executes the inherited `StaticAccuracyAdapterEnv` directly and reset validation checks its implementation ID and exact ten-by-100 allocation.
- Dry-run stress evidence produced before the last compiler/manifest changes is invalidated and removed. It will not appear in final evidence or results.

### P0-E008 - Console checkpoint implementation

- `scripts/run_phase0.mjs` is the authoritative Phase 0 orchestrator and uses native JavaScript `console.log` at every orchestration checkpoint.
- Every `console.log` has an immediately preceding `// console.log: <event>` identifier comment. `audit_phase0.py` independently fails on missing or mismatched comments.
- Python implementation steps use the inherited structured `console_log` adapter, which prints `console.log {JSON}`; every newly added call has an adjacent `# console.log: <event>` comment.
- Exact file/line/comment/event registry will be frozen after the implementation checkpoint so line numbers cannot be invalidated by later code edits.

### P0-E009 - First authoritative run rejected during provenance review

- Implementation checkpoint tested: `941bde5` (`feat: implement Phase 0 measurement foundation`).
- Run ID: `phase0_20260713`.
- Observed result before rejection: the orchestrator, 105-test regression, 15,000 canonical-opportunity run, 90,000 matched replay records, deterministic replay, and Phase 0 audit all returned success.
- Rejection decision: these outputs are invalidated and cannot serve as Phase 0 evidence.
- Defect: `aggregate_phase0.py` compared trace provenance with the repository's current `HEAD`. A later documentation-only `Path.md` commit would therefore make a valid immutable run impossible to re-aggregate, even though neither its implementation nor its inputs changed.
- WorkPlan clauses affected: Sections 2.2, 4 mandatory integrity traces, 7 steps 1 and 5, the Phase 0 hash-error exit gate, and Section 18 reproducibility evidence.
- Corrective action: freeze one validated 40-character implementation Git SHA when ledgers are compiled; bind it into the run manifest and every signed generation manifest; make trace emission, reset validation, and aggregation consume that immutable SHA; reject invalid SHAs and generation/run provenance disagreement.
- Additional checkpoint correction: the Python checkpoint comments for stress steps 03 and 04 were made text-identical to their emitted event identifiers.
- Corrective-test preflight attempt 1: the new invalid-SHA test initially requested a two-decision randomized partition, below the compiler's pre-registered minimum horizon of 80. The test failed before reaching its target assertion; its fixture was corrected to 80 without changing production behavior, and this failed attempt is retained here rather than omitted.
- Corrective preflight after the fixture repair: PASS, 106 tests total (78 inherited plus 28 Phase 0-specific); `python -m compileall -q src scripts tests` PASS; `git diff --check` PASS.
- Result hygiene: the rejected run will be removed with the scoped cleaner before the replacement run. No metric or hash from it will be used in the Phase 0 verdict.
- Next gate: pass the complete preflight after this correction, commit it, verify a clean result tree, and regenerate all authoritative evidence against that commit.

## Execution rules for this path

This document will be updated while work is performed, not reconstructed after a run. Every phase entry must record:

1. the exact `WorkPlan.md` requirements being implemented;
2. files created, changed, or removed and why;
3. implementation decisions, interfaces, invariants, and deviations;
4. commands executed and their exit status;
5. tests and benchmarks run, including seeds, splits, manifests, and artifact paths;
6. evidence that evaluation data is disjoint from training, tuning, calibration, repair, and development data;
7. failures, rejected approaches, rollbacks, unresolved risks, and corrective work;
8. the phase exit-gate decision with direct evidence rather than summary booleans;
9. the commit hash that freezes the accepted phase state.

No later phase may be marked in progress until the preceding phase exit gate has passed. A phase may only be marked complete when every stated exit criterion in `WorkPlan.md` has independently reproducible evidence. Missing, simulated, placeholder, hard-coded, or structurally inferred evidence is a failure, not a pass.

## Phase ledger

| Phase | WorkPlan scope | Status | Exit-gate evidence |
|---|---|---|---|
| 0 | Clone qualification and measurement integrity | In progress | P0-E000 through P0-E002 |
| 1 | Non-stationary distribution gauntlet | Not started | None |
| 2 | Corruption, correlated collapse, and partial observability | Not started | None |
| 3 | Autonomous failure discovery and self-repair | Not started | None |
| 4 | Full baseline tournament and Pareto audit | Not started | None |
| 5 | Deep ablation, transfer, and anti-overfit trials | Not started | None |

## Current checkpoint

Phase 0 is active. The implementation and 105-test preflight pass, but Phase 0 is not yet accepted: code must be checkpointed, the clean authoritative three-generation run must execute against that checkpoint, every result must be validated and independently replayed, exact console line evidence must be added, and the final clause-by-clause audit must pass. No Phase 1 work is authorized.
