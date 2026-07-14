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

## 19. Version 0.4 normative extension, evidence boundary, and preservation policy

- **Normative revision:** `MAVS_Self_Learning_Perception_Closure_Architecture_and_Revalidation_v0.4.pdf`.
- **Normative revision SHA-256:** `2E235F9D4AD2AA9F54243B6C928BC2AA0EA1F7B0D822EE19867CD345E65149D1`.
- **Extension planning date:** 2026-07-14.
- **Extension status:** implementation-ready planning only. Appending Phases 6-10 is not evidence that any Version 0.4 module, experiment, gate, or claim has passed.
- **Precedence:** Sections 19-27 govern the revised Perception-Closure implementation and revalidation. Sections 0-18 remain the immutable plan and historical interpretation for Phases 0-5 except where this section narrows the evidentiary meaning of prior results.
- **Program rule:** no Version 0.4 output may support a Self-Learning MAVS claim until Phase 6 synthesis-integrity gates, Phase 7 live-runtime gates, Phase 8 ablation/integrity gates, Phase 9 paired and blind revalidation gates, and Phase 10 independent release audit all pass in sequence.

### 19.1 Phase 3 evidentiary reclassification

The retained `phase3_20260713` card corpus contains exactly 120 candidates. All 120 use the same outer executable form: one named feature, operator `>=`, threshold `0.5`, lower/upper bounds `[0.0,1.0]`, monotone-increasing semantics, and one unit weight. Features, primitive labels, operation labels, curricula, domains, generations, candidate IDs, and metadata vary, but the outer computation and fitted values do not. The previous Phase 3 result is therefore a deterministic diagnostic-lifecycle and certification-harness benchmark, not proof of differentiated diagnostic synthesis.

| Prior Phase 3 evidence | Retained interpretation | Prohibited interpretation without a Version 0.4 rerun |
|---|---|---|
| Immutable traces, hashes, and deterministic replay | Validates deterministic candidate execution and replay plumbing. | Does not establish that a new semantic distinction was discovered. |
| Proposal, certification, promotion, rejection, quarantine, rollback, and genealogy state transitions | Validates governed lifecycle orchestration and rollback mechanics. | Does not establish that certification discriminated among naturally varying executable candidates. |
| Configuration persistence, checkpointing, lineage, and consolidation records | Validates persistence and bookkeeping mechanics. | Does not establish beneficial compounding of genuine diagnostic knowledge. |
| Candidate cards with varied names, operations, domains, curricula, and generations | Validates schema coverage and metadata transport. | Does not establish executable operation meaning, real parameter optimization, or behavioral diversity. |
| Existing Phase 3 audit verdict | Remains valid only for the pipeline/lifecycle claims it actually tested. | Must not be cited as evidence of autonomous diagnostic invention, learned perception extension, or high-quality synthesis. |

The reclassification is fail-closed: `pipeline_validity != diagnostic_synthesis_validity`. All prior artifacts remain available and hash-addressable; none may be deleted, relabeled as Version 0.4 evidence, or silently included in a revised claim aggregate.

### 19.2 Results preservation and namespace contract

Previous results are immutable historical evidence. Before Phase 6 execution, an indexing operation must create the following logical layout without deleting or overwriting any existing path:

```text
results/
|-- legacy/
|   |-- phase3_20260713_template_harness/
|   |-- phase4_original/
|   `-- phase5_original/
|-- perception_closure_v04/
|   |-- phase6/
|   |-- phase7/
|   |-- phase8/
|   |-- phase9/
|   |   |-- paired_original_bank/
|   |   `-- blind_bank/
|   `-- phase10/
`-- RESULTS_INDEX.md
```

The existing Phase 3, Phase 4, and Phase 5 evidence is currently distributed across `results/{manifests,checkpoints,raw,processed,aggregates,figures,reports}/<run_id>`. If moving those paths would invalidate manifests, Git LFS pointers, hashes, or published references, they must remain in place. In that case Phase 6 creates immutable indexed copies or content-addressed references under the legacy namespace, with a `legacy_manifest.json` that records every source path, destination/reference path, byte size, SHA-256, Git object/LFS object ID where applicable, original run ID, code SHA, claim status, and copy/link method. A complete byte/hash comparison must pass before a legacy namespace is sealed.

Legacy claim statuses are fixed as follows:

- `phase3_20260713_template_harness`: pipeline-lifecycle and certification-plumbing evidence only;
- `phase4_original`: historical tournament behavior of the pre-Perception-Closure architecture;
- `phase5_original`: diagnostic evidence motivating the redesign, including the retained `NOT_SUPPORTED` continual-governance result.

| Legacy logical namespace | Existing source run IDs that must be indexed without mutation |
|---|---|
| `results/legacy/phase3_20260713_template_harness/` | `phase3_20260713` under current `manifests`, `checkpoints`, `raw`, `processed`, and `reports` roots. |
| `results/legacy/phase4_original/` | `phase4_authoritative` under current `manifests`, `raw`, `aggregates`, and `reports` roots. |
| `results/legacy/phase5_original/` | `phase5_authoritative` under current `manifests`, `raw`, `aggregates`, `figures`, and `reports` roots. |

Every closed Version 0.4 result directory is append-only and contains a manifest binding code SHA, configuration hash, data/ledger hashes, seed ledger, environment lock, schema versions, artifact hashes, and claim status. No script may glob or concatenate legacy and Version 0.4 results. Any paired cross-version comparison requires an explicit `cross_version_comparison_manifest.json`. `results/RESULTS_INDEX.md` must identify every run as current, valid, failed, superseded, diagnostic-only, or release-bearing; default Version 0.4 reports may resolve only within `results/perception_closure_v04/`.

## 20. Revised Perception-Closure architecture and cross-phase contracts

The revised Self-Learning MAVS is a decision-conditioned Diagnostic Sciences system. It first runs the approved fast loop. An unresolved decision becomes an explicit finite safe/unsafe hypothesis-separation problem, not a generic confidence band. The resolver searches for bounded diagnostics, compositions, queries, probes, specialists, tools, or evidence-recovery actions that add protected conditional perception inside the live ambiguity class. It activates the smallest scope-certified nonredundant case program, issues a terminal action only under a closure certificate, and externally escalates only after every valid positive-value perception-extension path is exhausted or unavailable.

The formal implementation is `M^PC = (M, H, O, T, R, Q, V_local, L, V_persist, K, C, S, B, N)`: the base runtime, governance memory, ambiguity ontology, certified executable primitive library, resolver, evidence-acquisition system, local certification, learning operator, persistent certification, immutable kernel, compact persistent basis, governed selector, budget controller, and negative-knowledge base. Per-decision state is `state_t = (e_t, H_t, A_t, Z_t, G_t, Q_t, Lambda_t, budget_t)` and must be serializable at every resolver round.

The population objective is lexicographic: `Lex(UAR, FRR, ResidualEscRate, QueryCost, Latency, Complexity)`. A reduction in escalation or burden cannot compensate for an unsafe-acceptance regression; a false-rejection improvement cannot compensate for an unsafe-acceptance regression. Residual escalation is decomposed as `IrreducibleAmbiguity + EvidenceUnavailable + BudgetExhaustion + ResolverFailure`. `QUERY`, internal diagnostic/probe rounds, and external `ESCALATE` are different event types, counters, costs, and terminal semantics.

### 20.1 Mandatory Version 0.4 data contracts

| Contract | Mandatory content and invariant |
|---|---|
| `ExecutableDiagnostic` | Canonical executable AST; fitted parameters; executable positive scope and anti-scope; evidence, influence, and counterfactual contracts; semantic hash; behavioral fingerprint; operation semantics; lineage; search provenance. Names and labels are documentation only. |
| `Hypothesis` | Semantic regime claim, predicted witnesses, predicted nuisance/causal counterfactuals, discriminating actions, positive scope and defeating anti-scope, and terminal consequence if uniquely supported. |
| `AmbiguityState` | Surviving hypotheses, safe/unsafe compatibility, evidence keeping each hypothesis alive, equivalence-class hash, unresolved contrast type, candidate separation plan, and round/budget state. It is unresolved only when at least one safe-compatible and one unsafe-compatible hypothesis remain. |
| `PerceptionAction` | Executable diagnostic/composition/query/probe/specialist/tool/evidence-recovery action; targeted ambiguity; expected protected ambiguity reduction; evidence dependencies; scope proof; cost/privacy/latency budget; authority; semantic identity. |
| `QueryRecord` | Target ambiguity, expected observation, required source/provenance/trust/freshness, expected and realized ambiguity contraction, cost, latency, outcome, and whether the path becomes negative knowledge. |
| `ActiveCaseProgram` | Minimal selected executable basis; candidate marginal CMPG; redundancy and interaction analysis; activation certificates; influence graph; typed channels; authority bounds; prohibited-composition checks; program hash. |
| `LocalClosureCertificate` | Hypothesis separation, witness sufficiency, executable scope, evidence integrity, counterfactual stability, interaction safety, authority, risk justification, kernel preservation, and replay completeness. Every obligation has independent evidence and a reason code. |
| `ResidualEscalationRecord` | Exact unresolved hypotheses; tried and rejected/executed perception paths; remaining candidates; irreducible/evidence-unavailable/budget-exhausted/resolver-failure reason; budget ledger; proof that no permitted positive-value action remained. |
| `PersistentKnowledge` | Reusable semantic distinction, scopes/anti-scopes, query policy, legal/prohibited composition, compact case program, failure signature, negative knowledge, retained counterexamples, lineage, certification state, active-eligibility state, and rollback target. |

All schemas are versioned Draft 2020-12 JSON Schemas with strict unknown-field handling at process boundaries. Every record carries run/phase/generation/condition/world/case/round IDs, code/config/data/seed hashes, event time, participant-state hash, and trace-parent hashes. Evaluator-only semantic truth, minimum separating action, expected candidate class, promotion target, and hidden world construction fields are prohibited from participant, synthesis, certification, and persistent-memory schemas.

### 20.2 Cross-phase runtime and learning invariants

- The approved fast loop is always attempted first; only unresolved cases enter Perception Closure.
- Every unresolved case has explicit competing safe-compatible and unsafe-compatible hypotheses and an ambiguity-equivalence class.
- Conditional marginal perception gain is evaluated inside the live ambiguity class, never substituted with global diagnostic utility.
- Positive scope enables consideration; anti-scope, missing contract evidence, or insufficient authority prevents influence.
- Availability, scope, novelty, and conflict channels are query/adjudication signals by default and cannot directly create danger pressure or hard vetoes.
- Persistent memory expands the searchable knowledge space, not the simultaneously influential set. Every active primitive must add positive conditional perception and every composition must be certified.
- One certified causal family owns terminal interpretation unless an interaction certificate permits a multi-family explanation; unrelated severities are never additively stacked.
- `ACCEPT` and `REJECT` require a terminally homogeneous hypothesis set, an explicit safe/danger witness, and a valid persistent or local closure certificate.
- `ESCALATE` is legal only after no valid positive-value perception extension remains, necessary evidence is inaccessible, the bounded budget is exhausted, or the resolver fails; the reason is recorded without collapsing internal queries into escalation.
- Slow-loop promotion compresses repeated successful closure paths into reusable semantics, scopes, anti-scopes, query policies, certified compositions, compact programs, and negative knowledge. It never makes a new diagnostic globally influential by default.
- Merge, narrow, split, retire, quarantine, and prohibit-composition operations preserve evidence, lineage, counterexamples, and rollback even when active eligibility is removed.
- Every candidate, resolver round, terminal action, promotion, consolidation action, and escalation is deterministic and independently replayable from pinned manifests.

