import { spawnSync } from "node:child_process";

const python = process.env.PYTHON || "python";
const env = { ...process.env, PYTHONHASHSEED: "0", TZ: "Asia/Karachi", OMP_NUM_THREADS: "1", MKL_NUM_THREADS: "1", OPENBLAS_NUM_THREADS: "1", NUMEXPR_NUM_THREADS: "1" };

function run(script, args = []) {
  const result = spawnSync(python, [script, ...args], { stdio: "inherit", env });
  if (result.status !== 0) process.exit(result.status ?? 1);
}

// Phase 10 step 01: initialize an isolated unsealed result namespace.
console.log('{"event":"phase10.step01.start","action":"isolated_cleanup"}');
run("scripts/clean_phase10_results.py");
// Phase 10 step 02: execute focused fail-closed tests before evidence generation.
console.log('{"event":"phase10.step02.start","action":"focused_tests_before"}');
run("-m", ["pytest", "tests/phase10", "-q"]);
// Phase 10 step 03: freeze every Phase 6-9 input artifact and candidate linkage.
console.log('{"event":"phase10.step03.start","action":"freeze_input_index"}');
run("scripts/index_v04_inputs.py");
// Phase 10 step 04: audit candidate-by-candidate lineage and lifecycle reconciliation.
console.log('{"event":"phase10.step04.start","action":"candidate_spot_audit"}');
run("scripts/audit_v04_candidates.py");
// Phase 10 step 05: audit every proposal for semantic and behavioral template integrity.
console.log('{"event":"phase10.step05.start","action":"full_template_audit"}');
run("scripts/audit_v04_templates.py");
// Phase 10 step 06: independently recompute all certification gates and Phase 9 metrics.
console.log('{"event":"phase10.step06.start","action":"independent_recomputation"}');
run("scripts/recompute_v04_certification.py");
// Phase 10 step 07: challenge name, label, generation, curriculum, and candidate order.
console.log('{"event":"phase10.step07.start","action":"permutation_challenge"}');
run("scripts/run_v04_permutation_challenge.py");
// Phase 10 step 08: audit hidden fields, process access, memory, and sentinel retention.
console.log('{"event":"phase10.step08.start","action":"hidden_field_taint"}');
run("scripts/audit_v04_hidden_fields.py");
// Phase 10 step 09: replay the pinned sample and every protected failure.
console.log('{"event":"phase10.step09.start","action":"deterministic_replay"}');
run("scripts/replay_v04.py");
// Phase 10 step 10: validate terminal, lineage, authority, influence, and residual traces.
console.log('{"event":"phase10.step10.start","action":"trace_completeness"}');
run("scripts/audit_v04_traces.py");
// Phase 10 step 11: prove legacy/current and paired/blind result isolation.
console.log('{"event":"phase10.step11.start","action":"results_isolation"}');
run("scripts/validate_v04_results_isolation.py");
// Phase 10 step 12: execute the independent one-command reduced reproduction package.
console.log('{"event":"phase10.step12.start","action":"reproduction_package"}');
run("scripts/run_v04_reproduction.py");
// Phase 10 step 13: execute the complete repository regression suite.
console.log('{"event":"phase10.step13.start","action":"full_regression"}');
run("-m", ["pytest", "-q"]);
// Phase 10 step 14: generate claim statuses and maximum language from passed gates.
console.log('{"event":"phase10.step14.start","action":"claim_generation"}');
run("scripts/generate_v04_claims.py");
// Phase 10 step 15: independently audit every WorkPlan clause and release prerequisite.
console.log('{"event":"phase10.step15.start","action":"final_audit"}');
run("scripts/audit_phase10.py");
// Phase 10 step 16: execute focused tests after final artifact generation.
console.log('{"event":"phase10.step16.start","action":"focused_tests_after"}');
run("-m", ["pytest", "tests/phase10", "-q"]);
// Phase 10 step 17: sign manifests, snapshot pointers, and freeze the release namespace.
console.log('{"event":"phase10.step17.start","action":"release_freeze"}');
run("scripts/freeze_v04_release.py");
// Phase 10 step 18: report successful completion only after the immutable seal exists.
console.log('{"event":"phase10.step18.complete","status":"PASS","release":"FROZEN"}');
