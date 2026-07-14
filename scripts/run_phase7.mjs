import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

const repoRoot = resolve(import.meta.dirname, "..");
const index = process.argv.indexOf("--run-id");
if (index < 0 || !process.argv[index + 1]) throw new Error("--run-id is required");
const runId = process.argv[index + 1];
const runRoot = resolve(repoRoot, "results", "perception_closure_v04", "phase7", runId);
const completedSteps = [];

function run(command, args) {
  const result = spawnSync(command, args, { cwd: repoRoot, encoding: "utf8", stdio: "inherit" });
  if (result.error) throw result.error;
  if (result.status !== 0) throw new Error(`${command} ${args.join(" ")} failed with status ${result.status}`);
}

function capture(command, args) {
  const result = spawnSync(command, args, { cwd: repoRoot, encoding: "utf8" });
  if (result.error) throw result.error;
  if (result.status !== 0) throw new Error(`${command} ${args.join(" ")} failed with status ${result.status}`);
  return result.stdout.trim();
}

// console.log: phase7.orchestrator.step01.start
console.log(JSON.stringify({ event: "phase7.orchestrator.step01.start", run_id: runId }));

// console.log: phase7.orchestrator.step02.clean_named_run
console.log(JSON.stringify({ event: "phase7.orchestrator.step02.clean_named_run" }));
run("python", ["scripts/clean_phase7_results.py", "--run-id", runId]);
completedSteps.push("clean_named_run");

// console.log: phase7.orchestrator.step03.source_cleanliness
console.log(JSON.stringify({ event: "phase7.orchestrator.step03.source_cleanliness" }));
const dirty = capture("git", ["status", "--porcelain"]);
if (dirty) throw new Error(`Authoritative Phase 7 execution requires a clean source checkpoint: ${dirty}`);
const sourceCommit = capture("git", ["rev-parse", "HEAD"]);
completedSteps.push("source_cleanliness");

// console.log: phase7.orchestrator.step04.inherited_tests_before
console.log(JSON.stringify({ event: "phase7.orchestrator.step04.inherited_tests_before" }));
run("python", ["-m", "pytest", "-q", "tests/unit", "tests/integration", "tests/phase0", "tests/phase1", "tests/phase2", "tests/phase3", "tests/phase4", "tests/phase5", "tests/phase6"]);
completedSteps.push("inherited_tests_before");

// console.log: phase7.orchestrator.step05.phase7_tests_before
console.log(JSON.stringify({ event: "phase7.orchestrator.step05.phase7_tests_before" }));
run("python", ["-m", "pytest", "-q", "tests/phase7"]);
completedSteps.push("phase7_tests_before");

// console.log: phase7.orchestrator.step06.compile_microbenchmarks
console.log(JSON.stringify({ event: "phase7.orchestrator.step06.compile_microbenchmarks" }));
run("python", ["scripts/compile_phase7_microbenchmarks.py", "--run-id", runId]);
completedSteps.push("microbenchmarks_compiled");

// console.log: phase7.orchestrator.step07.run_runtime
console.log(JSON.stringify({ event: "phase7.orchestrator.step07.run_runtime" }));
run("python", ["scripts/run_phase7_runtime.py", "--run-id", runId]);
completedSteps.push("runtime_complete");

// console.log: phase7.orchestrator.step08.validate_traces
console.log(JSON.stringify({ event: "phase7.orchestrator.step08.validate_traces" }));
run("python", ["scripts/validate_phase7_traces.py", "--run-id", runId]);
completedSteps.push("trace_validation_complete");

// console.log: phase7.orchestrator.step09.replay
console.log(JSON.stringify({ event: "phase7.orchestrator.step09.replay" }));
run("python", ["scripts/replay_phase7.py", "--run-id", runId]);
completedSteps.push("deterministic_replay_complete");

// console.log: phase7.orchestrator.step10.phase7_tests_after
console.log(JSON.stringify({ event: "phase7.orchestrator.step10.phase7_tests_after" }));
run("python", ["-m", "pytest", "-q", "tests/phase7"]);
completedSteps.push("phase7_tests_after");

// console.log: phase7.orchestrator.step11.full_regression
console.log(JSON.stringify({ event: "phase7.orchestrator.step11.full_regression" }));
run("python", ["-m", "pytest", "-q"]);
completedSteps.push("full_regression");

// console.log: phase7.orchestrator.step12.write_orchestration_evidence
console.log(JSON.stringify({ event: "phase7.orchestrator.step12.write_orchestration_evidence" }));
mkdirSync(resolve(runRoot, "reports"), { recursive: true });
writeFileSync(resolve(runRoot, "reports", "orchestration_evidence.json"), `${JSON.stringify({ schema_version: "1.0.0", run_id: runId, source_commit: sourceCommit, completed_steps: completedSteps }, null, 2)}\n`, "utf8");
completedSteps.push("orchestration_evidence_written");

// console.log: phase7.orchestrator.step13.independent_audit
console.log(JSON.stringify({ event: "phase7.orchestrator.step13.independent_audit" }));
run("python", ["scripts/audit_phase7_closure.py", "--run-id", runId]);
completedSteps.push("independent_audit");

// console.log: phase7.orchestrator.step14.seal
console.log(JSON.stringify({ event: "phase7.orchestrator.step14.seal" }));
const auditBytes = readFileSync(resolve(runRoot, "reports", "phase7_audit.json"));
const auditSha256 = createHash("sha256").update(auditBytes).digest("hex").toUpperCase();
const audit = JSON.parse(auditBytes.toString("utf8"));
if (audit.status !== "PASS" || audit.finding_count !== 0) throw new Error("Cannot seal a failing Phase 7 audit.");
writeFileSync(resolve(runRoot, "SEALED"), `schema_version: 1.0.0\nrun_id: ${runId}\nsource_commit: ${sourceCommit}\naudit_status: PASS\naudit_findings: 0\naudit_sha256: ${auditSha256}\nsealed_date: 2026-07-14\nphase8_executed: false\n`, "utf8");
completedSteps.push("sealed");

// console.log: phase7.orchestrator.step15.complete
console.log(JSON.stringify({ event: "phase7.orchestrator.step15.complete", run_id: runId, source_commit: sourceCommit }));