### 20.3 Theorem targets and empirical assumption audits

The following are theorem/guarantee targets, not established results. Implementation tests must audit their assumptions and may provide finite-fixture proofs or counterexamples, but no empirical pass may be promoted into a universal theorem.

| Target | Required implementation property | Assumptions/evidence that must be audited |
|---|---|---|
| Conditional perception extension | A positive-CMPG candidate splits at least one live ambiguity class the incumbent state cannot split. | Correct finite hypothesis representation, identifiable signal, valid protected metric, executable candidate. |
| Perception closure | Repeated valid updates reduce the ambiguity class until it is decision-homogeneous or no permitted extension remains. | Finite hypotheses/actions, valid evidence updates, monotone elimination where claimed, bounded search. |
| Zero residual escalation on finitely separable classes | A finite certified sequence within budget closes every covered case without protected error. | Finite separability, accessible evidence, correct scopes/anti-scopes, sufficient budget, exact execution. |
| Irreducible escalation floor | Observationally identical safe/unsafe cases under every permitted action cannot be terminally separated without error. | Equality of permitted observable distributions and complete action enumeration. |
| Scope-safe influence | A diagnostic with zero influence outside its certified positive scope cannot directly create scope leakage. | Executable activation certificate, correct anti-scope, complete influence tracing. |
| Sparse-basis non-inferiority | Removing diagnostics with zero conditional gain preserves closure power for the live ambiguity. | Exact conditional redundancy and no hidden interaction. |
| Typed-meta safety | Novelty, masking, availability, scope uncertainty, and conflict cannot directly hard-veto. | Kernel and authority enforcement on every path. |
| Consolidation stability | Retiring dominated eligibility reduces interaction opportunities without worsening protected closure. | Complete retained suite, accurate dominance test, preserved lineage/rollback. |

The strong conditional target `UAR = FRR = ResidualEscRate = 0` applies only to a declared fully observable, finitely separable covered class with certified accessible actions inside budget. Outside that class, residual escalation must converge toward the measured irreducible floor, not an arbitrary abstention target. Phase 7 writes `reports/theorem_assumption_audit.md`; Phase 8 attacks each property; Phase 9 reports empirical scope and counterexamples; Phase 10 limits claim language accordingly.

## 21. Phase 6 - Executable Diagnostic Synthesis and Anti-Gaming Foundation

### Scope

Replace the Phase 3 name-centered bounded-function cards with a canonical executable diagnostic language and a synthesis/certification pipeline that makes renamed boilerplate, constant output, no-op behavior, parent-identical behavior, metadata-only operations, hidden-label leakage, and pre-labelled beneficial/harmful candidates structurally incapable of promotion. Phase 6 must demonstrate genuine structure and parameter search, explicit scope/anti-scope/evidence/influence/counterfactual contracts, name-invariant semantic identity, frozen-bank behavioral identity, independent behavior-only certification, and reproduced perception-extension witnesses before any candidate can enter the live Phase 7 runtime.

Phase 6 depends on the immutable Phase 0 contracts and kernel, the retained Phase 3 lifecycle plumbing, and the legacy indexing contract in Section 19. It may reuse pipeline mechanics but must replace synthesis semantics. Phase 7 is blocked until every Phase 6 integrity gate passes non-vacuously.

### Files made or changed

- `configs/phases/phase6.yaml`, `configs/perception_closure_v04/synthesis.yaml`, audited AST grammar, structure-search spaces, parameter-search ranges, split manifests, certification budgets, permutation suites, and anti-gaming fixtures;
- `schemas/v04/{diagnostic_ast,diagnostic_contract,structure_search_trace,parameter_search_trace,semantic_identity,behavioral_fingerprint,perception_extension_witness,blind_certification_request,independent_gate_vector,integrity_finding}.schema.json`;
- `src/mavs10d/diagnostics/{ast,contracts,semantic_hash,behavioral_fingerprint}.py`;
- `src/mavs10d/learning/{structure_search,parameter_fit,operation_constraints,synthesis}.py`;
- `src/mavs10d/certification/{blind_api,gates,persistent}.py`;
- `src/mavs10d/integrity/{template_collapse,permutation_tests,hidden_field_audit}.py`;
- `src/mavs10d/metrics/synthesis_integrity.py` and `src/mavs10d/reports/synthesis_integrity.py`;
- `scripts/{index_legacy_results,run_phase6_synthesis,certify_phase6_candidates,audit_phase6_integrity,replay_phase6_candidates}.py` and a Phase 6 orchestrator that cleans only the named, unsealed Version 0.4 Phase 6 run;
- `tests/phase6/` unit, property, metamorphic, process-isolation, taint, adversarial-integrity, statistical, schema, and deterministic-replay tests;
- only `results/legacy/`, `results/perception_closure_v04/phase6/`, and `results/RESULTS_INDEX.md` may be created or extended by this phase; original Phase 0-5 result paths remain byte-identical.

### Data and artifact contracts

Every proposed candidate, including integrity rejection and certification rejection, receives a stable candidate directory:

