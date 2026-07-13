from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from mavs10d.core.config import ExperimentConfig, load_experiment_config
from mavs10d.core.hashing import git_commit_hash, hidden_label_hash
from mavs10d.core.registry import ComponentRegistry, build_default_registry
from mavs10d.core.seeds import set_deterministic_seed
from mavs10d.core.trace_logging import JsonlTraceWriter, console_log, utc_now_iso
from mavs10d.core.types import EpisodeTrace, trace_supports_mavs_fields


@dataclass(frozen=True)
class ExperimentRunResult:
    output_path: Path
    records_written: int
    config_hash: str
    git_commit: str | None
    run_id: str


class ExperimentRunner:
    def __init__(
        self,
        registry: ComponentRegistry | None = None,
        repo_root: Path | None = None,
    ) -> None:
        self.registry = registry or build_default_registry()
        self.repo_root = repo_root or Path.cwd()

    def run_config_path(self, config_path: str | Path) -> ExperimentRunResult:
        # console.log: phase1.runner.step01.load_config
        console_log("phase1.runner.step01.load_config", config=str(config_path))
        config = load_experiment_config(config_path)
        return self.run(config)

    def run(self, config: ExperimentConfig) -> ExperimentRunResult:
        config_hash = config.config_hash or "missing-config-hash"
        commit = git_commit_hash(self.repo_root)
        output_path = config.outputs.raw_traces
        records_written = 0
        # console.log: phase1.runner.step02.resolve_environment
        console_log(
            "phase1.runner.step02.resolve_environment",
            environment_id=config.environment.id,
            environment_type=config.environment.type,
        )
        env = self.registry.create_environment(config.environment)
        # console.log: phase1.runner.step02.resolve_methods
        console_log(
            "phase1.runner.step02.resolve_methods",
            method_ids=[method.id for method in config.methods],
            method_types=[method.type for method in config.methods],
        )
        methods = [self.registry.create_method(method_config) for method_config in config.methods]
        with JsonlTraceWriter(output_path) as writer:
            for seed in config.seeds:
                set_deterministic_seed(seed)
                for method in methods:
                    # console.log: phase1.runner.step03.reset_episode
                    console_log(
                        "phase1.runner.step03.reset_episode",
                        seed=seed,
                        method_id=method.method_id,
                    )
                    method.reset(seed)
                    obs = env.reset(seed)
                    done = False
                    while not done:
                        # console.log: phase1.runner.step04.propose_candidate
                        console_log(
                            "phase1.runner.step04.propose_candidate",
                            episode_id=obs.episode_id,
                            step=obs.t,
                            method_id=method.method_id,
                        )
                        candidate = env.propose_candidate(obs)
                        # console.log: phase1.runner.step05.method_decide
                        console_log(
                            "phase1.runner.step05.method_decide",
                            episode_id=obs.episode_id,
                            step=obs.t,
                            method_id=method.method_id,
                        )
                        decision = method.decide(obs, candidate)
                        # console.log: phase1.runner.step06.environment_step
                        console_log(
                            "phase1.runner.step06.environment_step",
                            episode_id=obs.episode_id,
                            step=obs.t,
                            decision=decision.decision,
                        )
                        labels_before_step = env.hidden_labels()
                        step_result = env.step(decision)
                        trace_complete = trace_supports_mavs_fields(decision.trace)
                        trace = EpisodeTrace(
                            run_id=config.run_id,
                            config_hash=config_hash,
                            git_commit=commit,
                            environment_id=env.environment_id,
                            method_id=method.method_id,
                            seed=seed,
                            episode_id=obs.episode_id,
                            step_id=obs.t,
                            observation=obs,
                            candidate=candidate,
                            decision=decision,
                            step_result=step_result,
                            hidden_label_hash=hidden_label_hash(labels_before_step),
                            trace_complete=trace_complete,
                            created_at_utc=utc_now_iso(),
                            metadata={
                                **config.metadata,
                                "config_source": str(config.source_path)
                                if config.source_path
                                else None,
                            },
                        )
                        # console.log: phase1.runner.step07.write_trace
                        console_log(
                            "phase1.runner.step07.write_trace",
                            episode_id=obs.episode_id,
                            step=obs.t,
                            trace_complete=trace_complete,
                            output=str(output_path),
                        )
                        writer.write(trace)
                        records_written += 1
                        # console.log: phase1.runner.step08.method_update
                        console_log(
                            "phase1.runner.step08.method_update",
                            episode_id=obs.episode_id,
                            step=obs.t,
                            method_id=method.method_id,
                        )
                        method.update(obs, candidate, decision, step_result)
                        obs = step_result.next_observation
                        done = step_result.done
        return ExperimentRunResult(
            output_path=output_path,
            records_written=records_written,
            config_hash=config_hash,
            git_commit=commit,
            run_id=config.run_id,
        )

