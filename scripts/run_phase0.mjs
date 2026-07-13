import { spawnSync } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

const repoRoot = resolve(import.meta.dirname, "..");
const runIdIndex = process.argv.indexOf("--run-id");
if (runIdIndex < 0 || !process.argv[runIdIndex + 1]) {
  throw new Error("--run-id is required");
}
const runId = process.argv[runIdIndex + 1];
const completedSteps = [];

function run(command, args) {
  const result = spawnSync(command, args, { cwd: repoRoot, encoding: "utf8", stdio: "inherit" });
  if (result.error) throw result.error;
  if (result.status !== 0) throw new Error(`${command} ${args.join(" ")} failed with status ${result.status}`);
}

// console.log: phase0.orchestrator.step01.start
console.log(JSON.stringify({ event: "phase0.orchestrator.step01.start", run_id: runId }));

// console.log: phase0.orchestrator.step02.clean_results
console.log(JSON.stringify({ event: "phase0.orchestrator.step02.clean_results" }));
run("python", ["scripts/clean_results.py", "--all-runs"]);
completedSteps.push("clean_results");

// console.log: phase0.orchestrator.step03.inherited_tests_before
console.log(JSON.stringify({ event: "phase0.orchestrator.step03.inherited_tests_before" }));
run("python", ["-m", "pytest", "-q", "tests/unit", "tests/integration"]);
completedSteps.push("inherited_tests_before");

// console.log: phase0.orchestrator.step04.inherited_smoke
console.log(JSON.stringify({ event: "phase0.orchestrator.step04.inherited_smoke" }));
run("python", ["scripts/run_experiment.py", "--config", "configs/experiments/synthetic_smoke.yaml"]);
run("python", ["scripts/validate_traces.py", "--input", "results/raw/synthetic_smoke.jsonl"]);
completedSteps.push("inherited_smoke_before");

// console.log: phase0.orchestrator.step05.remove_regression_output
console.log(JSON.stringify({ event: "phase0.orchestrator.step05.remove_regression_output" }));
run("python", ["scripts/clean_results.py", "--all-runs"]);
completedSteps.push("regression_output_removed");

// console.log: phase0.orchestrator.step06.compile_ledgers
console.log(JSON.stringify({ event: "phase0.orchestrator.step06.compile_ledgers" }));
run("python", ["scripts/compile_generation_ledgers.py", "--run-id", runId, "--generation", "all"]);
completedSteps.push("generation_ledgers_compiled");

// console.log: phase0.orchestrator.step07.validate_resets
console.log(JSON.stringify({ event: "phase0.orchestrator.step07.validate_resets" }));
run("python", ["scripts/validate_generation_resets.py", "--run-id", runId]);
for (const generation of [1, 2, 3]) {
  run("python", ["scripts/validate_participant_state.py", "--input", `results/checkpoints/${runId}/generation_${generation}/phase0_diagnostic_bound.json`]);
}
completedSteps.push("generation_resets_and_participants_validated");

// console.log: phase0.orchestrator.step08.validate_update_contract
console.log(JSON.stringify({ event: "phase0.orchestrator.step08.validate_update_contract" }));
run("python", ["scripts/validate_updates.py", "--input", "tests/fixtures/phase0_quarantine_update.json"]);
completedSteps.push("update_contract_validated");

// console.log: phase0.orchestrator.step09.execute_stress
console.log(JSON.stringify({ event: "phase0.orchestrator.step09.execute_stress" }));
run("python", ["scripts/run_phase0_stress.py", "--run-id", runId, "--generation", "all"]);
completedSteps.push("stress_executed");

// console.log: phase0.orchestrator.step10.validate_self_learning_traces
console.log(JSON.stringify({ event: "phase0.orchestrator.step10.validate_self_learning_traces" }));
for (const generation of [1, 2, 3]) {
  run("python", ["scripts/validate_traces.py", "--contract", "self-learning", "--input", `results/raw/${runId}/phase0/generation_${generation}.jsonl`]);
}
completedSteps.push("self_learning_traces_validated");

// console.log: phase0.orchestrator.step11.aggregate_with_provenance_guard
console.log(JSON.stringify({ event: "phase0.orchestrator.step11.aggregate_with_provenance_guard" }));
run("python", ["scripts/aggregate_phase0.py", "--run-id", runId]);
completedSteps.push("provenance_guarded_aggregation");

// console.log: phase0.orchestrator.step12.phase0_tests
console.log(JSON.stringify({ event: "phase0.orchestrator.step12.phase0_tests" }));
run("python", ["-m", "pytest", "-q", "tests/phase0", "tests/metamorphic", "tests/leakage", "tests/statistical"]);
completedSteps.push("phase0_tests");

// console.log: phase0.orchestrator.step13.full_regression
console.log(JSON.stringify({ event: "phase0.orchestrator.step13.full_regression" }));
run("python", ["-m", "pytest", "-q"]);
completedSteps.push("full_regression_tests");

// console.log: phase0.orchestrator.step14.final_inherited_smoke
console.log(JSON.stringify({ event: "phase0.orchestrator.step14.final_inherited_smoke" }));
run("python", ["scripts/run_experiment.py", "--config", "configs/experiments/synthetic_smoke.yaml", "--output", `results/raw/${runId}/regression/synthetic_smoke.jsonl`]);
run("python", ["scripts/validate_traces.py", "--input", `results/raw/${runId}/regression/synthetic_smoke.jsonl`]);
completedSteps.push("inherited_smoke_after");

// console.log: phase0.orchestrator.step15.write_orchestration_evidence
console.log(JSON.stringify({ event: "phase0.orchestrator.step15.write_orchestration_evidence" }));
const evidenceDirectory = resolve(repoRoot, "results", "reports", runId);
mkdirSync(evidenceDirectory, { recursive: true });
writeFileSync(resolve(evidenceDirectory, "orchestration_evidence.json"), `${JSON.stringify({ schema_version: "1.0.0", run_id: runId, completed_steps: completedSteps }, null, 2)}\n`, "utf8");

// console.log: phase0.orchestrator.step16.audit
console.log(JSON.stringify({ event: "phase0.orchestrator.step16.audit" }));
run("python", ["scripts/audit_phase0.py", "--run-id", runId]);

// console.log: phase0.orchestrator.step17.complete
console.log(JSON.stringify({ event: "phase0.orchestrator.step17.complete", run_id: runId }));