```text
results/perception_closure_v04/phase6/
|-- manifests/{run_manifest,split_manifest,seed_ledger,environment_lock}.json
|-- candidates/<candidate_id>/
|   |-- candidate.json
|   |-- structure_search.parquet
|   |-- parameter_search.parquet
|   |-- semantic_identity.json
|   |-- behavioral_fingerprint.parquet
|   |-- operation_compliance.json
|   |-- perception_extension_witness.json
|   |-- blind_request.json
|   |-- independent_gate_vector.json
|   `-- certification_trace.parquet
|-- integrity/
|   |-- semantic_duplicate_classes.json
|   |-- behavioral_equivalence_classes.json
|   |-- template_collapse_report.json
|   |-- name_label_operation_permutation.json
|   |-- hidden_field_taint_report.json
|   |-- blind_api_schema_audit.json
|   |-- constant_noop_parent_identity_report.json
|   `-- gate_distribution_investigation.json
|-- reports/{synthesis_integrity.md,candidate_inventory.parquet,rejections.parquet,phase6_audit.json}
`-- CLAIMS.md
```

`candidate.json` contains `expression_ast`, fitted `parameters`, `positive_scope_ast`, `anti_scope_ast`, `evidence_contract`, `influence_contract`, `counterfactual_contract`, and `lineage`. The evidence contract declares sources, provenance, availability, freshness, trust, and failure behavior. The influence contract declares observation/query/soft/terminal authority and numeric bounds. The counterfactual contract declares nuisance-preserving interventions that must not alter output and causal interventions that must. Lineage records parents, exact operation, triggering contrast, synthesis evidence, all search traces, and rollback target.

The canonical semantic hash is `H(NormalizeAST, parameters, positive_scope, anti_scope, evidence_contract, influence_contract, counterfactual_contract)` and explicitly excludes candidate names, IDs, domains used only as labels, curriculum/generation labels, operation text, proposal order, and expected outcome. The behavioral fingerprint records raw and discretized output, activation, query, authority, and terminal influence over frozen trigger, retained, holdout, positive-scope boundary, anti-scope, nuisance counterfactual, causal counterfactual, adversarial, and disjoint-analogue banks.

### Code and coding method

1. Implement a typed bounded AST grammar for predicates, conjunctions, disjunctions, bounded arithmetic, comparisons, temporal and provenance relations, counterfactual comparisons, and query outputs. Parsing, validation, normalization, serialization, deserialization, and evaluation must be deterministic and versioned; opaque feature-name strings cannot execute.
2. Resolve every feature/evidence leaf through an audited registry declaring type, domain, provenance, availability, trust, units, bounds, missingness behavior, and permitted operations. Zero unresolved references are allowed.
3. Generate candidate structures from minimal protected failure contrasts. Search over both executable structure and parameter vectors. A threshold of `0.5` or unit weight may be an initialization, never an unexplained default.
4. Fit thresholds, weights, transforms, calibration values, positive-scope bounds, anti-scope bounds, authority levels, and interaction coefficients with lexicographic `UAR -> FRR -> residual escalation -> scope leakage -> instability -> complexity` objectives. Record every tried structure/vector, search range, split, seed, objective vector, protected-constraint result, rejection reason, and selection rationale.
5. Enforce nested separation: synthesis/development splits may select candidates; disjoint certification splits decide promotion; final blind banks are inaccessible. Any optional learned search/ranking component follows Section 6 model-card and split discipline and cannot see certification or final labels.
6. Canonicalize before hashing. Collapse exact semantic duplicates before certification. Reject behavioral equivalents unless a predeclared, independently certified improvement in cost, calibration, scope, or stability exists.
   Semantic and behavioral deduplication are separate mandatory gates; passing one never substitutes for the other.
7. Reject candidates that are name-only, metadata-only, constant-output, behaviorally null/no-op, parent-identical, sibling-identical, or unable to change the trigger/contrast/boundary/holdout behavior meaningfully. A versioned recalibration may share a parent AST only when independently fitted parameters and certified gain are proven.
8. Run synthesis and certification in separate processes with separate hierarchical seeds and serialized schemas. Strip operation label, expected beneficial/harmful class, curriculum slot, desired promotion outcome, candidate-quality label, generator truth, hidden world fields, and candidate name as a quality signal from the certifier request.
   This is blind behavior-only certification: promotion is determined from executable behavior and protected evidence, never narrative labels or intended outcomes.
9. Compute kernel, trigger, retained, scope, anti-scope, evidence-integrity, counterfactual, boundary, adversarial, redundancy, protected-error, stability, complexity, and replay gates independently from behavior. Persist the complete gate vector and supporting cases; an all-pass/all-fail distribution triggers a mandatory integrity investigation and cannot be waived narratively.
10. Require a protected perception-extension witness: the incumbent state cannot distinguish a safe/unsafe pair within tolerance; the pair requires different decisions; the candidate separates it for a causal reason; terminal behavior becomes correct without retained or anti-scope regression; and the witness reproduces on a disjoint neighborhood or structural analogue.

Operation labels have the following machine-checked executable meanings:

| Operation | Required semantic delta and rejection rule |
|---|---|
| `recalibrate` | Preserve parent AST structure and semantic dependencies; alter independently fitted calibration/threshold parameters and improve calibration/protected objective. Reject unchanged, hardcoded, or non-improving vectors. |
| `split` | Produce at least two children with distinct AST behavior or executable scopes that separate regimes conflated by the parent. Reject metadata-only children or behaviorally equivalent siblings. |
| `merge` | Consume at least two parents and reduce conditional redundancy, cost, or complexity while preserving/improving protected closure. Reject a renamed parent or any loss of required distinction. |
| `add` | Introduce a new evidence dependency, relation, query, or computation and pass a new perception-extension witness. Reject feature renames and inherited-output aliases. |
| `scope_narrow` | Change executable positive/anti-scope so the leaked neighboring region is deactivated while retained positive scope remains valid. |
| `scope_expand` | Add a newly certified executable region and pass new boundary, anti-scope, holdout, and disjoint-analogue tests. |
| `evidence_recovery` | Execute or consume a new evidence-acquisition path with provenance, availability, cost, and realized information-gain records. Metadata-only routing fails. |
| `policy_interaction` | Change a typed executable policy/evidence relationship with explicit authority and counterfactual obligations. Merely changing an operation label fails. |
| `configuration_specialization` | Change context-to-program mapping or terminal governance behavior in the specialized regime while preserving fallback and scope proofs. |
| `retire` | Remove active influence eligibility while preserving lineage, counterexamples, evidence, replayability, and rollback. A status-label change without runtime exclusion fails. |

### Tests, validation, and audit requirements

- AST tests cover type errors, illegal operations, missing leaves, bound violations, canonical associativity/commutativity where declared, serialization round trips, evaluator equivalence, and deterministic hashes.
- Semantic metamorphic tests permute names, IDs, labels, operation labels, curriculum/generation labels, and candidate ordering; semantic identity and certification outcomes must remain invariant when executable content is unchanged.
- Behavioral tests construct syntactically distinct equivalents, constants, no-ops, parent copies, sibling copies, trigger-only overfits, anti-scope leaks, and cost-only improvements; every class must receive the expected independent reason code.
- Parameter tests prove trials are actually executed, objective values recompute, identical optima have independent provenance, final blind data is unreadable, and hardcoded `0.5`/unit-weight collapse triggers integrity failure.
- Label-permutation tests shuffle candidate class labels and expected-operation labels. Hidden-field taint tests seed evaluator-only sentinels into world construction and fail on any presence, derivation, serialization, memory retention, or influence in synthesis/certification processes.
- Blindness tests inspect schemas, process arguments, environment variables, open files, imports, IPC payloads, memory/checkpoint fields, logs, and serialized artifacts. Candidate generation and certification must have separate seed ledgers and no shared mutable state.
- Independent audit recomputes semantic hashes, fingerprints, operation compliance, witness validity, gate vectors, template counts, and candidate replay from raw artifacts using code that is not imported by the synthesis/certification implementation.
- The Phase 6 audit enumerates every candidate, not only promotions, and reconciles proposed, integrity-rejected, certification-rejected, quarantined, promoted, and replayed counts exactly.

### Decision allocation and benchmarks

Phase 6 is a candidate-integrity program, not an extension of the prior 300K canonical-decision budget. Before execution, `phase6.yaml` freezes candidate/search budgets, grammar version, every operation stratum, split sizes, frozen audit-bank hashes, and compute limits. The benchmark must include retained Phase 3 template-pathology fixtures, naturally varying protected contrasts, positive/anti-scope neighbors, nuisance and causal counterfactuals, adversarial label/metadata traps, disjoint structural analogues, and random equal-budget proposal controls. Attractive aggregate error rates do not compensate for insufficient candidate diversity or a missing operation stratum.

No result can pass vacuously with zero promoted candidates or one surviving template. The accepted Phase 6 corpus must contain multiple canonical AST structures and independently selected parameter vectors, exercise every operation intended for Phase 7, and retain all failures. Counts and exposure denominators are reported rather than post-hoc padded.

### Exit gate and outputs

Phase 6 passes only when: 100% of feature references resolve to executable ASTs; zero name-only, metadata-only, constant-output, no-op, parent-identical, or sibling-identical candidates are promoted; every promotion has a unique semantic identity except a proven versioned recalibration; every behaviorally equivalent promotion has a predeclared certified improvement; 100% of promoted parameters have complete search provenance; 100% of operations satisfy the table above; 100% of promotions contain a reproduced disjoint perception-extension witness; the certifier schema and runtime are blind; label/name/operation/order permutations preserve outcomes; hidden-field taint is zero; all gate vectors are independently recomputable; template collapse fails closed; and every candidate evaluation replays deterministically.

The exact exit artifacts are the complete candidate directories, integrity reports, independent Phase 6 audit, schema validation report, split/separation audit, deterministic replay report, legacy-index manifest, and a generated `CLAIMS.md` limited to synthesis-integrity statements. Phase 7 cannot begin while any applicable gate is failed, missing, vacuous, or supported only by aggregate UAR/FRR/escalation.

## 22. Phase 7 - Live Perception-Closure Runtime

### Scope

Integrate the Phase 6 executable synthesis substrate into the live situation-conditioned resolver. Preserve the approved fast loop as the first attempt, then convert every unresolved decision into explicit competing hypotheses and a bounded ambiguity-equivalence class. Search conditionally for diagnostics and evidence actions that separate the live safe/unsafe contrast, acquire targeted evidence, assemble the smallest scope-safe diagnostic program, arbitrate typed influence without additive severity stacking, and issue `ACCEPT` or `REJECT` only under a complete local closure certificate. External `ESCALATE` is a residual terminal state available only after valid perception-extension paths are exhausted, inaccessible, outside budget, or the resolver fails.

Phase 7 depends on a sealed passing Phase 6 run and may load only Phase 6 candidates whose executable contracts and independent certifications remain valid. Every runtime-created candidate must pass the same Phase 6 integrity layer. Phase 8 is blocked until all Phase 7 microbenchmark, trace, scope, closure, and residual-escalation gates pass.

### Files made or changed

- `configs/phases/phase7.yaml`, `configs/perception_closure_v04/runtime.yaml`, ambiguity-family fixtures, query/evidence budgets, authority levels L0-L3, typed-channel rules, sparse-basis limits, and microbenchmark manifests;
- `schemas/v04/{hypothesis,ambiguity_state,perception_action,query_record,active_case_program,local_closure_certificate,residual_escalation,perception_trace,persistent_knowledge}.schema.json`;
- `src/mavs10d/core/runtime.py` extension preserving the approved fast loop and explicit terminal semantics;
- `src/mavs10d/resolution/{hypotheses,ambiguity,perception_search,query_planner,program_builder,closure}.py`;
- `src/mavs10d/diagnostics/{typed_channels,interactions}.py` and Phase 7 integration of `diagnostics/contracts.py`;
- `src/mavs10d/certification/{local,persistent}.py`;
- `src/mavs10d/learning/consolidation.py` and `src/mavs10d/memory/negative_knowledge.py`;
- `src/mavs10d/metrics/perception_closure.py` and runtime reporting adapters;
- `scripts/{compile_phase7_microbenchmarks,run_phase7_runtime,validate_phase7_traces,audit_phase7_closure,replay_phase7}.py` and a Phase 7 orchestrator;
- `tests/phase7/` unit, integration, state-machine, metamorphic, leakage, budget, adversarial-query, closure, persistence, and replay tests;
- only `results/perception_closure_v04/phase7/` and the Version 0.4 index may receive Phase 7 outputs.

### Data and artifact contracts

```text
results/perception_closure_v04/phase7/
|-- manifests/{run_manifest,microbenchmark_manifest,seed_ledger,environment_lock,phase6_dependency}.json
|-- traces/perception_rounds.parquet
|-- traces/terminal_decisions.parquet
|-- traces/queries_and_probes.parquet
|-- traces/escalations.parquet
|-- certificates/local/<certificate_id>.json
|-- programs/<program_id>.json
|-- hypotheses/<case_id>.json
|-- persistence/{promotion_candidates,consolidation_actions,negative_knowledge}.parquet
|-- metrics/{case_metrics,round_metrics,family_metrics}.parquet
|-- integrity/{scope_activation,typed_channels,interaction_safety,trace_replay,phase6_continuity}.json
`-- reports/{phase7_report.md,phase7_audit.json,CLAIMS.md}
```

Each unresolved case trace records the fast-loop outcome; explicit hypotheses; the evidence supporting and contradicting each hypothesis; ambiguity-class membership after every round; generated, filtered, rejected, and selected actions; expected and realized conditional perception gain; positive-scope and anti-scope evaluations; evidence availability/trust; query cost and result; active program; typed influence graph; interaction certificate; authority level; budget ledger; terminal closure certificate or residual-escalation decomposition; and complete parent hashes. `QUERY`, internal probe, diagnostic-program execution, resolver round, and external `ESCALATE` are different enum values and tables; no aggregation may alias them.

### Code and coding method

1. Build the visible evidence state and attempt the selected approved configuration. A terminal certified fast-loop result exits without resolver entry; unresolved selector/confidence output alone cannot become `ESCALATE`.
2. Construct a finite hypothesis set containing at least one safe-compatible and one unsafe-compatible explanation whenever a decision is genuinely unresolved. Each hypothesis declares predicted witnesses, counterfactuals, discriminating evidence actions, scope/anti-scope, and terminal consequence.
3. Maintain `A_t`, the ambiguity-equivalence class of hypotheses consistent with current evidence and kernel invariants. Classify the unresolved contrast as missing evidence, correlated consensus, scope uncertainty, diagnostic conflict, novelty, policy ambiguity, or a versioned extension with the same full contract.
4. Generate conditional perception actions from Phase 6 diagnostics/compositions plus queries, counterfactual probes, disjoint specialists, tools, simulations, delayed observations, provenance reconstruction, alternate views, and evidence-recovery actions. Every action must target a named surviving contrast.
5. Filter through the immutable kernel, executable positive scope, anti-scope, evidence availability, semantic identity, behavioral redundancy, interaction rules, authority, budget, privacy/latency limits, and negative knowledge. Untested compositions remain observation-only; prohibited compositions cannot execute.
6. Rank valid actions lexicographically by unsafe-acceptance protection, false-rejection protection, expected ambiguity contraction/CMPG, scope risk, cost, and latency. A small safety regression cannot be traded for many closures or reduced escalation.
7. When the ambiguity is caused by a missing observation, prefer the evidence action with maximum expected protected ambiguity reduction per unit cost. Record both expected and realized query yield. Missing evidence cannot be interpreted as adverse evidence.
8. Assemble `G_t*`, the smallest legal nonredundant situation-specific program with positive conditional perception gain. Persistent library size may increase the search space but not the simultaneously influential basis. Redundant diagnostics are suppressed and every multi-diagnostic interaction requires a certificate.
9. Arbitrate typed channels: danger may support `REJECT` under a danger witness; safe may support bounded `ACCEPT`; availability may request evidence or reduce authority; scope gates influence; novelty invokes broad low-authority search; conflict invokes adjudication. Availability, scope, novelty, and conflict never directly hard-veto.
10. Produce an explanation graph with a primary causal family rather than summing unrelated severities. Multi-family terminal influence is legal only under an explicit interaction certificate.
11. Execute the chosen query/probe/program, update evidence and hypotheses, and repeat while a valid positive-value extension remains and budget permits. Every round is immutable and replayable.
12. Issue `ACCEPT` only when surviving hypotheses are safe-homogeneous, a safe witness exists, and all closure obligations pass. Issue `REJECT` only for unsafe-homogeneous hypotheses with a danger witness and all obligations passing.
13. Issue external `ESCALATE` only for true irreducibility, inaccessible required evidence, exhausted bounded budget, or resolver failure. Persist the untried/invalid candidates and exact proof that no permitted positive-value path remained.
14. After delayed outcome/governance feedback, route repeated successful local programs through Phase 6 blind persistent certification. Consolidation may merge, narrow, split, retire, quarantine, or prohibit compositions; it preserves evidence/lineage and may not activate a candidate globally.
15. Persist reusable semantic distinctions, scopes/anti-scopes, high-yield query policies, legal/prohibited interactions, compact closure programs, failure signatures, and negative knowledge. Cap active eligibility, periodically re-certify under shifted priors, and require every persistent diagnostic to outperform its parent or a simpler basis on closure value.

