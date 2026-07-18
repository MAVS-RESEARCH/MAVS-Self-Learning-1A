import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const phaseRoot = resolve(root, "results", "perception_closure_v04", "phase9");
const completed = [];
function run(command, args) { const result = spawnSync(command, args, { cwd: root, encoding: "utf8", stdio: "inherit" }); if (result.error) throw result.error; if (result.status !== 0) throw new Error(`${command} ${args.join(" ")} failed with ${result.status}`); }
function capture(command, args) { const result = spawnSync(command, args, { cwd: root, encoding: "utf8" }); if (result.error) throw result.error; if (result.status !== 0) throw new Error(`${command} ${args.join(" ")} failed with ${result.status}`); return result.stdout.trim(); }

// console.log: phase9.orchestrator.step01.start
console.log(JSON.stringify({ event: "phase9.orchestrator.step01.start" }));
// console.log: phase9.orchestrator.step02.clean
console.log(JSON.stringify({ event: "phase9.orchestrator.step02.clean" }));
run("python", ["scripts/clean_phase9_results.py", "--all-phase9"]); completed.push("clean");
// console.log: phase9.orchestrator.step03.source_cleanliness
console.log(JSON.stringify({ event: "phase9.orchestrator.step03.source_cleanliness" }));
const dirty = capture("git", ["status", "--porcelain"]); if (dirty) throw new Error(`Authoritative Phase 9 execution requires a clean source checkpoint: ${dirty}`); const sourceCommit = capture("git", ["rev-parse", "HEAD"]); completed.push("source_cleanliness");
// console.log: phase9.orchestrator.step04.inherited_tests
console.log(JSON.stringify({ event: "phase9.orchestrator.step04.inherited_tests" }));
run("python", ["-m", "pytest", "-q", "tests/unit", "tests/integration", "tests/phase0", "tests/phase1", "tests/phase2", "tests/phase3", "tests/phase4", "tests/phase5", "tests/phase6", "tests/phase7", "tests/phase8"]); completed.push("inherited_tests");
// console.log: phase9.orchestrator.step05.phase9_tests_before
console.log(JSON.stringify({ event: "phase9.orchestrator.step05.phase9_tests_before" }));
run("python", ["-m", "pytest", "-q", "tests/phase9"]); completed.push("phase9_tests_before");
// console.log: phase9.orchestrator.step06.compile_and_seal_banks
console.log(JSON.stringify({ event: "phase9.orchestrator.step06.compile_and_seal_banks" }));
run("python", ["scripts/compile_phase9_banks.py", "--source-commit", sourceCommit]); completed.push("banks_sealed");
// console.log: phase9.orchestrator.step07.track_a
console.log(JSON.stringify({ event: "phase9.orchestrator.step07.track_a" }));
run("node", ["scripts/run_phase9_paired.mjs"]); completed.push("track_a");
// console.log: phase9.orchestrator.step08.track_b
console.log(JSON.stringify({ event: "phase9.orchestrator.step08.track_b" }));
run("node", ["scripts/run_phase9_blind.mjs"]); completed.push("track_b");
// console.log: phase9.orchestrator.step09.integrity
console.log(JSON.stringify({ event: "phase9.orchestrator.step09.integrity" }));
run("python", ["scripts/validate_phase9_integrity.py"]); completed.push("integrity");
// console.log: phase9.orchestrator.step10.replay
console.log(JSON.stringify({ event: "phase9.orchestrator.step10.replay" }));
run("python", ["scripts/replay_phase9.py"]); completed.push("replay");
// console.log: phase9.orchestrator.step11.post_g3_challenges
console.log(JSON.stringify({ event: "phase9.orchestrator.step11.post_g3_challenges" }));
run("python", ["scripts/validate_phase9_post_g3.py"]); completed.push("post_g3_challenges");
// console.log: phase9.orchestrator.step12.aggregate
console.log(JSON.stringify({ event: "phase9.orchestrator.step12.aggregate" }));
run("python", ["scripts/aggregate_phase9.py"]); completed.push("aggregate");
// console.log: phase9.orchestrator.step13.phase9_tests_after
console.log(JSON.stringify({ event: "phase9.orchestrator.step13.phase9_tests_after" }));
run("python", ["-m", "pytest", "-q", "tests/phase9"]); completed.push("phase9_tests_after");
// console.log: phase9.orchestrator.step14.full_regression
console.log(JSON.stringify({ event: "phase9.orchestrator.step14.full_regression" }));
run("python", ["-m", "pytest", "-q"]); completed.push("full_regression");
// console.log: phase9.orchestrator.step15.orchestration_evidence
console.log(JSON.stringify({ event: "phase9.orchestrator.step15.orchestration_evidence" }));
for (const track of ["paired_original_bank", "blind_bank"]) { mkdirSync(resolve(phaseRoot, track, "reports"), { recursive: true }); writeFileSync(resolve(phaseRoot, track, "reports", "orchestration_evidence.json"), `${JSON.stringify({ schema_version: "1.0.0", track_id: track, source_commit: sourceCommit, completed_steps: completed }, null, 2)}\n`, "utf8"); } completed.push("orchestration_evidence");
// console.log: phase9.orchestrator.step16.signed_manifests
console.log(JSON.stringify({ event: "phase9.orchestrator.step16.signed_manifests" }));
run("python", ["scripts/finalize_phase9_manifest.py"]); completed.push("signed_manifests");
// console.log: phase9.orchestrator.step17.independent_audit
console.log(JSON.stringify({ event: "phase9.orchestrator.step17.independent_audit" }));
run("python", ["scripts/audit_phase9.py"]); completed.push("independent_audit");
// console.log: phase9.orchestrator.step18.seal
console.log(JSON.stringify({ event: "phase9.orchestrator.step18.seal" }));
const auditBytes = readFileSync(resolve(phaseRoot, "phase9_audit.json")); const audit = JSON.parse(auditBytes.toString("utf8")); if (audit.status !== "PASS" || audit.finding_count !== 0) throw new Error("Cannot seal failing Phase 9 evidence."); const auditSha = createHash("sha256").update(auditBytes).digest("hex").toUpperCase(); writeFileSync(resolve(phaseRoot, "SEALED"), `schema_version: 1.0.0\nsource_commit: ${sourceCommit}\naudit_status: PASS\naudit_findings: 0\naudit_sha256: ${auditSha}\nsealed_date: 2026-07-18\nphase10_executed: false\n`, "utf8"); completed.push("sealed");
// console.log: phase9.orchestrator.step19.complete
console.log(JSON.stringify({ event: "phase9.orchestrator.step19.complete", source_commit: sourceCommit, audit_sha256: auditSha }));
