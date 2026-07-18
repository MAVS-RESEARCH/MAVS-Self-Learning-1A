import { spawnSync } from "node:child_process";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
function run(args) { const result = spawnSync("python", args, { cwd: root, encoding: "utf8", stdio: "inherit" }); if (result.status !== 0) throw new Error(`python ${args.join(" ")} failed with ${result.status}`); }

// console.log: phase9.track_a.step01.execute
console.log(JSON.stringify({ event: "phase9.track_a.step01.execute" }));
run(["scripts/run_phase9_track.py", "--track", "paired_original_bank"]);
// console.log: phase9.track_a.step02.firewall
console.log(JSON.stringify({ event: "phase9.track_a.step02.firewall" }));
run(["scripts/validate_phase9_firewall.py", "--track", "paired_original_bank"]);
// console.log: phase9.track_a.step03.state
console.log(JSON.stringify({ event: "phase9.track_a.step03.state" }));
run(["scripts/validate_phase9_state.py", "--track", "paired_original_bank"]);
// console.log: phase9.track_a.step04.complete
console.log(JSON.stringify({ event: "phase9.track_a.step04.complete" }));