### Tests, validation, and audit requirements

The locked microbenchmark families are authoritative:

| Family | Required behavior |
|---|---|
| Immediately separable | Approved fast loop closes; resolver-entry count is zero. |
| One-query separable | Resolver requests the correct evidence and closes in one internal round. |
| Multi-step separable | Resolver selects a valid sequence, updates hypotheses correctly, and does not waste budget on irrelevant actions. |
| Masked safe evidence | Availability/recovery query finds the safe witness; absence is never converted into danger. |
| Harmful versus benign correlation | Independence/provenance evidence separates mechanisms without a broad raw-correlation veto. |
| Scope neighbor | Superficial positive-scope similarity is defeated by executable anti-scope; influential leakage is zero. |
| Conflicting diagnostics | Attribution/counterfactual probes resolve the conflict without additive severity stacking. |
| New composition | Known primitives form a genuinely new executable distinction with an interaction certificate. |
| Genuinely new semantic need | Provisional L0/L1 hypotheses guide evidence acquisition but cannot issue an unauthorized terminal action. |
| Irreducible pair | The resolver proves no permitted action separates the pair and escalates with the irreducible reason. |
| Adversarial query trap | Poisoned or low-yield evidence paths are rejected using provenance and negative knowledge. |
| Budget-limited case | Escalation is attributed to budget exhaustion with the complete ledger, not generic uncertainty. |

Tests additionally cover hypothesis consistency/update laws, ambiguity contraction, query accounting, sparse-basis minimality, scope and anti-scope boundaries, authority bounds, typed-channel prohibitions, interaction certificates, kernel invariants, closure-certificate independence, residual decomposition, persistent handoff, consolidation/retirement, negative-knowledge reuse, process/hidden-field isolation, deterministic replay, and all Phase 6 continuity gates. Independent audit code recomputes every certificate obligation and verifies that no terminal action depends on an uncertified or out-of-scope influence path.

### Decision allocation and benchmarks

Phase 7 is a locked runtime microbenchmark and closure-trace program, not part of the old 300K budget. `phase7.yaml` freezes case counts per family, separability/access/scope/novelty/interaction/budget strata, query budgets, latency/privacy costs, library sizes, and seeds before execution. Separability levels are immediate, one-query, multi-step, and irreducible. Evidence access covers available, delayed, costly, corrupted, adversarially masked, and permanently inaccessible. Scope covers clean, neighboring confounder, overlapping families, and structural reset. Novelty covers known primitive, new composition, new scope, and genuinely new semantics. Interaction covers single cause, certified two-family interaction, redundancy, and contradictory witnesses. Budget covers unrestricted diagnostic research, industrial latency, and strict call limits. The same cases replay under library-size sweeps to prove that active basis size remains bounded.

### Exit gate and outputs

Phase 7 passes only with zero observed UAR and FRR on the fully observable core with one-sided bounds; residual escalation equal to the known irreducible mass there; zero deterministic-fixture closure errors; exact separation of query/probe/round/escalation counters; zero influential out-of-scope activation on retained and blind neighbors; bounded median active basis independent of total library size; a preregistered majority of automated queries producing measurable protected ambiguity contraction; zero typed-channel hard-veto violations; zero uncertified/prohibited interaction influence; 100% escalation decomposition; continued Phase 6 integrity for every runtime-created candidate; blind-only persistent handoff; and complete replay of every round, query, hypothesis update, active program, certificate, and terminal action.

The required outputs are all paths in the Phase 7 artifact contract, per-family and per-obligation metrics, all failed closure attempts, query-yield distributions, basis-size/library-size curves, persistence/consolidation records, an independent zero-gap Phase 7 audit, and a `CLAIMS.md` limited to passed runtime/microbenchmark gates. Phase 8 cannot begin until these outputs are sealed and all gates pass.

## 23. Phase 8 - Ablation and Integrity Program

### Scope

Falsify the anti-gaming substrate, live Perception-Closure runtime, and persistence/consolidation theory before spending either Phase 9 three-generation evidence bank. Phase 8 is a staged, preregistered causal matrix on the same locked Phase 7 microbenchmark and a sealed pre-rerun bank. Every comparison uses identical cases, visible information, seeds, method budget, query/tool/model-call budget, latency budget, compute budget, metric code, and report policy except for the one declared factor.

Phase 8 depends on sealed passing Phase 6 and Phase 7 runs. It must not tune the full system or rewrite an expected ablation direction after results are visible. Phase 9 remains blocked until the full system passes, integrity ablations fail or degrade in the causally predicted way without invalidating the harness, architecture/persistence comparisons are complete, and label permutations leave the benchmark invariant.

### Files made or changed

- `configs/phases/phase8.yaml` and exact single-factor configs `configs/ablations/v04/{I0-I11,P0-P15,L0-L10}.yaml`;
- a Phase 8 ablation registry that validates one declared semantic toggle, produces a normalized config diff, and refuses hidden multi-factor drift;
- matched-budget and shared-bank execution adapters for synthesis, runtime, persistence, legacy, oracle, and random controls;
- `schemas/v04/{ablation_definition,ablation_result,causal_contrast,matched_budget}.schema.json`;
- `scripts/{compile_phase8_matrix,run_phase8_ablations,validate_phase8_isolation,aggregate_phase8,audit_phase8}.py` and orchestrator;
- `src/mavs10d/metrics/phase8_integrity.py` and causal report generation;
- `tests/phase8/` registry, isolation, matched-budget, directionality, permutation, leakage, replay, and statistics tests;
- only `results/perception_closure_v04/phase8/` and the Version 0.4 result index may receive Phase 8 artifacts.

### Common ablation contract

For every ID, `full_config.json`, `ablation_config.json`, `config_diff.json`, `shared_bank_manifest.json`, `matched_budget.json`, `seed_ledger.json`, `metrics.parquet`, `paired_deltas.parquet`, `trace_index.json`, `causal_contrast.json`, `failures.parquet`, and `audit.json` are required under `results/perception_closure_v04/phase8/ablation_results/<ID>/`. `causal_contrast.json` records the isolated factor, unchanged fields, causal question, preregistered expected direction, required metrics, confidence method, pass/fail interpretation, and whether a surprising result revises the theory or invalidates the harness. All negative and null results are retained.

Unless a row says otherwise, the unchanged contract is the full Version 0.4 implementation, same executable candidates, worlds, cases, evidence, seeds, participant initialization, kernel, scopes, budgets, metrics, and operating points. `P15` oracle and leakage ablations `I6/I7` are diagnostic bounds/integrity attacks, never deployable competitors.

### Required synthesis-integrity ablations

| ID | Isolated factor and affected files/config | What remains unchanged | Causal question | Required metrics and artifacts | Pass/fail interpretation |
|---|---|---|---|---|---|
| I0 | Full executable synthesis reference; `I0.yaml`, all Phase 6 modules enabled. | Locked Phase 6/7 banks and budgets. | What does the integrity-complete synthesis system achieve? | Base bundle plus candidate diversity, template count, semantic/behavior classes, gate vectors, witness success. | Must pass every Phase 6 gate; otherwise all Phase 8 synthesis comparisons are blocked. |
| I1 | Replace structure search with fixed outer template plus renamed features; `I1.yaml`, `learning/structure_search.py` toggle. | Parameter/search budget, evidence, certifier, metrics, and candidate count. | Does integrity reject the exact Phase 3 pathology? | Base bundle plus `template_collapse_report.json` and name-only rejection ledger. | Integrity layer must reject before outcome metrics are interpreted; any promotion fails Phase 8. |
| I2 | Disable semantic hashing/dedup only; `I2.yaml`, `diagnostics/semantic_hash.py`. | Behavioral dedup, fitting, certifier, runtime, and budgets. | Can name-only/exact semantic duplicates enter certification or eligibility? | Duplicate-class counts, certification pressure, active-eligibility growth, semantic collision report. | Duplicate/pressure must measurably increase while protected harness remains valid; no change means the module is not functioning or test diversity is inadequate. |
| I3 | Disable behavioral fingerprint dedup only; `I3.yaml`, `diagnostics/behavioral_fingerprint.py`. | Semantic hashes, fitting, operation checks, banks, and budgets. | Can syntactically distinct but behaviorally identical candidates accumulate? | Behavioral-equivalence count, eligibility pressure, redundancy, active basis, interaction/conflict. | Equivalents or pressure must increase; protected performance improvement alone cannot justify duplicates. |
| I4 | Disable parameter fitting and use fixed `0.5`/unit values; `I4.yaml`, `learning/parameter_fit.py`. | Structure proposals, splits, certifier, scopes schema, and compute budget reserved equally. | Does real fitting prevent template collapse and poor scope/calibration? | Parameter distributions, calibration, scope leakage, witness success, protected metrics, unused-budget accounting. | Fixed values should reduce fit/witness/scope quality or reproduce collapse; equivalence requires investigating whether fitting is inert. |
| I5 | Disable operation-specific constraints only; `I5.yaml`, `learning/operation_constraints.py`. | Candidate ASTs, fits, blind certifier, and banks. | Do operation labels become metadata rather than executable semantics? | Operation compliance by type, metadata-only count, parent/sibling identity, promotion rate. | Noncompliant labeled operations must increase; if none do, fixtures do not exercise the contract. |
| I6 | Expose operation label and expected class to certifier; `I6.yaml`, `certification/blind_api.py` attack schema. | Executable inputs, bank, gate definitions, and budget. | Does metadata leakage inflate apparent certification? | Blind versus exposed gate accuracy, promotion delta, permutation sensitivity, taint trace. | Exposure must never improve valid blind performance; any improvement is leakage and invalidates affected results. |
| I7 | Expose hidden world/oracle construction fields; `I7.yaml`, blind API/evaluator firewall attack. | Candidate runtime, public evidence, metrics, and budget. | Can privileged leakage create impossible performance? | Hidden-field taint, performance delta, impossible-witness count, process/file-access trace. | Any improvement or memory contamination invalidates the harness; firewall must flag the attack. |
| I8 | Remove mandatory perception-extension witness gate; `I8.yaml`, `certification/gates.py`. | All other gates, certifier blindness, banks, and budget. | Can candidates promote without separating a previously inseparable contrast? | Witness-missing promotions, no-op/parent identity, downstream closure value, retained regression. | Missing-witness promotions must appear or the ablation is ineffective; any such promotion demonstrates witness necessity. |
| I9 | Disable counterfactual dependency audit only; `I9.yaml`, candidate counterfactual gate. | Scope, retained, holdout, adversarial gates, and fitting. | Can confounded or label-leaking dependencies pass? | Nuisance/causal counterfactual violations, leakage, false witness rate, promotion delta. | Violations must increase on planted confounds; failure to detect planted confounds invalidates the test. |
| I10 | Disable template-collapse alarm only; `I10.yaml`, `integrity/template_collapse.py`. | Semantic/behavior dedup, certification, proposals, and budgets. | Would the pipeline publish a one-template run when aggregate metrics look attractive? | Template distribution, integrity status with/without alarm, publication decision trace. | The planted one-template run must become publishable only under ablation; otherwise the alarm path is not isolated. |
| I11 | Replace structured proposal generation with budget-matched random generation; `I11.yaml`, proposal-engine selector. | Grammar, fitting, certifier, exact candidate/compute/query budget, and banks. | Does structured synthesis outperform equal-budget random search? | Valid/witnessed candidate yield, protected closure, search cost, semantic diversity, harmful/no-op rate. | Full synthesis must improve at least one preregistered yield/closure metric without protected regression; otherwise structured-discovery attribution is unsupported. |

