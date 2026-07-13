import { spawnSync } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

const repoRoot = resolve(import.meta.dirname, "..");
const runIdIndex = process.argv.indexOf("--run-id");
if (runIdIndex < 0 || !process.argv[runIdIndex + 1]) throw new Error("--run-id is required");
const runId = process.argv[runIdIndex + 1];
const completedSteps = [];

function run(command, args) {
  const result = spawnSync(command, args, { cwd: repoRoot, encoding: "utf8", stdio: "inherit" });
  if (result.error) throw result.error;
  if (result.status !== 0) throw new Error(`${command} ${args.join(" ")} failed with status ${result.status}`);
}

// console.log: phase1.orchestrator.step01.start
console.log(JSON.stringify({ event: "phase1.orchestrator.step01.start", run_id: runId }));

// console.log: phase1.orchestrator.step02.clean_phase1_run
console.log(JSON.stringify({ event: "phase1.orchestrator.step02.clean_phase1_run" }));
run("python", ["scripts/clean_results.py", "--run-id", runId]);
completedSteps.push("clean_phase1_run");

// console.log: phase1.orchestrator.step03.inherited_tests_before
console.log(JSON.stringify({ event: "phase1.orchestrator.step03.inherited_tests_before" }));
run("python", ["-m", "pytest", "-q", "tests/unit", "tests/integration", "tests/phase0"]);
completedSteps.push("inherited_tests_before");

// console.log: phase1.orchestrator.step04.verify_ctta_checkpoint
console.log(JSON.stringify({ event: "phase1.orchestrator.step04.verify_ctta_checkpoint" }));
run("python", ["scripts/validate_phase1_model.py"]);
completedSteps.push("ctta_checkpoint_verified");

// console.log: phase1.orchestrator.step05.compile_ledgers
console.log(JSON.stringify({ event: "phase1.orchestrator.step05.compile_ledgers" }));
run("python", ["scripts/compile_phase1_ledgers.py", "--run-id", runId]);
completedSteps.push("phase1_ledgers_compiled");

// console.log: phase1.orchestrator.step06.validate_separation
console.log(JSON.stringify({ event: "phase1.orchestrator.step06.validate_separation" }));
run("python", ["scripts/validate_phase1_separation.py", "--run-id", runId]);
completedSteps.push("separation_validated");

// console.log: phase1.orchestrator.step07.execute_stress
console.log(JSON.stringify({ event: "phase1.orchestrator.step07.execute_stress" }));
run("python", ["scripts/run_phase1_stress.py", "--run-id", runId]);
completedSteps.push("stress_executed");

// console.log: phase1.orchestrator.step08.validate_checkpoints
console.log(JSON.stringify({ event: "phase1.orchestrator.step08.validate_checkpoints" }));
run("python", ["scripts/validate_phase1_checkpoints.py", "--run-id", runId]);

// console.log: phase1.orchestrator.step09.validate_traces
console.log(JSON.stringify({ event: "phase1.orchestrator.step09.validate_traces" }));
run("python", ["scripts/validate_phase1_traces.py", "--run-id", runId]);
completedSteps.push("traces_validated");

// console.log: phase1.orchestrator.step10.aggregate_metrics
console.log(JSON.stringify({ event: "phase1.orchestrator.step10.aggregate_metrics" }));
run("python", ["scripts/aggregate_phase1.py", "--run-id", runId]);
completedSteps.push("metrics_aggregated");

// console.log: phase1.orchestrator.step11.phase1_tests
console.log(JSON.stringify({ event: "phase1.orchestrator.step11.phase1_tests" }));
run("python", ["-m", "pytest", "-q", "tests/phase1"]);
completedSteps.push("phase1_tests");

// console.log: phase1.orchestrator.step12.full_regression
console.log(JSON.stringify({ event: "phase1.orchestrator.step12.full_regression" }));
run("python", ["-m", "pytest", "-q"]);
completedSteps.push("full_regression");

// console.log: phase1.orchestrator.step13.final_inherited_smoke
console.log(JSON.stringify({ event: "phase1.orchestrator.step13.final_inherited_smoke" }));
run("python", ["scripts/run_experiment.py", "--config", "configs/experiments/synthetic_smoke.yaml", "--output", `results/raw/${runId}/regression/synthetic_smoke.jsonl`]);
run("python", ["scripts/validate_traces.py", "--input", `results/raw/${runId}/regression/synthetic_smoke.jsonl`]);
completedSteps.push("inherited_smoke_after");

// console.log: phase1.orchestrator.step14.write_evidence
console.log(JSON.stringify({ event: "phase1.orchestrator.step14.write_evidence" }));
const evidenceDirectory = resolve(repoRoot, "results", "reports", runId);
mkdirSync(evidenceDirectory, { recursive: true });
writeFileSync(resolve(evidenceDirectory, "orchestration_evidence.json"), `${JSON.stringify({ schema_version: "1.0.0", run_id: runId, completed_steps: completedSteps }, null, 2)}\n`, "utf8");

// console.log: phase1.orchestrator.step15.audit
console.log(JSON.stringify({ event: "phase1.orchestrator.step15.audit" }));
run("python", ["scripts/audit_phase1.py", "--run-id", runId]);

// console.log: phase1.orchestrator.step16.complete
console.log(JSON.stringify({ event: "phase1.orchestrator.step16.complete", run_id: runId }));
