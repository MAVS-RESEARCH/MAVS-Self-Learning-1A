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

Phase 0 is active. No implementation code has been imported or written yet. The next gate is a documentation-only checkpoint followed by qualification of the immutable Chapter 10D upstream SHA. No Phase 1 work is authorized.