### Required Perception-Closure runtime ablations

| ID | Isolated factor and affected files/config | What remains unchanged | Causal question | Required metrics and artifacts | Pass/fail interpretation |
|---|---|---|---|---|---|
| P0 | Full Version 0.4 runtime reference; `P0.yaml`. | Locked Phase 7 system/banks/budgets. | What does complete Perception Closure achieve? | Base bundle plus all Phase 7 metrics/certificates. | Must pass all Phase 7 gates or runtime causal claims stop. |
| P1 | Approved configuration only; bypass resolver in `P1.yaml`/`core/runtime.py`. | Same fast loop, cases, evidence, terminal policy, and budget accounting. | What is unresolved without situational closure? | Initial unresolved, local resolution, residual escalation, UAR/FRR. | P0 must improve local resolution/residual escalation without protected regression. |
| P2 | Remove explicit hypothesis set; generic confidence search in `resolution/hypotheses.py`. | Candidate actions, queries, scopes, and budget. | Does generic confidence choose the wrong perception extension? | Separating-action accuracy, ambiguity contraction, closure error, query waste. | Wrong actions/query waste or closure error should rise; no effect challenges hypothesis representation. |
| P3 | Replace conditional PE with global utility in `resolution/perception_search.py`. | Hypotheses, candidates, scopes, budgets. | Does global utility activate irrelevant diagnostics? | CMPG, irrelevant activation, scope leakage, active basis, FRR/escalation. | Irrelevance/leakage or burden should rise; otherwise conditionality is not evidenced. |
| P4 | Disable active query planner; `resolution/query_planner.py`. | Diagnostic search, available evidence interfaces, budgets charged but unused. | How much ambiguity requires targeted observation? | Query yield, local resolution, evidence-unavailable escalation, time/rounds. | One-query/masked/multi-step resolution must degrade without protected improvement. |
| P5 | Remove positive/anti-scope activation contract; `diagnostics/contracts.py`. | Candidate functions, hypotheses, query planner, kernel. | Do explicit scopes prevent leakage and FRR? | Scope/anti-scope violations, UDI, FRR, residual escalation, neighbor behavior. | Leakage/FRR should rise on neighbor suites; no effect invalidates scope attribution. |
| P6 | Remove sparse-basis selection; activate all eligible diagnostics in `program_builder.py`. | Library, candidates, scopes, budgets, terminal rules. | Do redundant active diagnostics create conflict and escalation? | Active basis, redundancy, conflict, interaction pressure, FRR/escalation, cost. | Basis/conflict/burden should grow; flat results require revising library-pathology theory. |
| P7 | Replace causal arbitration with additive severity stacking; `typed_channels.py`/runtime aggregator. | Same diagnostic outputs, scopes, queries, kernel bounds. | Does semantic collapse recreate the ambiguity band? | FRR, escalation, channel contributions, conflict, closure errors. | Predicted FRR/escalation pathology should reappear without UAR benefit. |
| P8 | Collapse typed channels; `diagnostics/typed_channels.py`. | Diagnostics, queries, scopes, budget, resolver. | Do novelty/masking/scope signals become false danger? | Meta-signal hard-veto count, FRR, unnecessary rejection/escalation, query suppression. | Any false-danger pressure demonstrates necessity; P0 must have zero such violations. |
| P9 | Disable interaction certificates; `diagnostics/interactions.py`. | Individual certifications, scopes, sparse limit, cases. | Can individually valid diagnostics become unsafe together? | Uncertified composition influence, interaction violations, UAR/FRR, conflict. | Planted unsafe combinations must activate/degrade; no effect means interaction fixtures are inadequate. |
| P10 | Remove local closure certificate; terminalize by confidence in `resolution/closure.py`. | Hypotheses/evidence/actions and terminal thresholds. | Does confidence substitute incorrectly for decision-homogeneous evidence? | Closure obligation failures, closure UAR/FRR, witness absence, replay gaps. | Incorrect or uncertified terminals should rise; any P0 uncertified terminal is itself a failure. |
| P11 | Immediately escalate on selector uncertainty; bypass resolver. | Fast loop, escalation semantics, cases, budgets. | What is the causal value of the resolver itself? | Initial unresolved versus residual escalation, local resolution, burden, protected errors. | P0 must reduce residual escalation/closure burden without protected regression. |
| P12 | Force binary terminal decision; disable external escalation. | Same evidence and resolver up to terminal fallback. | Is apparent zero escalation bought with errors? | UAR, FRR, closure errors, residual escalation, cost. | Escalation reaches zero only as a diagnostic bound; protected errors must expose the safety cost. |
| P13 | Reject on unresolved; `P13.yaml` terminal fallback. | Same resolver evidence/budget until fallback. | What is the false-rejection cost of blunt containment? | FRR, safe exposure, escalation, unresolved composition. | FRR should materially rise; it cannot be presented as autonomy. |
| P14 | Raw-correlation hard veto; legacy DS-CF ablation adapter. | Same evidence, cases, cost, and other kernel rules. | Does pre-DS-CF overbreadth recur? | Safe-correlation FRR, hard-veto causes, UAR, escalation. | Safe correlated cases must reveal overbreadth; any favorable aggregate is non-deployable. |
| P15 | Oracle evidence/closure access; evaluator-only adapter. | Same worlds and outcome metrics; oracle access explicitly uncharged and quarantined. | What is the upper bound when all separating evidence is available? | Oracle gap in UAR/FRR/residual escalation/rounds and evidence-unavailable mass. | Diagnostic upper bound only; inclusion in competitive claims fails audit. |

### Required persistence and consolidation ablations

| ID | Isolated factor and affected files/config | What remains unchanged | Causal question | Required metrics and artifacts | Pass/fail interpretation |
|---|---|---|---|---|---|
| L0 | Full persistence plus consolidation; `L0.yaml`. | Same G1-G3 banks, participant budget, and runtime. | What does the complete cumulative learner achieve? | Base bundle plus generation/retention/consolidation metrics. | Reference must pass retention, leakage, growth, and Phase 6 integrity gates. |
| L1 | Fresh reset each generation; clear all learned state. | Identical later-generation ledgers, seed, code, and compute/memory accounting. | What is the value of all retained governance knowledge? | Paired cumulative-fresh deltas, cold start, closure, burden, protected metrics. | L0 must be no worse on UAR/FRR and improve a preregistered learning/burden metric. |
| L2 | Freeze after G1; disable later synthesis/consolidation. | G1 state, G2/G3 ledgers, runtime, budgets. | Does learning beyond initial discovery add value? | G2/G3 closure, recurrence, new-scope/composition performance, costs. | L0 improvement supports continuing learning; parity/frozen win limits the claim. |
| L3 | Disable consolidation/retirement; retain every candidate. | Synthesis, certifications, memory budget accounting, ledgers. | Does library growth recreate leakage/escalation? | Eligibility/library/basis size, redundancy, scope leakage, escalation, FRR, retrieval cost. | Predicted growth pathology should worsen; no effect requires revising consolidation theory. |
| L4 | Disable negative knowledge. | Positive memory, diagnostics, query policies, budgets. | Does the system rediscover harmful programs and low-yield queries? | Repeated failed program/query rate, time/cost, violations, recurrence. | Rediscovery must rise on recurrence fixtures; otherwise negative knowledge is not evidenced. |
| L5 | Persist ontology only. | Same byte budget, G2/G3 cases, fast/runtime code. | What does semantic memory contribute without executable diagnostics? | Transfer, TTD/TTC, local resolution, query cost, synthesis count. | Separates semantic recognition from executable closure; no standalone superiority claim. |
| L6 | Persist diagnostics only; reset scopes/query policies/ontology/programs. | Same retained-byte budget and ledgers. | Are scopes and query policies essential memory? | Scope leakage, query yield, closure, recurrence, negative transfer. | Leakage/burden should expose missing contextual memory; otherwise persistence model is incomplete. |
| L7 | Persist query policies only. | Diagnostics/scopes/programs reset; same memory budget. | Is reusable evidence acquisition valuable independent of diagnostic growth? | Query yield, rounds, evidence-unavailable escalation, protected metrics. | Improvement supports query-policy memory; no gain limits that claim. |
| L8 | Persist compact case programs only. | Other learned objects reset; byte budget matched. | Are reusable closure operators the most useful memory unit? | Time/rounds to closure, recurrence, complexity, transfer, leakage. | Compare lexicographically to L5-L7; superiority is supported only without protected/scope regression. |
| L9 | Remove active-eligibility cap; all retained knowledge searchable/eligible. | Same stored library, runtime, cases, query/compute accounting. | Does unlimited eligibility violate sparse influence/library health? | Eligibility/basis size, retrieval cost, redundancy, leakage, escalation, interactions. | Pressure/pathology should rise; a flat result requires testing larger libraries before accepting the cap theory. |
| L10 | Disable periodic re-certification. | Original certifications, retained state, shifted G2/G3 banks. | Do stale scopes fail under shifted generations? | Stale-scope activation, leakage, protected errors, quarantine/rollback, retention. | Shifted-scope failures should rise; zero effect limits re-certification attribution. |

