# MAVS-Self-Learning 300K Implementation Work Plan

## 0. Document control

- **Program name:** `MAVS-SL-300K / Three-Generation Continual Governance Stress Program`.
- **Target repository:** `MAVS-RESEARCH/MAVS-Self-Learning-1A`
- **Local checkout:** `C:\Users\Saif malik\Self-Learning-MAVS-1`
- **Plan status:** implementation-ready; no implementation claim is made by this document.
- **Primary specification:** `MAVS_Self_Learning_300K_Three_Generation_Brutal_Validation_Spec.docx`.
- **Architecture authority:** `MAVS_Self_Learning_Architecture_and_Pareto_Comparison.docx.pdf`.
- **Source foundation required by the specification:** `MAVS-RESEARCH/MAVS-Chapter-10D`.
- **Planning date:** 2026-07-13.

This plan preserves the specification's six phases because the stated work is large and the phase budgets form an exact 100,000-decision generation: 5,000 + 15,000 + 20,000 + 20,000 + 25,000 + 15,000. The complete six-phase program is executed three times on independently regenerated worlds for exactly 300,000 canonical decision opportunities. Replays by methods, controls, sweeps, and ablations are evaluations of those same canonical opportunities and therefore do not change the canonical total.

## 1. What is being built

MAVS-Self-Learning is a governance-first system. Its fast loop executes only an approved governance configuration. Its slow loop learns from completed traces and repeated ambiguity, attributes failures to governance components, proposes the smallest explicit diagnostic or policy intervention, attacks that proposal with disjoint and adversarial tests, and promotes it only if a non-learned safety kernel and every certification gate pass.

The learned object is primarily the governance representation: diagnostics, diagnostic scopes, witnesses, evidence-recovery rules, ontology entries, configuration composition, and configuration applicability. The predictive specialists may remain frozen. This is not uncontrolled online model rewriting and it is not threshold tuning presented as frontier expansion.

The terminal actions are:

1. `ACCEPT`: release/execute; unsafe acceptance is a UAR event.
2. `REJECT`: block; safe rejection is an FRR event.
3. `ESCALATE`: request evidence/review or invoke bounded recovery; it is not an FP/FN, but it incurs escalation, latency, and intervention cost.

The lexicographic objective is: minimize UAR; at retained-set UAR <= epsilon minimize FRR; minimize escalation/intervention burden; minimize adaptation lag, recovery lag, and recurrence; maximize reward/calibration/stability; then minimize complexity, latency, and redundancy. In the fully labeled synthetic core, epsilon is zero: no amount of recall gain compensates for one observed retained-set unsafe acceptance.

The scoped empirical target is observed `UAR = 0` and `FRR = 0` on covered labeled worlds while escalation, intervention, adaptation cost, and cold-start loss contract from G1 to G2 to G3. A compounding claim additionally requires cumulative MAVS-SL to beat fresh MAVS-SL on the identical later-generation ledgers. This is an evaluation target with exact confidence bounds, never a universal proof.

### 1.1 Pre-registered hypotheses and required falsifiers

These hypotheses are first-class experiment contracts. The suite config, report generator, and claim audit must assign every confirmatory metric, baseline comparison, and falsifier below an immutable ID. A hypothesis is not supported merely because its preferred metric moved in the expected direction; its required falsifier must also be evaluated and reported.

| ID | Hypothesis | Required falsifier |
|---|---|---|
| H1 | MAVS-SL yields lower UAR than every non-governance-learning baseline at matched FRR and escalation. | Any baseline weakly dominates MAVS-SL across the complete paired frontier. |
| H2 | Repeated exposure to a recoverable failure family reduces FRR without increasing retained-set UAR. | Recall improves while any previously certified unsafe family is reopened. |
| H3 | MAVS-SL adapts and recovers faster than static MAVS, adaptive thresholds, online conformal, and drift-only adaptation. | Median adaptation or recovery lag is not better at matched burden. |
| H4 | Diagnostic synthesis and certification add value beyond threshold tuning, selector learning, or model adaptation alone. | A shallow ablation matches the full system on all primary metrics. |
| H5 | Governance primitives transfer across domains better than domain-specific safety filters. | Cross-domain holdouts erase the advantage or expose scope leakage. |
| H6 | Any observed zero-error result is not reject-all behavior. | Zero UAR/FRR requires excessive escalation, intervention, or lost task reward. |
| H7 | Cumulative MAVS-SL enters G2/G3 with lower early-run loss, shorter detection/repair latency, and a better frontier than fresh MAVS-SL on the identical ledger. | Fresh MAVS-SL matches or beats cumulative MAVS-SL on paired later-generation worlds. |
| H8 | Transfer occurs through abstract diagnostics, scopes, capsules, and certified configurations rather than raw-example memorization. | A raw-memory control matches cumulative transfer, or transfer disappears under surface/structural resets. |
| H9 | Consolidation improves library efficiency while preserving all protected-family behavior. | Pruning/merging causes retained regression, or unpruned growth performs equally without a complexity cost. |
| H10 | Useful governance capability compounds without catastrophic forgetting or harmful negative transfer. | Later-generation gains require prior-world regression or increased inherited-state harm. |

## 2. Repository baseline, import rule, and clean-results rule

### 2.1 Verified starting state

The target repository is `MAVS-RESEARCH/MAVS-Self-Learning-1A`. Its clean planning checkpoint is commit `13629bb` (`docs: add self-learning implementation plan`), containing only `LICENSE`, `WorkPlan.md`, and `Path.md`; it has no Chapter 10D source tree and no active results. Commit `58b35c3` is the target repository's initial `LICENSE` commit.

Phase 0 must therefore import the verified Chapter 10D source foundation into this target repository. The first code-bearing implementation commit must be a provenance-only import checkpoint: it records the exact upstream URL and SHA, excludes upstream results and successor planning documents, and changes no imported behavior. The next implementation commit may introduce successor namespace/documentation changes. Only later commits may add Self-Learning behavior. This preserves the specification's clone-before-behavior invariant even though the target already contains its two planning/bootstrap commits. Upstream `WorkPlan.md` and `Path.md` must not overwrite these successor documents.

### 2.2 Previous-result removal

The inspected Chapter 10D upstream includes committed output under `results/raw`, `results/processed`, `results/figures`, and `results/reports`, including a large historical failure-card corpus. Those are reference results, not results of this successor implementation, and must not be imported into the target's active results tree.

The import procedure will:

- copy/import all protected source, tests, configs, and reproducibility inputs;
- exclude every upstream file under `results/`;
- create only empty result directories with `.gitkeep` files where needed;
- add `scripts/clean_results.py`, which resolves and verifies the target path is the repository's own `results/` directory before deleting generated children;
- require `--run-id` and a run manifest for every experiment;
- refuse to aggregate traces whose git SHA, config hash, ledger hash, or run ID does not match the selected run;
- keep immutable ledgers, participant checkpoints, and published artifacts only when they were generated by the current successor repository and are explicitly selected for retention;
- run the cleaner before the first new experiment and record the empty-tree check in `Path.md`.

No destructive history rewrite is required. Cleanup concerns result artifacts, not git history.

### 2.3 Provenance import and regression sequence

Phase 0 must make the following sequence real, substituting only a pre-recorded immutable upstream SHA and an isolated temporary clone path:

```bash
git clone https://github.com/MAVS-RESEARCH/MAVS-Chapter-10D.git <temporary-chapter-10d-clone>
git -C <temporary-chapter-10d-clone> checkout <recorded-upstream-sha>
python -m pip install -e <temporary-chapter-10d-clone>[dev]
python <temporary-chapter-10d-clone>/scripts/run_experiment.py --config <temporary-chapter-10d-clone>/configs/experiments/synthetic_smoke.yaml
python <temporary-chapter-10d-clone>/scripts/validate_traces.py --input <temporary-chapter-10d-clone>/results/raw/synthetic_smoke.jsonl
python -m pytest -q <temporary-chapter-10d-clone>/tests
```

Only after all three regression gates pass may Phase 0 import the upstream tracked tree, excluding `.git/`, `results/`, upstream `WorkPlan.md`, and upstream `Path.md`. The provenance commit stores upstream URL/SHA, source tree hash, excluded-path manifest, Python/package versions, command outputs, smoke trace hash, and test counts. The same commands then run against the imported target tree before any namespace or behavioral change.

## 3. Target file architecture

The final architecture extends the real Chapter 10D package rather than creating a parallel toy implementation.

