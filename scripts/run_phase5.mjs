import { spawnSync } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

const repoRoot = resolve(import.meta.dirname, "..");
const index = process.argv.indexOf("--run-id");
if (index < 0 || !process.argv[index + 1]) throw new Error("--run-id is required");
const runId = process.argv[index + 1];
const completedSteps = [];

function run(command, args) {
  const result = spawnSync(command, args, { cwd: repoRoot, encoding: "utf8", stdio: "inherit" });
  if (result.error) throw result.error;
  if (result.status !== 0) throw new Error(`${command} ${args.join(" ")} failed with status ${result.status}`);
}

// console.log: phase5.orchestrator.step01.start
console.log(JSON.stringify({ event: "phase5.orchestrator.step01.start", run_id: runId }));

// console.log: phase5.orchestrator.step02.clean_named_run
console.log(JSON.stringify({ event: "phase5.orchestrator.step02.clean_named_run" }));
run("python", ["scripts/clean_results.py", "--run-id", runId]);
completedSteps.push("clean_named_run");

// console.log: phase5.orchestrator.step03.inherited_tests_before
console.log(JSON.stringify({ event: "phase5.orchestrator.step03.inherited_tests_before" }));
run("python", ["-m", "pytest", "-q", "tests/unit", "tests/integration", "tests/phase0", "tests/phase1", "tests/phase2", "tests/phase3", "tests/phase4"]);
completedSteps.push("inherited_tests_before");

// console.log: phase5.orchestrator.step04.phase5_tests_before
console.log(JSON.stringify({ event: "phase5.orchestrator.step04.phase5_tests_before" }));
run("python", ["-m", "pytest", "-q", "tests/phase5"]);
completedSteps.push("phase5_tests_before");

// console.log: phase5.orchestrator.step05.compile_banks
console.log(JSON.stringify({ event: "phase5.orchestrator.step05.compile_banks" }));
run("python", ["scripts/compile_phase5_ledgers.py", "--run-id", runId]);
completedSteps.push("banks_compiled");

// console.log: phase5.orchestrator.step06.validate_separation
console.log(JSON.stringify({ event: "phase5.orchestrator.step06.validate_separation" }));
run("python", ["scripts/validate_phase5_separation.py", "--run-id", runId]);
completedSteps.push("separation_validated");

// console.log: phase5.orchestrator.step07.execute_tournament
console.log(JSON.stringify({ event: "phase5.orchestrator.step07.execute_tournament" }));
run("python", ["scripts/run_phase5_tournament.py", "--run-id", runId]);
completedSteps.push("tournament_executed");

// console.log: phase5.orchestrator.step08.validate_traces
console.log(JSON.stringify({ event: "phase5.orchestrator.step08.validate_traces" }));
run("python", ["scripts/validate_phase5_traces.py", "--run-id", runId]);
completedSteps.push("traces_validated");

// console.log: phase5.orchestrator.step09.aggregate
console.log(JSON.stringify({ event: "phase5.orchestrator.step09.aggregate" }));
run("python", ["scripts/aggregate_phase5.py", "--run-id", runId]);
completedSteps.push("metrics_aggregated");

// console.log: phase5.orchestrator.step10.phase5_tests_after
console.log(JSON.stringify({ event: "phase5.orchestrator.step10.phase5_tests_after" }));
run("python", ["-m", "pytest", "-q", "tests/phase5"]);
completedSteps.push("phase5_tests_after");

// console.log: phase5.orchestrator.step11.full_regression
console.log(JSON.stringify({ event: "phase5.orchestrator.step11.full_regression" }));
run("python", ["-m", "pytest", "-q"]);
completedSteps.push("full_regression");

// console.log: phase5.orchestrator.step12.final_inherited_smoke
console.log(JSON.stringify({ event: "phase5.orchestrator.step12.final_inherited_smoke" }));
run("python", ["scripts/run_experiment.py", "--config", "configs/experiments/synthetic_smoke.yaml", "--output", `results/raw/${runId}/regression/synthetic_smoke.jsonl`]);
run("python", ["scripts/validate_traces.py", "--input", `results/raw/${runId}/regression/synthetic_smoke.jsonl`]);
completedSteps.push("inherited_smoke_after");

// console.log: phase5.orchestrator.step13.write_evidence
console.log(JSON.stringify({ event: "phase5.orchestrator.step13.write_evidence" }));
const evidenceDirectory = resolve(repoRoot, "results", "reports", runId, "phase5");
mkdirSync(evidenceDirectory, { recursive: true });
writeFileSync(resolve(evidenceDirectory, "orchestration_evidence.json"), `${JSON.stringify({ schema_version: "1.0.0", run_id: runId, completed_steps: completedSteps }, null, 2)}\n`, "utf8");

// console.log: phase5.orchestrator.step14.audit
console.log(JSON.stringify({ event: "phase5.orchestrator.step14.audit" }));
run("python", ["scripts/audit_phase5.py", "--run-id", runId]);
completedSteps.push("independent_audit");

// console.log: phase5.orchestrator.step15.complete
console.log(JSON.stringify({ event: "phase5.orchestrator.step15.complete", run_id: runId }));