### Code and coding method

- Freeze all ablation definitions, expected causal directions, primary metrics, uncertainty methods, and failure interpretations before execution.
- Validate each ablation against the registry and reject any undeclared config/source difference. Runtime monkey-patching without a serialized toggle is prohibited.
- Replay identical locked banks and paired seeds. Match synthesis attempts, queries, evidence interfaces, model/tool calls, latency, compute, tokens, memory, and candidate budgets; unused capacity is reported.
- Separate harness-invalidating leakage attacks from mechanistic performance ablations. I6/I7 success means the firewall detected and quarantined the exposure, not that the exposed method performed well.
- Report protected metrics first, then local resolution/residual escalation, then perception/scope/integrity, then burden. No burden gain offsets protected regression.
- Preserve all expected, unexpected, null, negative, and theory-revising results. A failed predicted direction updates the causal theory; it is never silently removed or used to retune the bank.

### Decision allocation and benchmarks

All I/P/L conditions replay the same Phase 7 locked microbenchmark and sealed pre-Phase-9 bank. The pre-rerun bank includes a matched diagnostic replay of the preserved `phase4_original` >=500-world tournament bank where its immutable ledgers can be reproduced; its purpose is to measure whether the old escalation band contracts under Perception Closure, not to supply a new blind claim. Ablation replays do not redefine canonical opportunities. Phase 8 configs freeze exact case counts, strata, seeds, attack fixtures, candidate/query budgets, library sizes, and paired comparisons. The pre-rerun bank is disjoint from the final Phase 9 blind bank and cannot be used to fit Phase 9 parameters after Phase 8 closes.

### Exit gate and outputs

Phase 8 passes only when I0/P0/L0 retain their prerequisite gates; I1 is rejected before performance interpretation; removing semantic or behavioral dedup measurably increases duplicates/eligibility pressure; I6/I7 cannot improve valid blind performance and are detected by taint/firewall audits; P0 improves local resolution over P1 without protected regression; scope/sparse/additive/no-consolidation ablations reproduce predicted pathology or the causal theory is explicitly revised before Phase 9; all comparator budgets and single-factor diffs validate; label/name/operation/order permutations preserve nonsemantic outcomes; no gate is rewritten; and every result replays.

The required outputs are the full per-ID bundles, synthesis/runtime/persistence causal tables, matched-budget ledger, permutation and hidden-field reports, negative/null result inventory, theory-revision ledger, independent Phase 8 audit, and generated Phase 8 `CLAIMS.md`. Phase 9 cannot begin until the full system passes and every integrity/harness condition is resolved fail-closed.

## 24. Phase 9 - Three-Generation Phase 5 Revalidation

### Scope

Repeat the original Phase 5 three-generation question with the intended Perception-Closure Self-Learning MAVS using two isolated tracks: a retrospective paired rerun on the exact original Phase 5 bank and a separately generated, preregistered, sealed, genuinely blind claim-bearing bank. Compare cumulative, fresh, and frozen-after-G1 Version 0.4 learning against legacy, fixed, reduced-learning, random, oracle, raw-memory, and required Phase 8 ablation controls. Evaluate lexicographically by UAR, FRR, residual external escalation, then query/compute/human burden. Preserve the original negative Phase 5 conclusion and use Track A only for diagnostic paired comparison; only Track B may support revised Self-Learning claims after Phase 10.

Phase 9 depends on sealed passing Phase 6-8 artifacts and frozen implementations/hyperparameters. Track A and Track B execute in separate named namespaces, processes, seed ranges, and manifests. No result from Track A may tune, delete, select, or repair a Track B participant.

### Files made or changed

- `configs/phases/phase9.yaml`, `configs/perception_closure_v04/phase9/{paired_original_bank,blind_bank}.yaml`, condition/comparator registry, exact original-bank reproduction manifest, new-bank generator manifest, and generation-boundary persistence matrix;
- `schemas/v04/{phase9_generation_manifest,phase9_participant_state,generation_summary,phase9_claim_gate}.schema.json`;
- adapters that replay legacy A0-A49 without importing legacy result files as current evidence, Version 0.4 cumulative/fresh/frozen conditions, fixed MAVS/DS-CF, reduced-learning controls, random proposal, oracle bounds, raw-memory, and selected/full Phase 8 ablations;
- Phase 9 bank compiler, information-firewall runner, generation-boundary sealer, participant-state auditor, aggregator, and report generator;
- `src/mavs10d/metrics/{perception_closure,synthesis_integrity,transfer}.py` extensions for Version 0.4 generation metrics and lexicographic paired comparisons;
- `scripts/{compile_phase9_banks,run_phase9_track,validate_phase9_firewall,validate_phase9_state,aggregate_phase9,audit_phase9}.py` and separate Track A/Track B orchestrators;
- `tests/phase9/` bank separation, original-ledger identity, participant-state legality, paired replay, hidden-field taint, metrics, trend-gate, result-isolation, and deterministic-replay tests;
- only the Phase 9 Version 0.4 namespace and result index may receive new Phase 9 artifacts.

### Two-track bank and result contract

```text
results/perception_closure_v04/phase9/
|-- paired_original_bank/
|   |-- manifests/generation_{1,2,3}/
|   |-- checkpoints/generation_{1,2,3}/
|   |-- candidate_cards/
|   |-- decision_traces/
|   |-- ablation_results/
|   |-- integrity/
|   |-- summaries/
|   `-- reports/
`-- blind_bank/
    |-- manifests/generation_{1,2,3}/
    |-- checkpoints/generation_{1,2,3}/
    |-- candidate_cards/
    |-- decision_traces/
    |-- ablation_results/
    |-- integrity/
    |-- summaries/
    `-- reports/
