# MAVS-Self-Learning 300K Implementation Path

## Document control

- Reset date: 2026-07-13
- Governing plan: `WorkPlan.md`
- Clean code foundation: commit `88feabb` (`chore: import verified Chapter 10D foundation`)
- Current implementation state: not started
- Current compliance state: not assessed

## Reset record

The prior one-pass implementation and its claimed compliance evidence are invalid and are not part of the current working tree. The repository has been restored to the verified Chapter 10D foundation. Only `WorkPlan.md` has been retained from the prior Self-Learning 300K work, and this file has been created from scratch.

The reset removed:

- the compact synthetic Self-Learning 300K program;
- all Self-Learning-specific phase, suite, method, and ablation configuration files;
- all provisional Self-Learning schemas, modules, scripts, and tests;
- the prior `Path.md` and its retrospective completion claims;
- the prior claim, reproducibility, baseline, and Makefile additions tied to that implementation;
- every generated artifact under `results/`;
- all test and Python cache directories.

No metric, benchmark, trace count, report, certification flag, or compliance verdict from the removed run may be cited as evidence. The old commits remain visible in Git history for auditability, but their implementation is absent from the current tree.

## Retained foundation

The pre-existing Chapter 10D code at commit `88feabb` remains as the implementation baseline. It is not evidence that any phase of `WorkPlan.md` has been completed. Existing foundation code must be inspected and explicitly accepted, modified, or rejected during the relevant phase before it can support a Self-Learning claim.

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
| 0 | Clone qualification and measurement integrity | Not started | None |
| 1 | Non-stationary distribution gauntlet | Not started | None |
| 2 | Corruption, correlated collapse, and partial observability | Not started | None |
| 3 | Autonomous failure discovery and self-repair | Not started | None |
| 4 | Full baseline tournament and Pareto audit | Not started | None |
| 5 | Deep ablation, transfer, and anti-overfit trials | Not started | None |

## Current checkpoint

The reset is complete. There are no current Self-Learning 300K results and no phase has begun. The next authorized implementation action is Phase 0 as defined in `WorkPlan.md`; it must be implemented and validated independently before any Phase 1 work begins.
