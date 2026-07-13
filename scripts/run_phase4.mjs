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

// console.log: phase4.orchestrator.step01.start
console.log(JSON.stringify({ event: "phase4.orchestrator.step01.start", run_id: runId }));

// console.log: phase4.orchestrator.step02.clean_phase4_run
console.log(JSON.stringify({ event: "phase4.orchestrator.step02.clean_phase4_run" }));
run("python", ["scripts/clean_results.py", "--run-id", runId]);
completedSteps.push("clean_phase4_run");

// console.log: phase4.orchestrator.step03.inherited_tests_before
console.log(JSON.stringify({ event: "phase4.orchestrator.step03.inherited_tests_before" }));
run("python", ["-m", "pytest", "-q", "tests/unit", "tests/integration", "tests/phase0", "tests/phase1", "tests/phase2", "tests/phase3"]);
completedSteps.push("inherited_tests_before");

// console.log: phase4.orchestrator.step04.compile_ledgers
console.log(JSON.stringify({ event: "phase4.orchestrator.step04.compile_ledgers" }));
run("python", ["scripts/compile_phase4_ledgers.py", "--run-id", runId]);
completedSteps.push("phase4_ledgers_compiled");

// console.log: phase4.orchestrator.step05.validate_separation
console.log(JSON.stringify({ event: "phase4.orchestrator.step05.validate_separation" }));
run("python", ["scripts/validate_phase4_separation.py", "--run-id", runId]);
completedSteps.push("separation_validated");

// console.log: phase4.orchestrator.step06.execute_tournament
console.log(JSON.stringify({ event: "phase4.orchestrator.step06.execute_tournament" }));
run("python", ["scripts/run_phase4_tournament.py", "--run-id", runId]);
completedSteps.push("tournament_executed");

// console.log: phase4.orchestrator.step07.validate_traces
console.log(JSON.stringify({ event: "phase4.orchestrator.step07.validate_traces" }));
run("python", ["scripts/validate_phase4_traces.py", "--run-id", runId]);
completedSteps.push("traces_validated");

// console.log: phase4.orchestrator.step08.aggregate
console.log(JSON.stringify({ event: "phase4.orchestrator.step08.aggregate" }));
run("python", ["scripts/aggregate_phase4.py", "--run-id", runId]);
completedSteps.push("metrics_aggregated");

// console.log: phase4.orchestrator.step09.phase4_tests
console.log(JSON.stringify({ event: "phase4.orchestrator.step09.phase4_tests" }));
run("python", ["-m", "pytest", "-q", "tests/phase4"]);
completedSteps.push("phase4_tests");

// console.log: phase4.orchestrator.step10.full_regression
console.log(JSON.stringify({ event: "phase4.orchestrator.step10.full_regression" }));
run("python", ["-m", "pytest", "-q"]);
completedSteps.push("full_regression");

// console.log: phase4.orchestrator.step11.final_inherited_smoke
console.log(JSON.stringify({ event: "phase4.orchestrator.step11.final_inherited_smoke" }));
run("python", ["scripts/run_experiment.py", "--config", "configs/experiments/synthetic_smoke.yaml", "--output", `results/raw/${runId}/regression/synthetic_smoke.jsonl`]);
run("python", ["scripts/validate_traces.py", "--input", `results/raw/${runId}/regression/synthetic_smoke.jsonl`]);
completedSteps.push("inherited_smoke_after");

// console.log: phase4.orchestrator.step12.write_evidence
console.log(JSON.stringify({ event: "phase4.orchestrator.step12.write_evidence" }));
const evidenceDirectory = resolve(repoRoot, "results", "reports", runId);
mkdirSync(evidenceDirectory, { recursive: true });
writeFileSync(resolve(evidenceDirectory, "orchestration_evidence.json"), `${JSON.stringify({ schema_version: "1.0.0", run_id: runId, completed_steps: completedSteps }, null, 2)}\n`, "utf8");

// console.log: phase4.orchestrator.step13.audit
console.log(JSON.stringify({ event: "phase4.orchestrator.step13.audit" }));
run("python", ["scripts/audit_phase4.py", "--run-id", runId]);

// console.log: phase4.orchestrator.step14.complete
console.log(JSON.stringify({ event: "phase4.orchestrator.step14.complete", run_id: runId }));