```

Track A reuses the original Phase 5 world ledgers under `results/manifests/phase5_authoritative/phase5/generation_{1,2,3}/`, together with the bound schedules, seeds, 300-world x 50-opportunity allocation, and 15,000 canonical opportunities per generation where legally and technically reproducible: 45,000 canonical opportunities total. The legacy manifest must compare source hashes and document every unavailable artifact before execution; silent approximation is prohibited. Track A is never blind and is diagnostic-only.

Track B contains newly generated sealed worlds with the same preregistered families, generation roles, difficulty distribution, 300 x 50 allocation, resource budgets, and 15,000 canonical opportunities per generation: a separate 45,000-opportunity claim bank. It uses new seeds, hidden semantic truth, minimum separating actions, new world identities, and disjoint surface/structural/adversarial realizations. Track B is sealed before any Version 0.4 participant runs. Method/control/ablation replays use the same canonical opportunities and do not inflate either bank's count.

### Required conditions and comparators

| Condition | Required role and state rule |
|---|---|
| Version 0.4 cumulative | Retain only certified semantics, scopes, anti-scopes, query policies, compact closure programs, negative knowledge, legal compositions, and condition-valid calibration across G1-G3. |
| Version 0.4 fresh | Reset all learned state at every generation while replaying the identical ledger; isolates persistence. |
| Version 0.4 frozen-after-G1 | Learn/certify/consolidate in G1, freeze afterward; isolates continuing synthesis and consolidation. |
| Legacy A0 full MAVS-SL | Historical architecture control in a quarantined legacy-compatible process. Track A also reruns the complete original A0-A49 registry when reproducible; no legacy result is copied into current metrics. |
| A1 frozen/no learning | Calibration/distribution-exposure control. |
| A2 threshold-only | Tests whether any gain is merely parameter tuning. |
| A3 selector-only | Tests context adaptation without new executable semantics. |
| Fixed full MAVS and DS-CF lineage | Non-self-learning governance controls with frozen state. |
| Raw-memory/matched-memory and reduced-learning controls | Bound abstraction versus memorization and isolate retained-state mechanisms under matched bytes. |
| Random proposal engine | Equal synthesis-candidate/compute budget control for structured discovery. |
| Oracle evidence or oracle closure | Evaluator-only upper bound, quarantined and never deployable or included in superiority claims. |
| Phase 8 I/P/L ablations | Run the preregistered claim-critical ablations on both banks with matched budgets; retain the complete Phase 8 matrix in Track A and at minimum every ablation used for a Track B mechanistic claim. Omitted Track B ablations make the associated mechanism claim unsupported. |

### Information firewall and generation protocol

- World generation writes hidden semantic truth, minimum separating action, expected separability, and evaluator outcomes only to an evaluator-owned sealed manifest.
- Synthesis sees public grammar, permitted evidence, traces, released/delayed outcomes, and public contracts; it never sees operation answers, desired promotion labels, hidden minimal diagnostics, final metrics, or evaluator truth.
- Certification receives metadata-stripped candidates and frozen suites only through the Phase 6 blind API. Final evaluation is a separate process/container identity with sealed seeds and signed outputs.
- No post-unseal parameter change, threshold change, candidate deletion, operating-point deletion, metric change, exclusion, or result-directed retry is allowed. Infrastructure failures remain logged and rerun only under predeclared retry rules.
- G1 covers discovery under initial known and novel ambiguity families and measures cold-start errors, queries, local resolution, genuine synthesis, and promotion quality.
- G2 covers homologous transfer, altered priors, new scopes, and new compositions and compares cumulative, fresh, and frozen-after-G1 on identical worlds.
- G3 covers structural reset, adversarial recombination, scope neighbors, evidence masking, library-targeted attacks, and recurrence to determine whether retained perception knowledge compounds or leaks.
- At each boundary, seal results, persist only condition-legal state, hash checkpoints, audit hidden-field contamination, and prevent any future manifest read. After G3, run retained counterexamples, rotating scope holdouts, template-collapse, label/operation permutation, certifier-blindness, hidden-field taint, and deterministic replay before summaries are generated.

### Metrics and statistical decision rules

| Family | Required generation-level metrics |
|---|---|
| Protected decisions | UAR, FRR, closure UAR, closure FRR, unsafe/safe exposure counts, exact/one-sided uncertainty bounds, worst world, and tail behavior. |
| Autonomy | Initial unresolved rate, automated query/probe/round rates, local resolution rate, residual external escalation, irreducible ambiguity rate/recall, and residual reason decomposition. |
| Perception | Conditional PE/CMPG, ambiguity contraction per round, selected separating-action accuracy, perception-witness count/reproduction, and query yield. |
| Scope/influence | Scope leakage, anti-scope violations, unintended decision influence, active basis size, active eligibility, interaction violations, typed-channel violations, and causal-family arbitration. |
| Synthesis integrity | Canonical AST/template count, semantic hashes, parameter-vector distribution, behavioral equivalence classes, constant/no-op/name-only/parent-identical counts, operation compliance, and search provenance completeness. |
| Certification integrity | Independent gate vectors, blindness, label/name/operation/order permutation invariance, and trigger/retained/holdout/boundary/counterfactual/adversarial outcomes. |
| Learning | Feedback-aware time to detection, time to local closure, time to persistent certification, recurrence, consolidation gain, library/eligibility size, negative-knowledge reuse, retention, forgetting, and negative transfer. |
| Burden | Queries, probes, rounds, model/tool calls, latency, compute, tokens, memory, program complexity, human/domain escalations, and consolidation/re-certification cost. |
| Traceability | Complete replay rate, manifest/hash integrity, participant-state legality, forbidden future reads, and hidden-field contamination count. |

All comparisons follow `Lex(UAR, FRR, ResidualEscRate, QueryCost, Latency, Complexity)`. Report paired point estimates and preregistered confidence bounds by generation, condition, bank, stratum, and world. Track A and Track B are never pooled. Generation trends use paired G1-G2-G3 slopes with difficulty diagnostics; a favorable G3 mean cannot substitute for a failed trend or cumulative/fresh comparison.

### Tests, validation, and audit requirements

- Prove Track A opportunity/seed/world/schedule hashes match the original Phase 5 bank or publish a pre-execution discrepancy ledger.
- Prove Track B has zero seed/world/example/template/policy/schedule/hidden-manifest overlap with development, Phase 6 certification, Phase 7/8 banks, Track A, and legacy results; include exact and near-duplicate audits.
- Validate every participant checkpoint field-by-field against cumulative/fresh/frozen/legacy/fixed/random/oracle/ablation persistence rules and matched storage/compute budgets.
- Independently recompute UAR, FRR, residual escalation, queries, closure, scope leakage, CMPG, template counts, gate vectors, generation slopes, and cumulative-fresh paired deltas from raw traces.
- Audit all candidates and terminal paths for Phase 6 integrity continuity, local-certificate validity, scope/anti-scope activation, operation semantics, taint, and result isolation.
- Replay a pinned complete sample and all protected failures; retain all negative, null, leakage, baseline-win, and theory-revising outcomes.

### Exit gate and outputs

The synthesis-integrity gate requires all Phase 6 gates in every synthesis-enabled generation/condition. The protected-core gate requires zero observed UAR and FRR on fully observable synthetic strata with one-sided bounds and exposures. Residual escalation must be at/near the known irreducible floor with no unexplained mass band. Scope leakage requires zero influential out-of-scope activation on retained and blind scope suites. Template integrity requires zero promoted name-only, constant, no-op, parent-identical, noncompliant, or unwitnessed candidates and no unaudited one-template collapse.

The trend gate requires cumulative residual escalation and scope leakage not to increase G1-G3 under stable/expanding evidence. The cumulative-learning gate requires cumulative to be no worse than fresh on UAR and FRR and to improve at least one of residual escalation, closure rounds, query cost, recurrence, consolidation gain, or time-to-closure with no retention/complexity violation. Track B must reproduce the qualitative mechanism found in Track A without old cases/labels. Required ablations must degrade predicted mechanisms without invalidating the harness. Auditability requires 100% replayable terminal decisions/escalations and zero hidden-field contamination.

Each bank must produce `generation_summary.parquet` and `.csv` for every method/condition/point/generation; candidate directories with ASTs, searches, scopes/anti-scopes, contracts, witnesses, hashes, fingerprints, and gate vectors; decision traces with hypotheses, ambiguity classes, queries, programs, certificates, and residual reasons; integrity reports `template_collapse_report.json`, `permutation_invariance.json`, `certifier_blindness.json`, `hidden_field_audit.json`, and `operation_compliance.json`; matched `ablation_results/`; `REPRODUCE.md`; environment lock; code/data hashes; seed ledger; and signed manifest. Each Track has a generated `CLAIMS.md`; Track A states diagnostic-only, and Track B claims remain provisional until Phase 10.

## 25. Phase 10 - Reproducibility, Claim, and Release Audit

### Scope

Prevent a second interpretive failure by making every revised Self-Learning claim mechanically dependent on candidate-level executable evidence, independently recomputed certification gates, complete perception traces, isolated result namespaces, and signed immutable manifests. Reproduce Phase 6 integrity, Phase 7 closure behavior, Phase 8 causal ablations, and Phase 9 paired/blind results from locked code/data/config/seed/environment inputs. Freeze a release only if the independent audit passes; otherwise preserve the run as diagnostic evidence and explicitly invalidate each affected claim.

Phase 10 depends on sealed Phase 6-9 namespaces. It may read them but cannot rewrite, repair, filter, or regenerate their accepted artifacts in place. Any required correction creates a new Version 0.4 run/version namespace and restarts every dependent gate. No Phase 9 Track B claim is release-bearing before Phase 10 closes.

### Files made or changed

- `configs/phases/phase10.yaml`, independent audit sample plan, protected-failure replay plan, release policy, signing policy, and claim-gate registry;
- `schemas/v04/{audit_manifest,claim_ledger,release_manifest,replay_comparison,results_isolation_audit}.schema.json`;
- independent audit implementations under `src/mavs10d/audit_v04/` for AST execution, semantic hashing, behavioral fingerprinting, gate recomputation, metric recomputation, taint scanning, permutation challenges, trace validation, and result isolation; production synthesis/certification metric functions may not be imported to establish independence;
- `scripts/{audit_v04_candidates,audit_v04_templates,recompute_v04_certification,run_v04_permutation_challenge,audit_v04_hidden_fields,replay_v04,validate_v04_results_isolation,generate_v04_claims,freeze_v04_release}.py`;
- one-command reproducibility entry points for complete Phase 6 integrity, Phase 7 microbenchmarks, all Phase 8 integrity/architecture/persistence ablations, a reduced Phase 9 rerun, and manifest verification;
- `tests/phase10/` audit-independence, deliberate-corruption, manifest, signature, taint, permutation, claim-generation, append-only, and release-freeze tests;
- only `results/perception_closure_v04/phase10/`, final Version 0.4 report pointers, and `results/RESULTS_INDEX.md` may be written by the audit/release process.

### Data and artifact contracts

```text
results/perception_closure_v04/phase10/
|-- manifests/{audit_manifest,seed_ledger,environment_lock,input_artifact_index}.json
|-- candidate_audit/{candidate_inventory,spot_audit,full_template_audit}.parquet
|-- certification/{recomputed_gate_vectors,gate_mismatches}.parquet
|-- permutation/{challenge_manifest,outcome_comparison}.json
|-- taint/{hidden_field_inventory,process_access_audit,memory_scan}.json
|-- replay/{sample_manifest,protected_failure_manifest,artifact_comparison}.json
|-- trace/{completeness,lineage,terminal_authority,residual_escalation}.json
|-- isolation/{legacy_hashes,v04_hashes,cross_version_manifests,overwrite_scan}.json
|-- claims/{claim_ledger.json,CLAIMS.md,claim_source_map.json}
|-- release/{release_manifest.json,signatures,tag_record,RESULTS_INDEX.snapshot.md}
|-- reports/{phase10_audit.json,phase10_audit.md,reproducibility_report.md,release_report.md}
`-- REPRODUCE.md
```

`input_artifact_index.json` enumerates every Phase 6-9 manifest and artifact with logical role, physical path, byte size, SHA-256, schema version, code/config/data/seed/environment bindings, Git object or LFS object ID, claim eligibility, and legacy/current status. Every candidate ever proposed has a candidate-level entry linking raw failure evidence, minimal contrast, AST, parameters, complete search trace, contracts, semantic identity, behavioral fingerprint, operation check, witness pair/analogue, independent gate vector, certification decision, promotion/rejection/quarantine, rollback target, runtime use, consolidation/retirement state, and all descendant traces.

### Code and coding method

1. Freeze the audit input index before reading results. Verify Git SHA, dirty-tree state, dependency lock, OS/runtime/hardware metadata, schema versions, configuration hashes, data/ledger hashes, generator hashes, seed hierarchy, process identities, and artifact hashes. Missing or mismatched bindings fail closed.
2. Re-run a stratified candidate spot audit covering every promoted operation type, every generation/condition/bank, every gate-vector pattern, every semantic/behavioral equivalence class, every rejection reason, and all protected failures. Trace from raw evidence through later runtime use and retirement/rollback.
3. Run a full template audit over every proposal, not a sample. Normalize all ASTs, enumerate parameter vectors, semantic hashes, behavioral classes, name-only variants, constants, no-ops, parent/sibling identities, operation compliance, and witness coverage. Reconcile totals with Phase 6/9 manifests.
4. Independently recompute every certification gate from raw traces and frozen cases using `audit_v04/`. Compare values, evidence cases, reason codes, and final vectors exactly or within preregistered numeric tolerances. Production aggregate counters or narrative labels are not audit evidence.
5. Execute the operation-label permutation challenge: shuffle candidate names, semantic-neutral IDs, operation labels, curriculum labels, generation labels, and candidate order while holding executable artifacts fixed. Certification and metric outcomes must remain invariant. Any changed gate/decision is an integrity failure.
6. Execute hidden-field taint auditing across source schemas, world/evaluator outputs, process arguments, environment variables, open/read files, IPC, candidate objects, traces, checkpoints, caches, logs, persistent memory, and serialized results. Plant unique evaluator-only sentinels in controlled tests and require zero participant influence or retention.
7. Deterministically replay the preregistered sample plus every unsafe acceptance, false rejection in protected fixtures, closure error, unexplained escalation, scope leak, harmful promotion, taint event, gate mismatch, quarantine, and rollback. Recompute terminal decisions, queries, programs, certificates, metrics, and hashes.
8. Validate trace completeness: every canonical opportunity has exactly one terminal record; every unresolved case has hypotheses and round lineage; every query/probe has target/result/cost; every active diagnostic has activation and influence proof; every terminal decision has authority/certificate; every escalation has residual decomposition; every learning transition has provenance and rollback.
9. Audit result isolation. Verify original Phase 0-5 files remain byte-identical to their legacy-index hashes; no legacy/current silent concatenation exists; Track A and Track B are separate; no Phase 6-8 bank contaminates Track B; every cross-version comparison has an explicit manifest; default reports point only to the current namespace.
10. Generate `claim_ledger.json` directly from audited gates. Each claim has status `supported`, `partially_supported`, `unsupported`, or `falsified`; exact supporting/failing gates; exposure counts and bounds; bank/condition/generation scope; artifact hashes; and maximum permitted language. Handwritten claim elevation is prohibited.
11. Provide one-command independent reproduction of Phase 6 integrity tests, Phase 7 microbenchmarks, Phase 8 matrix validation, reduced Phase 9 paired/blind paths, Phase 10 recomputation, and final claim generation. The reduced rerun is a reproducibility check, not a substitute for full Phase 9 evidence.
12. On success, tag the exact code commit, freeze dependency/container/environment locks, sign manifests and the claim ledger, snapshot `RESULTS_INDEX.md`, and make post-freeze changes require a new namespace/version. Phase 10 does not push, tag, or publish externally without separate user authorization; the plan defines the release artifact, not permission to mutate a remote.
    Release freezing is complete only when code, environments, manifests, signatures, result pointers, and claim language all bind to the same audited artifact graph.