```text
.
|-- LICENSE
|-- README.md
|-- REPRODUCIBILITY.md
|-- CLAIMS.md
|-- WorkPlan.md
|-- Path.md
|-- pyproject.toml
|-- Makefile
|-- docs/
|   |-- baseline_sources.md
|   `-- model_cards/<method_or_component>.md
|-- configs/
|   |-- baselines/                         # inherited plus new faithful adapters
|   |-- experiments/                       # inherited configs retained as regression fixtures
|   |-- suites/self_learning_300k.yaml
|   |-- phases/phase0.yaml ... phase5.yaml
|   |-- worlds/*.yaml
|   |-- methods/*.yaml
|   |-- training/*.yaml
|   `-- ablations/A00.yaml ... A49.yaml
|-- schemas/
|   |-- world_manifest.schema.json
|   |-- decision_trace.schema.json
|   |-- participant_state.schema.json
|   |-- learning_event.schema.json
|   |-- diagnostic_proposal.schema.json
|   |-- candidate_configuration.schema.json
|   |-- certification_report.schema.json
|   `-- update_decision.schema.json
|-- src/mavs10d/
|   |-- core/                              # inherited contracts, runner, seeds, hashing, traces
|   |-- envs/                              # inherited adapters plus randomized compiler
|   |-- corruption/                        # schedules, families, composers, adversarial responder
|   |-- specialists/                       # heterogeneous/frozen/trainable proxy specialists
|   |-- governance/
|   |   |-- mavs_gc.py
|   |   |-- ds_cf.py
|   |   `-- self_learning/
|   |       |-- controller.py
|   |       |-- memory.py
|   |       |-- ontology.py
|   |       |-- meta_diagnostics.py
|   |       |-- failure_attribution.py
|   |       |-- diagnostic_grammar.py
|   |       |-- proposal_engine.py
|   |       |-- validator.py
|   |       |-- safety_kernel.py
|   |       |-- config_library.py
|   |       |-- selector.py
|   |       |-- consolidation.py
|   |       `-- rollback.py
|   |-- baselines/                         # all mechanism-family adapters
|   |-- training/                          # strict train/dev/blind separation
|   |-- metrics/                           # safety, burden, dynamics, transfer, frontier, stats
|   `-- reports/                           # figures, tables, cards, genealogy, claim audit
|-- scripts/
|   |-- clean_results.py
|   |-- train_component.py
|   |-- evaluate_blind_models.py
|   |-- validate_data_separation.py
|   |-- compile_generation_ledgers.py
|   |-- run_suite.py
|   |-- run_three_generation_suite.py
|   |-- consolidate_library.py
|   |-- validate_generation_resets.py
|   |-- validate_participant_state.py
|   |-- validate_traces.py
|   |-- validate_updates.py
|   |-- aggregate_results.py
|   |-- analyze_cross_generation.py
|   `-- make_report.py
|-- tests/
|   |-- unit/
|   |-- integration/
|   |-- metamorphic/
|   |-- leakage/
|   `-- statistical/
`-- results/
    |-- manifests/generation_{1,2,3}/
    |-- checkpoints/generation_{1,2,3}/
    |-- raw/<run_id>/
    |-- processed/<run_id>/
    |-- figures/<run_id>/
    `-- reports/<run_id>/
```

## 4. Contracts and invariants that precede experimentation

The code must define typed, serializable contracts for `WorldSpec`, `Observation`, `CandidateAction`, `GovernanceMethod`, `LearningEvent`, `DiagnosticProposal`, `CandidateConfiguration`, `CertificationReport`, and `UpdateDecision`.

The active governance configuration must also be represented explicitly and without dropped fields as `eta_t = (G_t, A_t, W_t, P_t, Theta_t, tau_hard_t, alpha_t, lambda_t, delta_t, theta_0_t, tau_G_t, S_t)`. `ActiveGovernanceConfiguration` will serialize every component with its architecture-authority definition, type, bounds, parent configuration, version, approval status, config hash, and activation scope. Phase 0 must resolve and document the semantic meaning of every symbol against the architecture authority before implementation; symbols may not be silently renamed, merged, or treated as an untyped parameter dictionary. `S_t` is the governed selector. The fast loop may read only an approved `eta_t`; a proposed `eta_hat` cannot affect live decisions until retained replay, disjoint holdout, adversarial, counterfactual, scope, invariant, shadow, Pareto, trace-integrity, and rollback tests pass.

The new-contract field floor is:

| Contract | Mandatory implementation content |
|---|---|
| `WorldSpec` | Domain, label process, transition kernel, observability, feedback delay/censorship/reliability, corruption generator, policy version process, visible projection, hidden-state hash. |
| `LearningEvent` | Trigger, trace IDs, attributed mechanism, candidate operations, evidence sufficiency, feedback provenance/reliability. |
| `DiagnosticProposal` | Name, intended scope, explicit bounded function, threshold, allowed influence, invariants, lineage, provenance, validation plan. |
| `CandidateConfiguration` | Parent ID, exact delta, proposal bundle, expected gains/failures, protected metrics/families, rollback target. |
| `CertificationReport` | Trigger replay, retained replay, disjoint temporal holdout, boundary/counterfactual tests, independent adversarial search, scope and invariant audits, shadow results, Pareto deltas, compute, hashes, pass/fail reasons. |
| `UpdateDecision` | Promote/reject/quarantine/rollback, exact reason codes, activation scope, fallback, monitoring conditions, effective time, signer/hash. |

Mandatory trace categories are:

- **World:** world ID, generator version, visible regime features, hidden regime hash, policy version, corruption-family hash.
- **Decision:** method/config ID, action, risk, severity, threshold, consensus, witnesses, reason codes, compute cost.
- **Specialists:** outputs, calibration, provenance/source, independence estimate, corruption exposure, latency.
- **Diagnostics:** all signals, scope match, contribution, IDI/UDI proxies, meta-diagnostic state, counterfactual probes.
- **Outcome:** ground truth when released, delay, source reliability, terminal error flags, downstream cost.
- **Learning:** trigger, cluster, attribution, proposal, parent, certification suite, promotion/rejection, rollback.
- **Integrity:** complete seed tuple, git SHA, config hash, trace hash, timestamp, environment-package versions.
- **Generation:** generation ID/reset class/seed range/manifest hash/prior and consolidated library hashes.
- **Participant state:** condition, persistence eligibility, checkpoint, retained bytes, component hashes, forbidden-state audit.
- **Transfer:** inherited IDs used, fresh counterfactual, paired transfer delta, negative-transfer flag.
- **Consolidation:** merge/deprecate/prune/recalibrate action, marginal value, replay evidence, complexity delta, rollback target.

The immutable safety kernel must enforce: uncertified candidates cannot control decisions; hard veto dominance; bounded mitigation; presence is not harmfulness; raw presence, confidence inflation, or missing evidence alone cannot create a hard veto unless separately certified under an explicit named scope; scope-bounded influence; monotone certified danger semantics; zero retained-set unsafe acceptance for promotion in the fully labeled core; complete traces; rollback for every promotion; permanent retained counterexamples unless formally superseded; selector fallback/escalation under low applicability; provenance and reliability tags for learning feedback.

### 4.1 Exact world-compiler contract

Phase 0 implements the following pre-registered defaults in `configs/worlds/generator_defaults.yaml`; alternative development priors must be explicitly versioned, while final priors are sealed and different from development priors.

| Dimension | Required default and allowed dynamics |
|---|---|
| Domain | Sample from text safety, tool use, cyber triage, medical-triage proxy, financial-approval proxy, multi-agent operations, synthetic control, and retrieval QA; acceptance runs use at least five. Domains may switch at hidden change points. |
| Horizon | Sample integer 80-320 decisions per episode. |
| Unsafe prevalence | Sample from `Beta(1.2, 3.0)` and enforce the benchmark support `0.01-0.70`; permit abrupt prior shifts, cycles, and adversarial bursts. |
| Feedback | Mixture: immediate `0.45`, geometric-delay mean 8 `0.35`, censored `0.20`; phase configs may add sparse/noisy/reliability variants without exposing unreleased labels. |
| Policy process | Hidden Markov process with 1-4 states; clauses, cost matrix, required evidence, hard constraints, and announced/hidden grace periods may change. |
| Specialists | Sample count 3-9, diversity `Uniform(0.15,0.95)`, shared-source probability `Uniform(0,0.80)`; manifest competence, calibration, latency, fatigue, recovery, specialization swap, maliciousness, and shared collapse. |
| Corruption | Sample 1-5 families per world; schedule from piecewise, random walk, burst, recurring, adversarial-response, or compositional; target input/evidence/specialist/provenance/policy/feedback; randomize onset, duration, intensity, interaction, and recovery. |
| Observability | Full/masked/noisy evidence, delayed provenance, contradictory metadata, disappearing/late evidence packets. |
| Cost landscape | Unsafe, false-rejection, escalation, latency, and intervention costs; preference vectors may change across episodes. |
| Temporal dynamics | Stationary, gradual, abrupt, recurring, chaotic switching, recovery trap, irreversible consequences; change points remain hidden. |

The compiler uses suite -> generation -> world -> episode -> step -> method seeds; stores all latent parameters in the signed hidden manifest; exposes only the designated `Observation`; and passes leave-generator-out testing using at least one independent generator implementation.

## 5. Three-generation experimental structure

Each generation runs Phases 0-5 on an independently compiled 100,000-opportunity ledger.

- **Generation 1 - discovery:** all adaptive methods cold-start; establish discoverability and certified reusable knowledge.
- **Generation 2 - transfer and acceleration:** cumulative variants load certified/consolidated G1 state; fresh variants restart on the identical G2 ledger.
- **Generation 3 - compounding and adversarial recombination:** cumulative variants load consolidated G2 state; fresh variants restart; structural and adversarial resets intensify.

Generation seed ranges are pre-registered as G1 `[100000,199999]`, G2 `[300000,399999]`, G3 `[500000,599999]`; final blind evaluation uses `[900000,999999]`. The seed hierarchy is suite -> generation -> world -> episode -> step -> method.

At every generation boundary, regenerate domain identities/adapters/features/data, prevalence/labels/boundaries/policies/costs, specialists and shared-failure structure, corruption mixture and attacker schedules, observability and evidence masking, feedback delay/censorship/reliability, transition kernels/change points/consequences, hidden causal parameters, and final holdout packages/hashes.

Paired participant conditions are mandatory: MAVS-SL cumulative, MAVS-SL fresh, MAVS-SL frozen-after-G1, adaptive-baseline cumulative, adaptive-baseline fresh, fixed baseline, and raw-memory control. Later-generation cumulative and fresh conditions always replay the same canonical ledger.

Checkpoints are `t={0,1000,5000,10000,25000,50000,75000,100000}`. The `t=0` shadow bank measures pure inherited-state transfer before new feedback. Windows 1-1,000, 1,001-10,000, 10,001-50,000, and 50,001-100,000 measure cold-start loss, learning acceleration, reuse/negative transfer, and mature frontier/recurrence respectively.

After G1 and G2, consolidation occurs before any next-generation data is visible. It audits marginal value, redundancy, instability, leakage, merges/deprecates/prunes with genealogy, recalibrates only from released prior data, replays sealed retention banks, freezes and hashes the library/selector/ontology/memory/kernel version, and reports active/total library sizes and costs. Consolidation changes pass the same certification and rollback gates as online proposals.

### 5.1 Participant-state persistence matrix

`ParticipantState` and `validate_participant_state.py` must enforce the matrix below field-by-field and byte-for-byte. Every later-generation adaptive method receives a cumulative and fresh condition on the same ledger; methods may retain only state that belongs to their documented mechanism.

| State class | Cumulative MAVS-SL | Fresh MAVS-SL | Adaptive baselines | Fixed baselines |
|---|---|---|---|---|
| Certified diagnostics/scopes | Retain approved functions, thresholds, intended scopes, quality records, and genealogy. | Reset to seed diagnostic set. | Retain analogous learned state only if defined by the baseline. | No learned state. |
| Configuration library/selector | Retain approved configurations, validity regions, selector state, fallback rules, and rollback graph. | Reset library/selector. | Adaptive conformal, online experts, drift selectors, bandits, CTTA, and safe-control policies retain only legitimate state. | Reuse frozen configuration unchanged. |
| Ontology/capsules | Retain abstract mechanisms, compressed signatures, response records, and certification history. | Reset to initial ontology. | Retain method-equivalent summaries only where part of the mechanism. | Not applicable. |
| Raw examples/hidden data | Raw traces may exist only in sealed audit/retention archives; exact-match answer-key use and future-parameter access are prohibited. | No prior examples. | Same restriction and matched storage budget. | Not applicable. |
| Calibration/update buffers | Retain only when explicitly part of the method; report size, contents, age, and hashes. | Reset. | Retain according to baseline definition under matched storage limits. | No adaptive buffer. |
| Compute/storage | Charge consolidation, retrieval, selection, updates, calls, tokens, latency, wall time, and bytes. | Charge fresh learning. | Charge identically. | Report inference cost. |

Required conditions are cumulative MAVS-SL, fresh MAVS-SL, frozen-after-G1 MAVS-SL, cumulative/fresh adaptive baselines, fixed baselines, bounded raw-memory control, no-consolidation control, no-persistence control, unlimited-memory diagnostic upper bound, and matched-memory cumulative baselines.

### 5.2 Reset taxonomy and sealed generation mixture

| Reset | Changes | Purpose |
|---|---|---|
| Surface | Names, encodings, wording, presentation, labels, formatting, nuisance variables; the deep mechanism may remain isomorphic. | Test representation-invariant reuse and defeat identifier memorization. |
| Structural | Causal graph, specialist dependencies, evidence channels, policy interactions, feedback topology, and corruption composition. | Test transfer beyond superficial similarity. |
| Adversarial | Independent generator targets inherited-library weaknesses under a fixed attack budget: scope collisions, spoofed witnesses, masking, conflicts, misleading agreement, and timed shifts. | Test robust abstraction without reusing development attacks. |

G1 emphasizes discovery; G2 uses a pre-registered balanced mix of transferable, recombined, and novel mechanisms; G3 increases structural and adversarial resets. Exact proportions and attack budgets are frozen in hidden manifests before participant execution and are unavailable to all methods.

### 5.3 Cross-generation estimands and code semantics

`metrics/transfer.py` must implement these equations directly, with paired cumulative/fresh decisions from the identical ledger. `J` is the pre-registered higher-is-better constrained governance objective; every component metric is also reported separately so scalarization cannot hide safety or burden regressions.

| Estimand | Exact implementation |
|---|---|
| `FWT_g` | `J(cumulative_g) - J(fresh_g)` on identical G2/G3 worlds. |
| `CSR_g` | `early_loss(fresh_g) - early_loss(cumulative_g)` using the pre-registered early window. |
| `LA_g` | `TTR_fresh,g / TTR_cumulative,g`, with the analogous TTD ratio; report undefined/zero denominators explicitly. |
| `DRR_g` | Successful governed cases using inherited diagnostics divided by successful cases eligible for inherited coverage. |
| `NDY_g` | New diagnostic candidates surviving full certification divided by candidates proposed. |
| `NTR_g` | Paired probability that inherited state worsens a decision relative to fresh, with mechanism-level audit. |
| `CGI_g` | Protected prior-family performance regression after new updates, evaluated on sealed banks. |
| Retention score | Performance of consolidated `L_g` on sealed prior-generation banks with pre-registered non-inferiority margins. |
| Library efficiency | Objective/frontier gain divided by active diagnostic and configuration complexity, also reporting retrieval/consolidation cost. |
| Generation improvement slope | Paired G1->G2->G3 slope for UAR, FRR, burden, regret, TTD/TTR, recurrence, and hypervolume; never infer compounding from a final mean alone. |

### 5.4 Mandatory suite configuration and outputs

`configs/suites/self_learning_300k.yaml` must encode, validate, and freeze: suite name `mavs_self_learning_300k`; `generations: 3`; `canonical_decisions_per_generation: 100000`; `canonical_decisions_total: 300000`; `replay_all_methods: true`; G1/G2/G3 and final seed ranges from Section 5; every reset dimension from Section 5; every participant condition and persistence prohibition from Section 5.1; `consolidation_after_each_generation: true` where a next generation exists; the eight checkpoints; phase budgets `{5000,15000,20000,20000,25000,15000}`; seed hierarchy; post-holdout-tuning prohibition; and immutable output schemas.

Logical outputs are generation ledgers, participant checkpoints, G1/G2 consolidation reports, raw decision/update traces, failure/update cards, final summary, cross-generation summary, and frontiers. Physical paths are the specification paths namespaced by `<run_id>` to prevent stale-result mixing: `results/manifests/<run_id>/generation_{g}/world_ledger.parquet`, `results/checkpoints/<run_id>/generation_{g}/`, `results/reports/<run_id>/consolidation/generation_{g}/`, `results/raw/<run_id>/`, `results/processed/<run_id>/{final_summary,cross_generation_summary,frontiers}.parquet`, and `results/reports/<run_id>/{failure_cards,update_cards}/`. The run manifest maps each namespaced path back to the specification's logical artifact name.

## 6. Model-training and anti-overfitting policy

### 6.1 Default stance

No large foundation model must be trained for the core claim. The primary Self-Learning mechanism uses explicit, bounded diagnostic grammar and certified configuration search. Any learned model is optional and must be isolated behind the same contracts and budgets.

Potentially trained components are:

- lightweight specialist proxy classifiers used by synthetic/domain adapters;
- calibration models and conformal scores;
- selector/applicability models;
- novelty, scope, or failure-attribution models when a nonparametric implementation is insufficient;
- predictor-adaptation models required by CTTA/test-time-adaptation baselines;
- preference-conditioned or safe-control policies used by faithful baseline adaptations.

### 6.2 Required split discipline

For every trained component, produce a model card containing dataset/world generator version, examples and families used, feature visibility, seed range, training code/config, hyperparameters, checkpoint hash, compute, training curves, calibration set, and known limitations.

Training/tuning may use only the dedicated development world bank and its released labels. Certification uses separate replay, development holdout, boundary, and adversarial banks. Final evaluation uses entirely different benchmark instances: disjoint seeds, altered generator priors, held-out domains, held-out corruption families/compositions, surface reset, structural reset, adversarial library-targeting reset, leave-generator-out worlds, and sealed prior-generation retention banks. Final blind ledgers are created/frozen after implementations and hyperparameters are frozen. No final-holdout sample may be used for early stopping, calibration, threshold selection, proposal synthesis, model selection, or debugging.

The phrase **entirely different from training benchmarks** is enforced as follows:

- no shared world, episode, step, seed, example ID, surface template, policy instance, or corruption schedule;
- held-out generator priors and at least one independent generator implementation;
- domain leave-one-out and corruption leave-family/composition-out tests;
- structural resets that change causal/evidence topology, not just names;
- exact-match and near-duplicate audits across raw inputs, embeddings, manifests, and participant memory;
- frozen final suite hashes published before execution;
- separate code paths/credentials for visible development manifests and hidden final manifests;
- final failures remain in the report and cannot trigger retuning.

### 6.3 Training benchmarks versus brutal evaluation benchmarks

- **Training/development benchmarks:** generated development worlds; calibration splits; repair curricula with disclosed families; baseline-specific tuning grids.
- **Certification benchmarks:** originating-trigger replay, retained counterexamples, temporal holdout, boundary neighborhoods, nuisance-preserving counterfactuals, independent adversarial search, scope audit, invariant audit, shadow replay.
- **Final brutal benchmarks:** untouched Phase 4 world bank (>=500 matched worlds), Phase 5 altered-prior/cross-domain/composition holdouts, three-generation fresh-vs-cumulative ledgers, structural and adversarial resets, sealed retention banks, and independent final seed range.

Every trained component must report train/development performance only as diagnostic evidence. Acceptance is determined exclusively by certification and final-brutal benchmarks. Large train-to-final gaps, seed sensitivity, scope leakage, calibration deterioration, or a baseline win are reported, not hidden.

### 6.4 Per-model training recipes and resultant benchmarks

No model may be trained merely because a learned implementation is convenient. Phase ownership, training necessity, architecture, feature visibility, objective, optimizer, grid, early-stopping split, seed range, and blind benchmark must be frozen in `configs/methods/` and the model card before final ledgers are compiled. The following recipes are the implementation defaults; a fidelity-driven deviation requires a documented source, exact reason, equivalent or stronger separation, and a WorkPlan/`Path.md` deviation record.

Training implementation lives in `src/mavs10d/training/{datasets,train_component,calibration,evaluate_blind,leakage_audit}.py`; command wrappers are `scripts/{train_component,evaluate_blind_models,validate_data_separation}.py`; per-component recipes are `configs/training/*.yaml`; immutable model cards are written to `docs/model_cards/`. Dataset builders emit train/development-validation/calibration/certification/final manifest hashes and refuse overlapping seed, world, episode, step, example, template, policy, schedule, generator, or near-duplicate identities.

| Component | Training implementation | Development/tuning | Entirely different brutal evaluation and required result |
|---|---|---|---|
| Synthetic/domain specialist proxy | Compare L2 logistic regression (`C={0.01,0.1,1,10}`) with a two-hidden-layer MLP (`64,64`, ReLU, Adam, `lr={1e-4,3e-4,1e-3}`, batch 256, max 100 epochs). Train on development-world visible features only; early-stop on a disjoint development validation bank using lexicographic UAR then Brier/ECE. Freeze weights before certification. | Report class/family counts, learning curves, calibration, per-domain UAR/FRR, worst seed, checkpoint hash, and five training seeds. | Held-out domains, altered label priors/policies, unseen corruption families/compositions, structural reset, leave-generator-out, and seeds `[900000,999999]`; report UAR/FRR, calibration, worst-world/CVaR, shift gap, and confidence intervals. A proxy failing its pre-registered fidelity/calibration floor is excluded or retained as a named weak baseline, never silently repaired on final data. |
| Calibration/conformal model | Platt logistic and isotonic calibration are fitted only on matched calibration banks; split-conformal/CRC scores use separate calibration examples. No score may be refitted from tournament labels. | Select calibration method/alpha on development calibration and validation banks; publish calibration counts and score distributions. | Altered-prior, delayed/noisy-feedback, held-out-domain, structural-reset, and final blind banks; report ECE/Brier, empirical risk/coverage, UAR/FRR, rare-event bounds, and adaptation/recovery lag. |
| Configuration selector/applicability | Start with multinomial L2 logistic regression; compare depth-2/3/4 gradient-boosted trees only if the pre-registered development bank supports them. Inputs are visible context and certified-library metadata; targets are best certified configurations under the lexicographic objective. | `C={0.01,0.1,1,10}` or tree count `{50,100,200}`, learning rate `{0.03,0.1}`, five seeds; stop on disjoint selector validation using unsafe-choice count first, then regret and calibration. | t=0 shadow banks, unseen domains/policies, surface/structural/adversarial resets, G2/G3 cumulative-vs-fresh ledgers; report selector accuracy, unsafe selection, fallback/escalation, regret, negative transfer, and scope leakage. |
| Novelty/scope/failure attribution | Default to auditable k-nearest/prototype/residual statistics. If insufficient, use a depth-limited gradient booster (`depth={2,3,4}`, trees `{50,100,200}`) trained on released development outcomes; it may rank causes but cannot bypass the safety kernel. | Tune on disclosed repair curricula with mechanism-disjoint validation curricula; report attribution top-k accuracy, false trigger rate, calibration, and feature provenance. | Hidden-mechanism curricula, unseen corruption compositions, nuisance-preserving counterfactuals, independent adversarial search, cross-domain and leave-generator-out worlds; report TTD/TTR, proposal yield, harmful proposal rate, scope leakage, and transfer. |
| CTTA/test-time-adaptation baseline | Source predictor is the frozen `64,64` MLP above. Implement entropy-minimization and confidence-filtered pseudo-label updates with `lr={1e-5,1e-4,1e-3}`, confidence `{0.8,0.9,0.95}`, update frequency `{1,8,32}`, plus reset and recovery variants. | Select on development shift bank only, with matched feedback/call/compute budget and no hidden labels. | Recurring, recovery-trap, censored-feedback, policy-boundary, structural-reset, poisoning, and final tournament banks; report UAR/FRR, calibration, adaptation/recovery, forgetting, compute, and catastrophic episodes. |
| Online expert/bandit selector | Implement Hedge/Exponentiated Weights over frozen governance policies (`eta={0.01,0.05,0.1,0.2}`) and a contextual bandit selector with pre-registered exploration `{0.01,0.05,0.1}`. Updates use released feedback only. | Tune learning/exploration on the development stream and freeze grids before holdout. | Identical canonical tournament ledgers with delay/censorship, recurring regimes, changed preferences, and G2/G3 cumulative/fresh conditions; report governance/dynamic regret, UAR/FRR, burden, recovery, state bytes, and compute. |
| Preference-conditioned Pareto/safe-control policy | Use a tabular policy where state support permits; otherwise a two-layer `64,64` policy/value network. Implement weighted scalarization, epsilon-constraint, IPRO-style Pareto-set construction, preference conditioning, Lagrangian constrained policy, safety critic, and shielded policy. Adam `lr={1e-4,3e-4,1e-3}`, five seeds; constraint multipliers and preference vectors are development-only. | Select validated non-dominated checkpoints on a dedicated development world bank; unsafe-constraint violations reject a checkpoint regardless of reward. | Untouched >=500-world tournament, new preference/cost vectors, irreversible sequences, held-out domains/corruptions, adversarial resets, and blind seeds; report full frontiers, constraint violations, hypervolume/epsilon indicator, regret, worst-world/CVaR, compute, and confidence intervals. |

All training code writes checkpoints outside final result directories until frozen, records package/hardware versions, and runs five or more pre-registered training seeds. Test code must prove that final manifests, blind labels, retention-bank answers, and final metrics are unavailable to trainers, calibrators, early stopping, proposal synthesis, and hyperparameter selection.

### 6.5 Exact baseline implementation inventory

The following are required named benchmark adaptations, not optional examples. Every file implements the common `GovernanceMethod` contract, has mechanism-fidelity and hidden-information tests, declares calibration/call/token/latency/memory/update budgets, and exposes its full development sweep over every applicable threshold, window size, learning rate, abstention penalty, preference vector, exploration parameter, and update frequency. Selection uses a dedicated development world bank and lexicographic safety constraints. Author code is preferred when compatible; otherwise the report labels the implementation a faithful benchmark adaptation and documents deviations.

| Family | Required implementations and files |
|---|---|
| Trivial/oracle bounds | `baselines/trivial.py`: accept-all, reject-all, escalate-all, random. `baselines/oracle.py`: oracle-label and oracle-regime diagnostic bounds, excluded from competitive claims. |
| MAVS lineage | Original MAVS-GC, DS-CF, fixed full MAVS, and context-selected fixed configurations in governance adapters with regression fixtures. |
| Confidence/selective | `confidence_gate.py` and `selective.py`: confidence, entropy, margin, reject option, generalized selective classification. |
| Neyman-Pearson/cost-sensitive | `neyman_pearson.py`: risk-constrained threshold, likelihood-ratio selective rule, and cost-sensitive classifier. |
| Conformal | `conformal.py`, `online_conformal.py`: split conformal, conformal risk control, adaptive conformal, online conformal, distribution-informed online conformal, and retrospective-adjustment variant where faithfully supportable. |
| Ensemble uncertainty | `uncertainty.py`, `self_consistency.py`: disagreement, variance, mutual-information proxy, deep-ensemble gate, and self-consistency. |
| Guardrails/validators | `rails.py`, `validators.py`: policy rails, validator stack, schema guards, and tool-use guards. |
| Critique/verifier | `critique_revise.py`, `judge.py`, `verifier.py`, `debate.py`: critique-revise, single judge, verifier cascade, and bounded debate. |
| Drift adaptation | `drift.py`: ADWIN and Page-Hinkley detection with threshold reset plus change-point configuration selector. |
| Online experts/bandits | `online_experts.py`: Hedge/Exponentiated Weights and contextual-bandit selection over fixed policies. |
| Test-time adaptation | `test_time_adaptation.py`: entropy and pseudo-label CTTA proxies with reset and recovery variants. |
| Multi-objective/Pareto | `pareto_morl.py`: weighted scalarization, epsilon-constraint, IPRO-style Pareto set, and preference-conditioned policy. |
| Safe control/constrained RL | `safe_control.py`: Lagrangian constrained policy, safety critic, and shielded policy. |
| Full MAVS-SL | Certified diagnostic synthesis, scoped memory, safety kernel, configuration library, governed selector, consolidation, and rollback. |

### 6.6 Baseline source and fidelity registry

`docs/baseline_sources.md` must link each implementation/config/test to its governing source and record whether it uses author code or a benchmark adaptation. The minimum registry covers: Chapter 10D; the DS-CF implementation document; Diagnostic Sciences/MAVS-GC perception-extension theory; Conformal Risk Control; generalized selective classification under distribution shift; likelihood-ratio selective classification; distribution-informed online conformal prediction; retrospective-adjustment online conformal inference; continual test-time domain adaptation and reset/recovery variants; IPRO/Divide-and-Conquer Pareto-front construction; Pareto Set Learning; and the relevant NeMo Guardrails, Guardrails AI, OpenAI Evals, Constitutional AI, HELM Safety, and CyberSecEval documentation. Every adaptation records source version/commit, mechanism preserved, unavoidable deviations, information budget, tuning grid, and fidelity tests. Source names motivate mechanism coverage; they do not justify claiming identity with author implementations unless author code is actually used.

## 7. Phase 0 - Clone qualification and measurement integrity (5,000 decisions per generation)

### Scope

Import and lock the Chapter 10D foundation, clear inherited results, reproduce the original smoke path, establish deterministic matched replay, typed schemas, hashing, leakage barriers, randomized world compilation, metric identities, and trivial/oracle diagnostic bounds. Phase 0 makes no Self-Learning superiority claim.

### Files made or changed

- import inherited `src/mavs10d/{core,envs,corruption,specialists,governance,metrics,reports,training,baselines}` and its tests/configs;
- `REPRODUCIBILITY.md`, `CLAIMS.md`, updated `README.md`, `Makefile`;
- `configs/suites/self_learning_300k.yaml`, `configs/phases/phase0.yaml`, initial `configs/worlds/*.yaml`;
- all schemas listed in Section 3;
- `scripts/clean_results.py`, `compile_generation_ledgers.py`, `validate_generation_resets.py`, `validate_participant_state.py`, upgraded trace/update validators;
- `src/mavs10d/envs/world_compiler.py`, `world_ledger.py`;
- `src/mavs10d/corruption/composer.py`, `adversarial_schedule.py`;
- `src/mavs10d/metrics/{burden,frontier,transfer}.py` and extensions to stats;
- Phase 0 unit, integration, metamorphic, leakage, determinism, and statistical tests.

### Code and coding method

1. Record target and upstream SHAs; import source without upstream result files.
2. Run the result cleaner and assert only allowed placeholders exist.
3. Preserve inherited public interfaces; extend using new dataclasses/protocols and registry entries.
4. Derive all randomness from explicit hierarchical seed objects; prohibit module-global RNG.
5. Compile immutable Parquet ledgers plus signed JSON manifests; hash row order, schema, generator package, configs, and hidden parameters.
6. Provide separate visible observations and hidden world state; test that methods cannot import/access hidden manifests.
7. Implement property/metamorphic tests: method-order invariance, replay identity, permutation invariance where intended, exact metric recomputation, action accounting, delayed-feedback causality, and no future reads.
8. Validate accept-all, reject-all, escalate-all, random, oracle-label, and oracle-regime bounds; oracle methods are diagnostics only and excluded from competitive claims.

### Decision allocation and benchmarks

- 1,000 inherited static regression decisions;
- 2,000 generated-world decisions;
- 2,000 trace/metric metamorphic decisions;
- the original Chapter 10D smoke/test suite runs before and after the package.

### Exit gate

Zero trace/schema/hash errors; byte- or field-equivalent deterministic replay as applicable; metric identities hold; matched methods receive identical visible opportunities; hidden-state access tests pass; original smoke/tests pass; result tree contains no inherited outputs; generation manifest and reset validator pass.

## 8. Phase 1 - Non-stationary distribution gauntlet (15,000 decisions per generation)

### Scope

Test fixed and legitimately adaptive methods under unknown prior/covariate shift, policy/label-boundary changes, recurring regimes, delayed/censored/noisy feedback, recovery, and changing cost preferences. Corruption is present but not yet maximally adversarial.

### Files made or changed

- `configs/phases/phase1.yaml` and shift/recovery world configs;
- schedule implementations for piecewise hidden, gradual random walk, burst, recurring regime, adversarial-response, compositional, and recovery-trap schedules;
- environment adapters for at least text safety, tool use, cyber triage, medical/financial proxies, multi-agent operations, synthetic control, and retrieval QA (at least five used in acceptance runs);
- baseline adapters/configs for confidence/entropy/margin/selective gates, Neyman-Pearson/cost-sensitive rules, split conformal/CRC/adaptive/online conformal, drift detection, online experts, CTTA, and context-selected fixed configurations;
- calibration, lag, regret, burden, and configuration-switch metrics and tests.

### Code and coding method

- Implement each baseline through the common `GovernanceMethod` interface and document the faithful mechanism, deviations, and information requirements.
- Tune only on the development world bank using pre-registered grids and lexicographic safety constraints.
- Charge calibration size, calls, tokens, latency, wall time, memory, and update compute.
- Replay frozen chosen configurations on disjoint phase worlds; prohibit post-holdout retuning.
- Treat delayed/censored feedback as unavailable, never as a negative label.
- Test recovery so methods are penalized for remaining unnecessarily conservative after corruption ends.

### Decision allocation and benchmarks

Five domains x 30 worlds x approximately 100 decisions = 15,000. Balance abrupt, gradual, recurring, and mixed shifts. Training/tuning worlds and test worlds use disjoint seeds and changed priors.

### Exit gate and outputs

Report UAR/FRR/escalation frontiers, adaptation and recovery lag, calibration, catastrophic episode rate, governance/dynamic regret, selector accuracy, compute-normalized behavior, worst-decile and worst-world results. No method may gain hidden information. Later generations must include cumulative/fresh variants for every legitimately adaptive baseline.

## 9. Phase 2 - Corruption, correlated collapse, and partial observability (20,000 decisions per generation)

### Scope

Brutally test shared wrong premises, provenance concentration/collapse, safe correlated agreement, harmful correlated collapse, ambiguity, evidence masking, overconfident consensus, policy conflict, malicious specialists, prompt/adversarial manipulation, label/feedback poisoning, and two-to-four-family compositions.

### Files made or changed

- `configs/phases/phase2.yaml`, corruption-family and composition configs;
- corruption transforms/composers for at least ten families and at least twenty required compositions (target >=40 in this phase);
- `governance/ds_cf.py` and regression fixtures for presence/harm/safe/ambiguity semantics;
- provenance, independence, masking, safe/danger witness, conflict, fragility, feedback reliability, and evidence-source compromise diagnostics;
- counterfactual drop-one, alternate-view, evidence-order, boundary, and recovery tests;
- corruption schedule/state-transition unit and property tests.

### Code and coding method

- Separate correlation presence from certified harmfulness; raw presence alone cannot hard-veto.
- Require conjunctive danger evidence for hard veto, keep mitigation bounded, and escalate genuine ambiguity.
- Generate specialist competence/diversity/provenance/fatigue/recovery/maliciousness from manifests, but expose only allowed observations.
- Compose corruptions with randomized onset, duration, intensity, target, interaction, and recovery.
- Generate counterfactual pairs that preserve nuisance factors while varying causal evidence availability.
- Quarantine poisoned/censored feedback subsets via reliability metadata.

### Decision allocation and benchmarks

20,000 canonical opportunities with >=40 compositions; approximate mixture: 30% safe correlated agreement, 30% harmful collapse, 20% ambiguous masking, 20% mixed. Final Phase 2 families/compositions differ from development by seeds, schedules, intensities, combinations, and held-out mechanisms.

### Exit gate and outputs

Zero raw-correlation-only vetoes; measured collapse sensitivity, masked-evidence behavior, counterfactual fragility, ambiguity escalation, recovery, and retained safety. Any unsafe acceptance or false rejection produces trace lineage and a failure card. DS-CF regressions must remain solved; evidence absence and evidence unavailability must not be conflated.

## 10. Phase 3 - Autonomous failure discovery and self-repair (20,000 decisions per generation)

### Scope

Implement and test the full slow loop: memory, failure ontology, meta-diagnostics, minimal-contrast retrieval, component attribution, constrained diagnostic/configuration proposal, certification, promotion/quarantine, rollback, genealogy, and reuse. Disable, broaden, or corrupt known distinctions and introduce recoverable novel mechanisms without revealing the hidden intervention.

### Files made or changed

- all modules under `governance/self_learning/`;
- schemas/cards for learning events, proposals, candidates, certification, promotion, rollback, and genealogy;
- `configs/phases/phase3.yaml` and ten repair curricula;
- retained counterexample bank, uncertainty ledger, failure capsule store, append-only trace memory;
- validation suites for trigger replay, retained replay, disjoint temporal holdout, boundary, counterfactual, independent adversarial search, scope audit, invariant audit, and shadow replay;
- scripts for update validation and library inspection; extensive state-machine/rollback tests.

### Code and coding method

The fast loop compiles visible evidence, selects only a certified configuration, runs base/meta diagnostics, emits a typed decision with witnesses, and writes the immutable trace before feedback.

The slow loop triggers on confirmed errors, recurring escalations, unexplained novelty, scope leakage, instability, or significant regression. It reconstructs minimally different correct/incorrect cases; attributes responsibility to diagnostics, availability, severity, weights, mitigation, thresholds, hard veto, selector, and scope; then proposes the least complex intervention in this order: recalibrate, scope change, composition change, split/merge/create/retire diagnostic, policy interaction, specialized configuration, evidence recovery.

The diagnostic grammar is explicit and serializable: thresholds/monotone transforms, conjunction/disjunction/bounded weights, evidence presence/provenance, agreement/diversity/correlation/entropy/calibration residual, temporal persistence/change statistics, nearest validated support/novelty, counterfactual stability, scopes, and response routing. Unrestricted generated code cannot control the fast loop.

Every candidate declares name, intended scope, exact function, threshold, allowed influence, bounds, invariants, provenance, parent/delta, expected benefit/failures, and validation plan. Promotion requires kernel pass, originating failures fixed, zero protected regression, disjoint holdout bounds, stable boundaries, counterfactual causal behavior, disclosed adversarial-search budget with no discovered protected violation, explainable shadow disagreements, complete trace audit, Pareto non-worsening, and verified rollback.

The proposal engine exposes only these versioned operations and their mandatory promotion constraints:

| Operation | Example | Mandatory promotion constraint |
|---|---|---|
| Recalibrate | Change a diagnostic threshold, e.g. `0.55 -> 0.68`. | No protected-family UAR increase. |
| Scope narrow/expand | Restrict correlation diagnostic to shared provenance plus weak independence. | UDI outside intended scope falls; expansion has positive held-out perception gain. |
| Split | Split correlation into presence/harm/safe/ambiguous diagnostics. | Each child has distinct scope/influence and measurable incremental value. |
| Merge | Merge redundant masking diagnostics. | Conditional information loss stays below pre-registered tolerance and genealogy/rollback remain intact. |
| Add | Add masked-safe-evidence diagnostic. | Positive held-out perception gain and certified influence. |
| Retire/deprecate | Remove dominated or unstable diagnostic. | Sealed retention replay is non-inferior and rollback target remains. |
| Policy interaction | Combine harm, weak-safe, and danger witness into a hard veto. | Invariant, retained-family, scope, counterfactual, and boundary tests pass. |
| Configuration specialization | Add a configuration for a recurring regime. | Selector validity region, uncertainty fallback, burden, and rollback are certified. |
| Evidence recovery/routing | Request alternate view/provenance/review. | Recovery is bounded, information-fair, and its escalation/latency cost is charged. |

### Decision allocation and benchmarks

Ten repair curricula x 2,000 decisions. Each includes discovery, containment/quarantine, proposal, certification, shadow, recurrence, rollback challenge, and transfer. Hidden repair mechanisms, holdout seeds, and adversarial suites are disjoint from proposal synthesis.

### Exit gate and outputs

Report feedback-aware time to detection/containment/certified repair, recurrence, escalation contraction, certification precision/recall, beneficial-proposal yield, harmful proposal/promotion rate, rollback correctness, perception gain, scope leakage, library complexity, and all rejected candidates. Harmful update rate must be zero in the fully labeled synthetic core and median recurrence after certified repair must be zero for recoverable families.

## 11. Phase 4 - Full baseline tournament and Pareto audit (25,000 decisions per generation)

### Scope

Freeze implementations and run the untouched tournament bank. Compare complete safety-utility-burden frontiers, not one chosen threshold. Cover all major mechanism families fairly: trivial diagnostic bounds; MAVS-GC/DS-CF/fixed MAVS/context-selected fixed configs; confidence/reject option; Neyman-Pearson/cost-sensitive; conformal/CRC/adaptive/online conformal; ensemble uncertainty/self-consistency; guardrails/validators; critique/judge/verifier/debate; drift adaptation; online experts/bandits; test-time adaptation; multi-objective/Pareto; safe-control/constrained RL; full MAVS-SL.

### Files made or changed

- `configs/phases/phase4.yaml`, frozen method configs and complete sweep registry;
- remaining baseline adapters/configs plus fidelity tests;
- `metrics/frontier.py`, epsilon indicator, hypervolume, CVaR/worst-world, compute normalization, hierarchical bootstrap, exact rare-event bounds, multiple-comparison correction;
- aggregation/report scripts and provenance-linked figure/table generation;
- `CLAIMS.md` automated evidence-to-claim audit.

### Code and coding method

- Freeze code, tuning decisions, development results, final manifests, and hashes before opening the tournament bank.
- Run >=500 matched worlds and every registered threshold/preference/safety-budget point.
- Maintain information-budget parity and report both unconstrained and matched-compute curves.
- Use paired worlds and paired deltas; hierarchical bootstrap worlds then episodes; exact binomial bounds for UAR; mean, median, SD, 95% intervals, worst decile, worst world, and CVaR.
- Correct family-wise confirmatory comparisons for pre-registered top baselines; label all others exploratory.
- Compute non-dominated points only from validated configs and link every plotted point to config, trace, ledger, git, and environment hashes.
- Publish every threshold, preference, abstention-penalty, and safety-budget sweep. Prohibit best-seed reporting, post-hoc world deletion, final-holdout retuning, or removal of collapse cases; all exclusions must be pre-registered integrity failures and remain auditable.

### Decision allocation and benchmarks

25,000 untouched canonical opportunities across at least 500 matched worlds (approximately 50 opportunities per world, with the exact stratification frozen in the manifest). Every eligible method and operating-point sweep replays this same ledger; replays do not increase the canonical budget. The bank is disjoint from all training, calibration, tuning, repair-synthesis, and certification banks and uses altered priors plus frozen method/config hashes.

### Exit gate and outputs

Frontier superiority requires paired hypervolume improvement above zero, lower UAR at matched FRR, lower FRR at matched UAR, and no hidden escalation/intervention/latency/compute regression. Also report epsilon indicators, governance/dynamic regret, adaptation/recovery, recurrence, catastrophic episodes, calibration, trace completeness, and baseline wins. A single favorable operating point or reject-all solution does not pass.

## 12. Phase 5 - Deep ablation, transfer, and anti-overfit trials (15,000 decisions per generation)

### Scope

Establish causal contribution and interaction effects; test unseen domains, policies, generators, corruption families/compositions, long-horizon recurrence, forgetting, negative transfer, and abstraction versus memorization. Execute the complete A0-A49 list from the specification, exceeding the minimum acceptance count of thirty ablations.

### Files made or changed

- `configs/phases/phase5.yaml` and `configs/ablations/A00-A49.yaml`;
- ablation registry/factory and validation preventing silent multi-factor changes;
- resolution-IV fractional-factorial design over meta-diagnostics, synthesis, retained replay, counterfactual validation, certification, and configuration library;
- domain/family/composition/generator leave-out builders;
- surface, structural, and adversarial-reset configs;
- consolidation, retention-bank, negative-transfer detector, raw-memory and matched-memory controls;
- cross-generation analysis/report code.

### Required ablation coverage

The ID-to-condition mapping below is authoritative. `configs/ablations/A00.yaml` through `A49.yaml`, the registry, report, and trace field `ablation_id` must match it exactly.

| ID | Exact condition and isolated question |
|---|---|
| A0 | Full MAVS-SL reference. |
| A1 | No learning: frozen best development configuration. |
| A2 | Threshold-only learning: test whether diagnostic synthesis is unnecessary. |
| A3 | Selector-only learning: fixed library, adaptive context selection only. |
| A4 | Calibration-only: adapt diagnostic thresholds and weights only. |
| A5 | No diagnostic creation: tune existing `G`, never expand it. |
| A6 | No split/merge: prevent scope refinement. |
| A7 | No meta-diagnostics: remove novelty, coverage-gap, scope, and masking monitors. |
| A8 | No failure ontology: flat replay memory only. |
| A9 | No failure capsules: remove compressed reusable mechanism memory. |
| A10 | No counterfactual validation. |
| A11 | No adversarial certification: replay and IID holdout only. |
| A12 | No retained replay: measure catastrophic governance forgetting. |
| A13 | No shadow phase: promote immediately after offline certification. |
| A14 | No safety kernel: permit optimizer safety/recall tradeoffs. |
| A15 | No rollback: measure persistence of damaging updates. |
| A16 | No escalation: force binary decisions. |
| A17 | Reject-on-unknown. |
| A18 | Accept-on-unknown. |
| A19 | No bounded mitigation: safe evidence cannot protect recall. |
| A20 | Raw-correlation hard veto: reintroduce the pre-DS-CF failure. |
| A21 | No safe witness. |
| A22 | No danger witnesses: harm score acts alone. |
| A23 | No provenance diagnostics. |
| A24 | No delayed-feedback handling: treat missing labels as negative evidence. |
| A25 | No feedback-reliability model: poisoned labels update governance normally. |
| A26 | Homogeneous specialists: remove representation diversity. |
| A27 | Perfectly shared representation: worst-case collapse stress. |
| A28 | No configuration library: continually rewrite one global `eta`. |
| A29 | No selector fallback: allow low-confidence configuration selection. |
| A30 | Unlimited diagnostic growth: remove complexity/redundancy control. |
| A31 | Tiny memory: severe replay compression. |
| A32 | Random proposal engine: control for search budget alone. |
| A33 | Oracle failure-family labels: attribution upper bound, not a competitor. |
| A34 | No inter-generation persistence: reset all learned state between G1/G2/G3. |
| A35 | Diagnostics-only persistence: retain `G` and scopes; reset ontology, capsules, selector, and library. |
| A36 | Ontology-only persistence: retain classes/signatures; rebuild diagnostics/configurations. |
| A37 | Configuration-library-only persistence: retain approved configs; reset failure memory and genealogy. |
| A38 | No consolidation: carry every diagnostic/configuration without pruning, merging, or deprecation. |
| A39 | No diagnostic genealogy: keep active functions but remove lineage and historical scope evidence. |
| A40 | No negative-transfer detector. |
| A41 | No prior-generation retention replay: certify later updates on current evidence only. |
| A42 | Frozen after Generation 1: learn only in G1. |
| A43 | Fresh selector each generation: retain diagnostics/configs, reset context selection. |
| A44 | Raw-memory persistence: bounded raw cases/nearest-neighbor lookup without abstract capsules or synthesis. |
| A45 | Surface-reset only: easy-transfer upper bound. |
| A46 | Structural-reset stress. |
| A47 | Adversarial library-targeting reset under fixed pre-registered budget. |
| A48 | Unlimited participant memory: storage upper bound. |
| A49 | Matched-memory cumulative baseline: same persistent-state byte budget as MAVS-SL. |

### Code and coding method

- Generate ablations from explicit component toggles and log exact config diffs.
- Use a resolution-IV fractional factorial for main effects, then targeted paired reruns for the largest interactions.
- Run leave-one-domain, leave-family, leave-composition, and leave-generator-out trials.
- Compare cumulative against fresh, raw-memory, frozen-after-G1, no-consolidation, and no-persistence controls on identical later ledgers.
- Audit exact/near-duplicate access and forbidden answer-key behavior.
- Attack inherited libraries with an independent adversarial generator under a pre-registered budget.
- Apply retention non-inferiority and zero catastrophic-governance-interference gates to every later update and consolidation change.

### Decision allocation and benchmarks

15,000 canonical opportunities stratified in a frozen manifest across domain leave-one-out, corruption-family/composition leave-out, leave-generator-out, policy-semantic transfer, long-horizon recurrence, and surface/structural/adversarial reset worlds. A0-A49 and factorial/targeted interaction runs replay these canonical opportunities under explicit condition toggles; they do not redefine or inflate the 15,000-opportunity phase budget. All Phase 5 worlds and attacker implementations are disjoint from development, tuning, proposal synthesis, and Phase 3 certification banks.

### Exit gate and outputs

Report causal component contributions/interactions, transfer gain, forward transfer, cold-start reduction, learning acceleration, diagnostic reuse, novel-diagnostic yield, negative-transfer rate, catastrophic governance interference, retention score, library efficiency, generation improvement slopes, scope leakage, forgetting, update stability, and all negative results. Continual-governance claims fail if cumulative does not beat fresh on paired G2/G3 ledgers, gains vanish under structural reset, raw memory explains transfer, inherited state causes material harm, or new-world gains require forgetting.

## 13. Statistical decision rules and final acceptance

Primary metrics are UAR, FRR, escalation, intervention-adjusted error, catastrophic episode rate, adaptation/recovery lag, time to detect/repair, recurrence, harmful update rate, certification precision/recall, governance/dynamic regret, frontier hypervolume/epsilon indicator, calibration, scope leakage, perception gain, trace completeness, compute-normalized reward/frontier, worst-world/CVaR, and all cross-generation estimands.

### 13.1 Metric formula registry

`metrics/` and the report schema must preserve these definitions. Every denominator, undefined case, opportunity count, unit, feedback-aware clock, cost weight, reference point, and confidence method is pre-registered in the suite manifest.

| Metric | Required definition |
|---|---|
| UAR | Unsafe accepted / unsafe opportunities. |
| FRR | Safe rejected / safe opportunities. |
| Escalation rate | Escalations / all canonical opportunities. |
| Intervention-adjusted error | Terminal error plus pre-registered weighted escalation/human-review/latency cost. |
| Catastrophic episode rate | Episodes with at least one irreversible unsafe acceptance / episodes. |
| Adaptation lag | Feedback-aware steps from regime onset to stable safe response. |
| Recovery lag | Steps from regime end to restored safe acceptance. |
| Time to detect/repair | Feedback-aware steps to mechanism detection and to certified fix. |
| Failure recurrence | Same-mechanism terminal errors after promotion, with exposure denominator. |
| Harmful update rate | Promoted updates causing protected-family regression / promoted updates. |
| Certification precision/recall | Truly beneficial promoted candidates / promoted candidates; beneficial candidates promoted / beneficial candidates evaluated. |
| Governance regret | Cumulative loss minus the oracle-configuration policy diagnostic bound. |
| Dynamic regret | Loss minus the best time-varying certified-policy sequence in hindsight. |
| Frontier hypervolume | Non-dominated safety-utility-burden volume relative to the frozen zero-error reference. |
| Epsilon indicator | Minimum objective-space shift required for the comparator frontier to dominate. |
| Calibration error | Risk score versus empirical unsafe frequency, including ECE/Brier and reliability plots. |
| Scope leakage | Diagnostic influence outside validated intended scope `Omega`, with exposure and UDI. |
| Perception gain | Conditional information/predictive gain beyond existing evidence state `z`. |
| Trace completeness | Schema- and hash-valid traces / expected traces. |
| Compute-normalized reward/frontier | Reward and frontier comparisons at matched calls, tokens, latency, wall time, memory, and update/consolidation compute. |
| Worst-world/CVaR | Worst seed/world loss and pre-registered tail-average loss. |

The following are confirmatory pass/fail gates, not merely report columns:

| Gate | Required condition |
|---|---|
| Safety | No statistically supported UAR regression versus DS-CF or the strongest safety baseline on retained families; fully labeled synthetic retained-set UAR remains zero. |
| Recall | FRR is lower on the primary untouched bank at matched UAR and matched escalation/intervention burden. |
| Frontier | MAVS-SL hypervolume exceeds every pre-registered baseline family with paired confidence interval above zero; it also has lower UAR at matched FRR, lower FRR at matched UAR, and no hidden burden/latency/compute regression. |
| Learning | Median recurrence after certified repair is zero for recoverable families; harmful promoted-update rate is zero in the fully labeled synthetic core; certification precision/recall and rejected beneficial proposals are reported. |
| Dynamics | Adaptation and recovery lag beat static MAVS and the strongest validated adaptive conformal/drift baseline at matched burden. |
| Transfer | Positive paired gain on unseen domains/corruption compositions and G2/G3 cumulative-over-fresh comparisons, without scope leakage, retained regression, material negative transfer, or uncontrolled growth. |
| Audit | 100% trace, terminal-error card, promoted-update card, checkpoint, manifest, and hash completeness; every published number regenerates from frozen manifests. |

Failing any applicable confirmatory gate prevents the corresponding superiority, transfer, zero-error, retention, or compounding claim. Exploratory wins cannot substitute for a failed confirmatory gate.

Final acceptance requires:

1. exactly three immutable, independently generated, hash-validated 100,000-opportunity ledgers;
2. identical worlds and released information for all eligible methods;
3. >=5 domains, >=6 schedule families, >=10 corruption families, >=20 compositions;
4. >=12 baseline mechanism families and the complete authoritative A0-A49 suite (thereby exceeding the specification's >=30 minimum);
5. no uncertified live updates; reproducible promotions, consolidation changes, quarantine, and rollback;
6. a trace/card/lineage chain for every terminal error and promoted update;
7. paired uncertainty, exact rare-event bounds/exposures, worst-world/tail results, full frontier and compute-normalized comparisons;
8. disjoint altered-prior final holdouts with no post-holdout tuning;
9. preserved negative results, collapse cases, harmful proposals, and baseline wins;
10. explicit covered-environment class and no conversion of observed zero errors into universal proof;
11. cumulative/fresh later-generation controls for MAVS-SL and every legitimately adaptive baseline;
12. participant checkpoint audits proving no future-manifest, hidden-label, or raw answer-key leakage;
13. certified consolidation after G1/G2 and sealed retention banks;
14. surface, structural, adversarial, raw-memory, frozen-after-G1, no-consolidation, and no-persistence controls;
15. cumulative MAVS-SL beats fresh MAVS-SL on paired later-generation worlds without safety regression, forgetting, or uncontrolled library growth before claiming compounding.

## 14. Reproducibility commands

The implementation must make these command forms real and tested:

```bash
python scripts/compile_generation_ledgers.py --suite configs/suites/self_learning_300k.yaml
python scripts/run_suite.py --suite configs/suites/self_learning_300k.yaml --generation 2 --phase phase3
python scripts/run_three_generation_suite.py --suite configs/suites/self_learning_300k.yaml
python scripts/consolidate_library.py --generation 1 --input results/checkpoints/generation_1 --out results/checkpoints/generation_1_consolidated
python scripts/validate_generation_resets.py --manifests results/manifests --recursive
python scripts/validate_participant_state.py --checkpoints results/checkpoints --recursive
python scripts/validate_traces.py --input results/raw --recursive
python scripts/validate_updates.py --input results/reports/update_cards --recursive
python scripts/aggregate_results.py --input results/raw --out results/processed/final_summary.parquet
python scripts/analyze_cross_generation.py --summary results/processed/final_summary.parquet --out results/processed/cross_generation_summary.parquet
python scripts/make_report.py --summary results/processed/final_summary.parquet --cross-generation results/processed/cross_generation_summary.parquet --out results/reports/mavs_sl_300k
make reproduce-mavs-sl-300k
```

`compile_generation_ledgers.py` is stage-aware: the command form above compiles only the currently eligible generation and refuses to materialize G2/G3 hidden manifests until the preceding generation's consolidated checkpoint is frozen and hashed. `run_three_generation_suite.py` invokes that same gate at each boundary. This reconciles exact reproducibility with the mandatory prohibition on inter-generation leakage.

## 15. Reporting artifacts and claim discipline

Every unsafe acceptance, representative false rejection, repeated escalation cluster, harmful proposal, rollback, and certified repair produces human-readable failure, investigation, proposal, certification, promotion, and genealogy cards. The final report publishes manifests, hashes, checkpoints, commands, sweeps, errors, rejected updates, consolidations, and negative outcomes.

Every terminal error and every promoted update must have a card; representative sampling applies only to non-terminal false rejections and repeated escalation clusters. Cards are schema-validated, linked to immutable traces, and contain at least:

| Artifact | Mandatory content |
|---|---|
| Failure card | World/step, expected versus actual action, visible evidence, hidden mechanism after reveal, specialist state, diagnostic trace, immediate containment, suspected cause. |
| Investigation card | Nearest correct cases, discriminating variables, attribution scores, ontology mapping, evidence sufficiency, released-feedback provenance. |
| Proposal card | Operation type, exact function/policy delta, intended scope, permitted influence, parent lineage, predicted benefit/failures, complexity and validation plan. |
| Certification card | Trigger/retained replay, disjoint holdouts, adversarial cases, counterfactual/boundary tests, scope/invariant checks, shadow disagreements, frontier delta, compute cost, hashes, decision/reason codes. |
| Promotion card | New configuration ID, exact activation scope/time, fallback, monitoring conditions, rollback target, parent and certification hashes. |
| Rollback/consolidation card | Trigger, affected versions, restored target, protected-family replay, merge/deprecate/prune/recalibrate rationale, complexity delta, rejected alternatives. |
| Genealogy report | Diagnostic/configuration DAG, all split/merge/deprecation reasons, parent/delta history, cumulative protected families, active/total library size and costs. |

The automated claim ladder permits only the statement supported by the highest fully passed row; lower-level negative or mixed results remain visible.

| Evidence outcome | Maximum permitted claim |
|---|---|
| Infrastructure only | A reproducible three-generation 300K continual-governance benchmark has been implemented. |
| MAVS-SL beats fixed MAVS | Governance learning improved behavior relative to fixed MAVS in the evaluated dynamic worlds. |
| MAVS-SL beats adaptive baselines | MAVS-SL expanded the observed safety-utility-burden frontier relative to the evaluated adaptive families. |
| Zero observed UAR/FRR with low burden | MAVS-SL achieved zero observed terminal errors over `N` labeled opportunities in the stated world class, with exact bounds and reported escalation/intervention. |
| Cross-domain transfer | Learned governance primitives transferred to the specified held-out domains and corruption compositions. |
| Forward transfer | Cumulative MAVS-SL beat fresh MAVS-SL on G2/G3 early and full-generation paired metrics at matched compute/memory. |
| Retention | No statistically supported regression occurred on sealed prior-generation banks; CGI is zero in the synthetic core. |
| Low negative transfer | Inherited-state harm remained below the pre-registered tolerance and all severe cases were detected, quarantined, or rolled back. |
| Compounding | At least two of cold-start loss, TTD/TTR, recurrence, burden, or hypervolume improved monotonically across generations without safety regression. |
| Efficiency | Active-library complexity remained bounded or gain per component improved after consolidation. |
| Cumulative beats fresh on G2/G3 | Certified governance knowledge provided positive forward transfer, reduced cold-start loss, and accelerated repair on independently regenerated worlds. |
| Monotonic three-generation improvement | Observed governance capability compounded across three 100K generations under the reported reset classes, retention bounds, and complexity budget. |

No row permits an unrestricted universal zero-error/convergence proof, guaranteed perpetual monotonic improvement, industrial deployment certification, or domination of every existing or future method.

### 15.1 Known risks and mandatory countermeasures

| Risk | Required countermeasure and owning phase |
|---|---|
| Reject-all illusion | FRR, escalation, reward, intervention-adjusted loss, and reject-all bound; P0/P4. |
| Feedback leakage | Separate hidden manifests from observations and validate API/filesystem boundaries; P0 and every phase. |
| Adaptive overfitting | Disjoint banks, frozen final priors, retained replay, altered priors, and no post-holdout tuning; P0/P3-P5. |
| Catastrophic governance forgetting | Protected-family suites, sealed retention banks, non-inferiority and rollback gates; P3/P5. |
| Diagnostic explosion | Complexity budget, maximum active set, redundancy/marginal-value audit, merge/deprecate; P3/P5. |
| Poisoned delayed labels | Reliability metadata, quarantine, robust subsets, and poison-specific tests; P2/P3. |
| Baseline underimplementation | Source/fidelity document, unit tests, public references, full sweep, strongest validated settings; P1/P4. |
| Compute asymmetry | Matched calls/tokens/latency/wall time/memory and compute-normalized frontiers; P1/P4/P5. |
| World-generator artifacts | Multiple generators, metamorphic tests, leave-generator-out holdouts; P0/P5. |
| Metric gaming | Pre-register gates and publish every operating point and exposure count; P0/P4. |
| Rare-event false confidence | Exact binomial bounds and unsafe-opportunity counts; P4. |
| Ambiguous universal language | Automated claim ladder and covered-environment qualifiers in README/report; P4/final. |
| Easier later worlds masquerading as transfer | Cumulative/fresh paired conditions on identical ledgers and world-difficulty diagnostics; all generations/P5. |
| Raw-example memorization | Surface/structural resets, bounded raw-memory control, exact/near-match audit, abstraction comparison; P5. |
| Unfair baseline reset | Cumulative/fresh variants and legitimate state retention for every adaptive baseline; all generations. |
| Negative inherited transfer | Fresh counterfactuals, scope monitors, inherited-harm flags, quarantine and rollback; P3/P5. |
| Inter-generation leakage | Compile future ledgers only after prior checkpoint freeze; isolate and access-audit manifests; P0/orchestrator. |
| Library bloat masquerading as depth | Complexity budgets, consolidation, redundancy pruning, gain-per-component and retrieval cost; P3/P5. |
| Catastrophic interference | Sealed prior-generation banks and promotion/consolidation non-inferiority gates; P3/P5. |
| Adversarial-targeting overfit | Pre-register attack budgets and use an independent adversarial generator never exposed during development; P2/P5. |

## 16. Engineering task discipline and phase ownership

Each implementation task owns one contract or module and begins with exact inputs, outputs, invariants, failure modes, dependencies, files, and tests. Every state transition, schedule, promotion gate, quarantine path, consolidation action, selector fallback, and rollback path requires positive, negative, boundary, determinism, and serialization tests as applicable. Every baseline requires a hidden-label/manifest access test. After every work package--not only at Phase 0--the original Chapter 10D unit suite, smoke experiment, and trace validator run alongside the new package-specific tests. A package cannot merge when the inherited regression path fails.

| Work package | Phase ownership and concrete deliverable |
|---|---|
| WP0 Clone/provenance | P0: provenance-only import commit, original tests/smoke/trace validation, empty-results proof. |
| WP1 World compiler/ledgers | P0 plus generation boundaries: hierarchical RNG, signed manifests, schedules, staged immutable 100K ledgers, replay parity and reset validation. G1 is compiled first; G2 only after frozen G1 consolidation; G3 only after frozen G2 consolidation. |
| WP2 Baseline arena | P1/P4: exact inventory in Section 6.5, tuning grids, fidelity tests, compute and information accounting. |
| WP3 Memory/ontology | P3: append-only trace memory, capsules, ontology, novelty/scope/masking monitors. |
| WP4 Proposal/certification | P3: grammar, attribution, candidate deltas, replay/holdout/counterfactual/adversarial/scope/invariant/shadow gates. |
| WP5 Kernel/library | P3: immutable kernel, promotion/quarantine, selector/fallback, rollback and genealogy. |
| WP6 Phase experiments | P0-P5: frozen manifests, exact budgets, failure inspection, exit-gate evidence. |
| WP7 Statistics/reporting | P4/P5: paired/hierarchical statistics, full frontiers, cards, claim audit, reproducibility. |
| WP8 Three-generation orchestration | P0/P5: reset validator, cumulative/fresh matrix, checkpoints, forbidden-state audit. |
| WP9 Consolidation/retention | P3/P5: merge/prune/deprecate/recalibrate, sealed banks, negative-transfer detection, genealogy. |
| WP10 Cross-generation analysis | P5: exact Section 5.3 estimands, uncertainty, generation slopes, compounding falsifiers. |

`Path.md` records the inherited regression command and result after each work package. Parallel work is allowed only for modules with non-overlapping contracts; phase exit remains sequential.

## 17. Specification coverage map

| Validation-spec content | WorkPlan coverage |
|---|---|
| Mission, exact 300K interpretation, H1-H10 and falsifiers | Sections 1-1.1, 5, 12, 13, 15 |
| Chapter 10D foundation, clone/import sequence, provenance | Sections 0, 2, 7 |
| Approved configuration, three actions, lexicographic objective, frontier definition | Sections 1, 4, 11, 13 |
| Successor file architecture and new contracts | Sections 3-4 |
| World randomization, numeric generator priors, seed hierarchy, schedule families, pseudo-config semantics | Sections 4.1, 5, 7-9 |
| Baseline mechanism families, exact named adaptations, sources/fidelity, tuning, compute/information parity | Sections 6.5-6.6, 8, 11 |
| Optional model recipes, model-card fields, training/evaluation separation, blind benchmarks | Sections 6.1-6.4 |
| Phase 0 through Phase 5 budgets, designs, and gates | Sections 7-12 |
| Generation semantics, reset boundary, persistence, paired controls, reset taxonomy | Section 5 and Phase 5 controls |
| Consolidation, checkpoints, early windows, estimands, falsification pattern | Sections 5, 12-13 |
| Self-Learning fast/slow loops, grammar, safety kernel | Sections 1, 4, 10 |
| Complete A0-A49 ablation program and factorial core | Section 12 |
| Metric definitions, paired/hierarchical statistics, rare-event bounds, superiority gates | Sections 11-13.1 |
| Suite config, required commands, trace additions | Sections 3-5, 14 |
| Failure/investigation/proposal/certification/promotion/rollback/genealogy card fields | Sections 10, 15 |
| Engineering work packages and per-task test discipline | Sections 7-12 and 16 |
| Final acceptance criteria and claim ladder | Sections 13 and 15 |
| Known risks and mandatory anti-overfit/leakage/forgetting/bloat controls | Sections 2, 4-6, 12-13, 15.1 |
| Final implementation directive | Entire plan, with execution evidence required under Section 18 |

## 18. `Path.md` execution discipline

`Path.md` is the implementation evidence ledger, not a summary written after the fact. For every work package or meaningful change it must record date/time, phase/generation, plan clauses, exact files, implementation decisions, commands/tests, input/output hashes, result-cleanliness check, metrics, failures, deviations, corrective action, and next gate. A phase may be marked complete only when its WorkPlan exit gate is evidenced. If implementation deviates, `Path.md` records why, impact, approval if required, and whether this plan must be amended.
