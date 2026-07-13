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

// console.log: phase2.orchestrator.step01.start
console.log(JSON.stringify({ event: "phase2.orchestrator.step01.start", run_id: runId }));

// console.log: phase2.orchestrator.step02.clean_phase2_run
console.log(JSON.stringify({ event: "phase2.orchestrator.step02.clean_phase2_run" }));
run("python", ["scripts/clean_results.py", "--run-id", runId]);
completedSteps.push("clean_phase2_run");

// console.log: phase2.orchestrator.step03.inherited_tests_before
console.log(JSON.stringify({ event: "phase2.orchestrator.step03.inherited_tests_before" }));
run("python", ["-m", "pytest", "-q", "tests/unit", "tests/integration", "tests/phase0", "tests/phase1"]);
completedSteps.push("inherited_tests_before");

// console.log: phase2.orchestrator.step04.compile_ledgers
console.log(JSON.stringify({ event: "phase2.orchestrator.step04.compile_ledgers" }));
run("python", ["scripts/compile_phase2_ledgers.py", "--run-id", runId]);
completedSteps.push("phase2_ledgers_compiled");

// console.log: phase2.orchestrator.step05.validate_separation
console.log(JSON.stringify({ event: "phase2.orchestrator.step05.validate_separation" }));
run("python", ["scripts/validate_phase2_separation.py", "--run-id", runId]);
completedSteps.push("separation_validated");

// console.log: phase2.orchestrator.step06.execute_stress
console.log(JSON.stringify({ event: "phase2.orchestrator.step06.execute_stress" }));
run("python", ["scripts/run_phase2_stress.py", "--run-id", runId]);
completedSteps.push("stress_executed");

// console.log: phase2.orchestrator.step07.validate_traces_without_cards
console.log(JSON.stringify({ event: "phase2.orchestrator.step07.validate_traces_without_cards" }));
run("python", ["scripts/validate_phase2_traces.py", "--run-id", runId, "--without-cards"]);
completedSteps.push("traces_validated_without_cards");

// console.log: phase2.orchestrator.step08.create_failure_cards
console.log(JSON.stringify({ event: "phase2.orchestrator.step08.create_failure_cards" }));
run("python", ["scripts/make_phase2_failure_cards.py", "--run-id", runId]);
completedSteps.push("failure_cards_created");

// console.log: phase2.orchestrator.step09.validate_traces_and_cards
console.log(JSON.stringify({ event: "phase2.orchestrator.step09.validate_traces_and_cards" }));
run("python", ["scripts/validate_phase2_traces.py", "--run-id", runId]);
completedSteps.push("traces_and_cards_validated");

// console.log: phase2.orchestrator.step10.aggregate_metrics
console.log(JSON.stringify({ event: "phase2.orchestrator.step10.aggregate_metrics" }));
run("python", ["scripts/aggregate_phase2.py", "--run-id", runId]);
completedSteps.push("metrics_aggregated");

// console.log: phase2.orchestrator.step11.phase2_tests
console.log(JSON.stringify({ event: "phase2.orchestrator.step11.phase2_tests" }));
run("python", ["-m", "pytest", "-q", "tests/phase2"]);
completedSteps.push("phase2_tests");

// console.log: phase2.orchestrator.step12.full_regression
console.log(JSON.stringify({ event: "phase2.orchestrator.step12.full_regression" }));
run("python", ["-m", "pytest", "-q"]);
completedSteps.push("full_regression");

// console.log: phase2.orchestrator.step13.final_inherited_smoke
console.log(JSON.stringify({ event: "phase2.orchestrator.step13.final_inherited_smoke" }));
run("python", ["scripts/run_experiment.py", "--config", "configs/experiments/synthetic_smoke.yaml", "--output", `results/raw/${runId}/regression/synthetic_smoke.jsonl`]);
run("python", ["scripts/validate_traces.py", "--input", `results/raw/${runId}/regression/synthetic_smoke.jsonl`]);
completedSteps.push("inherited_smoke_after");

// console.log: phase2.orchestrator.step14.write_evidence
console.log(JSON.stringify({ event: "phase2.orchestrator.step14.write_evidence" }));
const evidenceDirectory = resolve(repoRoot, "results", "reports", runId);
mkdirSync(evidenceDirectory, { recursive: true });
writeFileSync(resolve(evidenceDirectory, "orchestration_evidence.json"), `${JSON.stringify({ schema_version: "1.0.0", run_id: runId, completed_steps: completedSteps }, null, 2)}\n`, "utf8");

// console.log: phase2.orchestrator.step15.audit
console.log(JSON.stringify({ event: "phase2.orchestrator.step15.audit" }));
run("python", ["scripts/audit_phase2.py", "--run-id", runId]);

// console.log: phase2.orchestrator.step16.complete
console.log(JSON.stringify({ event: "phase2.orchestrator.step16.complete", run_id: runId }));