### Tests, validation, and audit requirements

- Deliberate corruption tests change AST nodes, parameter values, scope bounds, evidence dependencies, gate values, trace rows, seed ledgers, result paths, and signatures; each corruption must be detected with a stable reason code.
- Audit-independence tests fail if the recomputation package imports production synthesis, certification, aggregation, or claim-decision functions.
- Environment tests reproduce in a clean pinned environment and prove that unpinned dependency, locale, timezone, hash-randomization, thread count, device, or nondeterministic kernel changes are either controlled or declared.
- Replay tests compare byte hashes for canonical JSON and exact discrete outputs, and preregister tolerances plus raw values for permitted floating-point artifacts.
- Candidate-by-candidate reconciliation proves `proposed = integrity_rejected + certification_rejected + quarantined + promoted` under documented mutually exclusive lifecycle states and tracks later retirement/rollback separately.
- Claim-generator tests inject failed, missing, and contradictory gates and require claim downgrading; an integrity failure can never be rendered as a minor limitation.
- Release tests reject dirty trees, untracked evidence, missing LFS objects, unsigned manifests, unresolved audit findings, stale result pointers, non-append-only mutation, and any provisional Track B claim.

### Decision allocation and benchmarks

Phase 10 does not create a new scientific opportunity bank. It replays the pinned audit sample, every protected failure, and the reduced preregistered reproduction subset from Phase 6-9. Sample strata and reduced-run sizes are frozen before audit execution and cannot exclude rare failures or inconvenient operation types. Full claim metrics remain those of the complete Phase 9 banks.

### Exit gate and outputs

Phase 10 passes only when all input hashes/manifests validate; every candidate is indexed; the stratified and full template audits reconcile; independent certification and metric recomputation match; permutations are invariant; hidden-field contamination is zero; required replays match; trace/lineage/authority/escalation completeness is 100%; legacy/current and Track A/Track B isolation passes; every claim is mechanically generated from audited artifacts; the reproduction commands pass in the pinned environment; and release manifests/signatures/freeze rules validate.

A failed integrity audit is not a caveat. It invalidates every dependent Self-Learning claim and preserves the affected run only as append-only diagnostic evidence. A negative scientific gate with intact integrity remains a valid negative result and produces `unsupported` or `falsified`, never a concealed result. The final outputs are the complete Phase 10 artifact tree, signed release manifest, independent audit, reproducibility package, frozen result index, and generated claim ledger/`CLAIMS.md`.

## 26. Version 0.4 coverage and advancement audit

| Normative Version 0.4 requirement | WorkPlan enforcement and required evidence |
|---|---|
| Prior Phase 3 evidence is accurately bounded | Section 19.1; 120-candidate single-template reclassification, retained pipeline claims, prohibited synthesis claims. |
| Previous results preserved without overwrite | Section 19.2; immutable legacy indexes/copies, SHA-256/LFS bindings, claim status, no silent concatenation. |
| Revised result namespace | Sections 19.2 and 21-25; `results/perception_closure_v04/phase6` through `phase10`, including Phase 9 paired/blind subtrees. |
| Executable canonical AST and explicit evidence dependencies | Phase 6 files, contracts, feature registry, evaluator, zero unresolved strings. |
| Real structure/parameter/scope/authority search | Phase 6 code steps 3-5 and parameter provenance artifacts/gates. |
| Positive scope, anti-scope, influence, and counterfactual contracts | Sections 20-21 schemas, executable contract, operation checks, boundary/counterfactual suites. |
| Name-invariant semantic hashes and behavioral fingerprints | Phase 6 data contract, semantic/behavioral equivalence reports, independent recomputation. |
| Semantic/behavioral deduplication | Phase 6 gates and Phase 8 I2/I3 causal ablations. |
| Operation-specific executable meaning | Phase 6 operation table, compliance artifacts, Phase 8 I5. |
| Perception-extension witness and disjoint analogue | Phase 6 step 10, witness schema/artifact, 100% promotion gate, Phase 8 I8. |
| Blind independent certification | Phase 6 separate processes/API/gates, label and hidden-field exclusions, Phase 8 I6/I7, Phase 10 recomputation. |
| Label/name/operation/order permutation tests | Phase 6 integrity suite, Phase 8 closure rule, Phase 9 post-G3 audit, Phase 10 challenge. |
| Hidden-field taint tests | Phase 6 process/schema scan, Phase 8 I7, Phase 9 firewall, Phase 10 full taint audit. |
| Template collapse, no-op, constant, parent-identical, name-only rejection | Phase 6 rejection rules and artifacts, Phase 8 I1/I4/I8/I10, Phase 9 integrity metrics, Phase 10 full audit. |
| Explicit competing hypotheses and ambiguity-equivalence classes | Sections 20 and 22, hypothesis/ambiguity schemas, round traces, tests. |
| Conditional perception search and targeted evidence acquisition | Phase 7 steps 4-7, query planner/artifacts, Phase 8 P2-P4. |
| Sparse scope-safe case programs | Phase 7 steps 8-10, program/activation artifacts, Phase 8 P5-P7/L9. |
| Typed influence and non-additive arbitration | Phase 7 step 9-10, typed-channel/interaction audits, Phase 8 P7-P9. |
| Local closure certification | Phase 7 steps 11-13 and certificate obligations, Phase 8 P10. |
| Conditional theorem targets and irreducible boundary remain honest | Section 20.3 assumption audits, Phase 7 finite fixtures, Phase 8 attacks, Phase 9 scoped evidence, Phase 10 claim limits. |
| QUERY/probe/round/external ESCALATE separation | Sections 20 and 22 trace contracts/gates; Phase 9 autonomy metrics. |
| Escalation only after valid extension exhaustion | Phase 7 residual proof/decomposition, P1/P4/P11-P15, Phase 9 residual gate, Phase 10 trace audit. |
| Persistent learning and consolidation without global activation | Sections 20/22, negative knowledge and library-health rules, Phase 8 L0-L10, Phase 9 cumulative controls. |
| Complete synthesis-integrity ablations I0-I11 | Section 23 exact per-ID factor/files/invariants/question/metrics/artifacts/interpretation. |
| Complete runtime ablations P0-P15 | Section 23 exact per-ID factor/files/invariants/question/metrics/artifacts/interpretation. |
| Complete persistence ablations L0-L10 | Section 23 exact per-ID factor/files/invariants/question/metrics/artifacts/interpretation. |
| Untouched Phase 4 diagnostic rerun | Phase 8 sealed pre-rerun bank; preserved historical bank, matched comparison, diagnostic-only status. |
| Original Phase 5 paired rerun and new sealed blind bank | Section 24 two-track contract and isolation. |
| Cumulative, fresh, frozen-after-G1 and all controls | Section 24 comparator matrix, legacy A0-A49 Track A, fixed/reduced/random/oracle/Phase 8 controls. |
| Lexicographic UAR, FRR, residual escalation, burden | Sections 20 and 24 metrics/rules; no compensatory scalar claim. |
| Generation, trend, scope, template, cumulative-learning gates | Phase 9 metrics and exit gate. |
| Exact result/report directory layout | Sections 19.2 and Phase 6-10 artifact trees. |
| Deterministic replay, manifests, hashes, environment/seed lock | Every phase manifest contract; Phase 10 independent replay and freeze. |
| Candidate-by-candidate executable release evidence | Phase 6 candidate directory and Phase 10 input index/full reconciliation. |
| Independent certification recomputation | Phase 10 separate `audit_v04/` implementation and mismatch artifacts. |
| Trace completeness and results isolation | Phase 10 steps 8-9 and 100% gate. |
| Claim generation from audited artifacts | Phase 10 claim ledger/status/language and fail-closed generator tests. |
| Release freezing and fail-closed claim discipline | Phase 10 step 12 and exit rule; failed integrity invalidates dependent claims. |

Advancement is strictly sequential: `Phase 6 integrity -> Phase 7 runtime -> Phase 8 falsification -> Phase 9 paired/blind revalidation -> Phase 10 release audit`. A downstream favorable metric cannot cure a failed upstream gate. A missing artifact, empty/vacuous test, altered bank, silent approximation, unreconciled count, unsigned manifest, or non-replayable result is a failed gate.

## 27. Version 0.4 `Path.md` protocol

Appending Sections 19-27 does not authorize `Path.md` to mark Phase 6, 7, 8, 9, or 10 implemented, started, passed, or complete. Until the user separately authorizes implementation, the Phase ledger remains closed at Phase 5 and may state only that the Version 0.4 work has been planned.

After implementation is authorized, `Path.md` is updated continuously in the existing evidence-ledger style. Every meaningful work step records:

1. date/time, Version 0.4 phase, generation/bank/condition where applicable, and exact WorkPlan clauses;
2. task performed and scientific/engineering question;
3. files created, modified, removed, or deliberately preserved, with the reason for each;
4. implementation decisions, interfaces, invariants, and any deviation from this plan;
5. exact commands/tests executed, exit status, test counts, seeds, configs, code/data/environment hashes, and runtime;
6. exact results and exposure denominators, including negative/null outcomes and uncertainty;
7. generated artifact paths, schemas, byte/hash bindings, and result-namespace isolation proof;
8. failures, rejected approaches, unresolved gaps, corrective actions, and whether prior evidence was invalidated;
9. independent audit findings, taint/permutation/replay results, and open reason codes;
10. commit/checkpoint/freeze identifier where applicable; and
11. an explicit advancement-gate decision with direct evidence for every condition, not a summary boolean.

No phase is complete until every stated completion condition, artifact contract, test requirement, independent audit, and exit gate in its WorkPlan section passes. Phase 6 cannot be closed by lifecycle plumbing, Phase 7 cannot be closed by aggregate error rates without valid closure traces, Phase 8 cannot be closed without all I/P/L comparisons, Phase 9 cannot be claim-bearing from Track A or an unsealed Track B, and Phase 10 cannot close with any unresolved integrity finding. If a gate fails, `Path.md` records the phase as in progress or failed/blocked according to evidence; it never records implementation success merely because code or a WorkPlan section exists.
