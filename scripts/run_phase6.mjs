import { spawnSync } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

const repoRoot = resolve(import.meta.dirname, "..");
const index = process.argv.indexOf("--run-id");
if (index < 0 || !process.argv[index + 1]) throw new Error("--run-id is required");
const runId = process.argv[index + 1];
const runRoot = resolve(repoRoot, "results", "perception_closure_v04", "phase6", runId);
const completedSteps = [];

function run(command, args) {
  const result = spawnSync(command, args, { cwd: repoRoot, encoding: "utf8", stdio: "inherit" });
  if (result.error) throw result.error;
  if (result.status !== 0) throw new Error(`${command} ${args.join(" ")} failed with status ${result.status}`);
}

// console.log: phase6.orchestrator.step01.start
console.log(JSON.stringify({ event: "phase6.orchestrator.step01.start", run_id: runId }));

// console.log: phase6.orchestrator.step02.clean_named_run
console.log(JSON.stringify({ event: "phase6.orchestrator.step02.clean_named_run" }));
run("python", ["scripts/clean_phase6_results.py", "--run-id", runId]);
completedSteps.push("clean_named_run");

// console.log: phase6.orchestrator.step03.inherited_tests_before
console.log(JSON.stringify({ event: "phase6.orchestrator.step03.inherited_tests_before" }));
run("python", ["-m", "pytest", "-q", "tests/unit", "tests/integration", "tests/phase0", "tests/phase1", "tests/phase2", "tests/phase3", "tests/phase4", "tests/phase5"]);
completedSteps.push("inherited_tests_before");

// console.log: phase6.orchestrator.step04.phase6_tests_before
console.log(JSON.stringify({ event: "phase6.orchestrator.step04.phase6_tests_before" }));
run("python", ["-m", "pytest", "-q", "tests/phase6"]);
completedSteps.push("phase6_tests_before");

// console.log: phase6.orchestrator.step05.index_legacy
console.log(JSON.stringify({ event: "phase6.orchestrator.step05.index_legacy" }));
run("python", ["scripts/index_legacy_results.py"]);
completedSteps.push("legacy_indexed");

// console.log: phase6.orchestrator.step06.synthesize
console.log(JSON.stringify({ event: "phase6.orchestrator.step06.synthesize" }));
run("python", ["scripts/run_phase6_synthesis.py", "--run-id", runId]);
completedSteps.push("synthesis_complete");

// console.log: phase6.orchestrator.step07.validate_separation
console.log(JSON.stringify({ event: "phase6.orchestrator.step07.validate_separation" }));
run("python", ["scripts/validate_phase6_separation.py", "--run-id", runId]);
completedSteps.push("separation_validated");

// console.log: phase6.orchestrator.step08.certify
console.log(JSON.stringify({ event: "phase6.orchestrator.step08.certify" }));
run("python", ["scripts/certify_phase6_candidates.py", "--run-id", runId, "--seed", "630001"]);
completedSteps.push("blind_certification_complete");

// console.log: phase6.orchestrator.step09.replay
console.log(JSON.stringify({ event: "phase6.orchestrator.step09.replay" }));
run("python", ["scripts/replay_phase6_candidates.py", "--run-id", runId]);
completedSteps.push("candidate_replay_complete");

// console.log: phase6.orchestrator.step10.report
console.log(JSON.stringify({ event: "phase6.orchestrator.step10.report" }));
run("python", ["scripts/report_phase6.py", "--run-id", runId]);
completedSteps.push("integrity_reports_complete");

// console.log: phase6.orchestrator.step11.phase6_tests_after
console.log(JSON.stringify({ event: "phase6.orchestrator.step11.phase6_tests_after" }));
run("python", ["-m", "pytest", "-q", "tests/phase6"]);
completedSteps.push("phase6_tests_after");

// console.log: phase6.orchestrator.step12.full_regression
console.log(JSON.stringify({ event: "phase6.orchestrator.step12.full_regression" }));
run("python", ["-m", "pytest", "-q"]);
completedSteps.push("full_regression");

// console.log: phase6.orchestrator.step13.inherited_smoke
console.log(JSON.stringify({ event: "phase6.orchestrator.step13.inherited_smoke" }));
run("python", ["scripts/run_experiment.py", "--config", "configs/experiments/synthetic_smoke.yaml", "--output", resolve(runRoot, "regression", "synthetic_smoke.jsonl")]);
run("python", ["scripts/validate_traces.py", "--input", resolve(runRoot, "regression", "synthetic_smoke.jsonl")]);
completedSteps.push("inherited_smoke_after");

// console.log: phase6.orchestrator.step14.write_orchestration_evidence
console.log(JSON.stringify({ event: "phase6.orchestrator.step14.write_orchestration_evidence" }));
mkdirSync(resolve(runRoot, "reports"), { recursive: true });
writeFileSync(resolve(runRoot, "reports", "orchestration_evidence.json"), `${JSON.stringify({ schema_version: "1.0.0", run_id: runId, completed_steps: completedSteps }, null, 2)}\n`, "utf8");

// console.log: phase6.orchestrator.step15.independent_audit
console.log(JSON.stringify({ event: "phase6.orchestrator.step15.independent_audit" }));
run("python", ["scripts/audit_phase6_integrity.py", "--run-id", runId]);
completedSteps.push("independent_audit");

// console.log: phase6.orchestrator.step16.complete
console.log(JSON.stringify({ event: "phase6.orchestrator.step16.complete", run_id: runId }));
