"""Strictly development-only training for the Phase 1 CTTA source predictor."""

from __future__ import annotations

import json
import warnings
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.neural_network import MLPClassifier
from sklearn.exceptions import ConvergenceWarning

from mavs10d.core.hashing import file_sha256, stable_hash
from mavs10d.envs.phase1_gauntlet import Phase1WorldCompiler


@dataclass(frozen=True)
class TrainingTrial:
    seed: int
    learning_rate: float
    epochs: int
    validation_uar: float
    validation_brier: float


def train_phase1_proxy(output_directory: Path) -> dict[str, Any]:
    compiler = Phase1WorldCompiler()
    train_bank = compiler.compile_development("train", 1000, worlds_per_domain=5)
    validation_bank = compiler.compile_development("validation", 10000, worlds_per_domain=5)
    x_train, y_train = _matrix(train_bank)
    x_validation, y_validation = _matrix(validation_bank)
    mean = x_train.mean(axis=0)
    scale = x_train.std(axis=0)
    scale[scale < 1e-9] = 1.0
    x_train = (x_train - mean) / scale
    x_validation = (x_validation - mean) / scale
    trials: list[TrainingTrial] = []
    candidates: list[tuple[tuple[float, float], MLPClassifier, TrainingTrial]] = []
    for seed in (11, 23, 37, 53, 71):
        for learning_rate in (0.0001, 0.0003, 0.001):
            model = MLPClassifier(
                hidden_layer_sizes=(64, 64),
                activation="relu",
                solver="adam",
                batch_size=256,
                learning_rate_init=learning_rate,
                max_iter=1,
                warm_start=True,
                shuffle=True,
                random_state=seed,
            )
            best: tuple[float, float] | None = None
            best_weights: tuple[list[np.ndarray], list[np.ndarray]] | None = None
            patience = 0
            epochs = 0
            for epoch in range(1, 101):
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", category=ConvergenceWarning)
                    model.fit(x_train, y_train)
                probability = model.predict_proba(x_validation)[:, 1]
                uar = float(((probability < 0.5) & (y_validation == 1)).sum() / max(1, (y_validation == 1).sum()))
                brier = float(np.mean((probability - y_validation) ** 2))
                objective = (uar, brier)
                epochs = epoch
                if best is None or objective < best:
                    best = objective
                    best_weights = ([array.copy() for array in model.coefs_], [array.copy() for array in model.intercepts_])
                    patience = 0
                else:
                    patience += 1
                if patience >= 8:
                    break
            assert best is not None and best_weights is not None
            model.coefs_, model.intercepts_ = best_weights
            trial = TrainingTrial(seed, learning_rate, epochs, best[0], best[1])
            trials.append(trial)
            candidates.append((best, model, trial))
    _, selected, selected_trial = min(candidates, key=lambda item: (item[0], item[2].seed, item[2].learning_rate))
    output_directory.mkdir(parents=True, exist_ok=True)
    checkpoint_path = output_directory / "phase1_ctta_source.npz"
    payload: dict[str, np.ndarray] = {"feature_mean": mean, "feature_scale": scale}
    for index, value in enumerate(selected.coefs_):
        payload[f"weight_{index}"] = value
    for index, value in enumerate(selected.intercepts_):
        payload[f"bias_{index}"] = value
    np.savez_compressed(checkpoint_path, **payload)
    manifest: dict[str, Any] = {
        "schema_version": "1.0.0",
        "component": "phase1_ctta_source_predictor",
        "architecture": [8, 64, 64, 1],
        "activation": "relu_relu_sigmoid",
        "optimizer": "adam",
        "batch_size": 256,
        "maximum_epochs": 100,
        "early_stopping_patience": 8,
        "training_domains": list(train_bank.manifest["domains"]),
        "blind_evaluation_domains": ["text_safety", "tool_use", "cyber_triage", "financial_approval_proxy", "multi_agent_operations"],
        "train_manifest": train_bank.manifest,
        "validation_manifest": validation_bank.manifest,
        "trials": [asdict(trial) for trial in trials],
        "selected_trial": asdict(selected_trial),
        "checkpoint_sha256": file_sha256(checkpoint_path),
        "feature_visibility": "visible_features_only",
        "final_manifest_access": False,
        "known_limitations": ["synthetic proxy", "fixed binary unsafe target", "not a governance safety guarantee"],
    }
    manifest["manifest_sha256"] = stable_hash(manifest)
    manifest_path = output_directory / "training_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return manifest


def predict_checkpoint(checkpoint_path: Path, features: np.ndarray) -> np.ndarray:
    checkpoint = np.load(checkpoint_path)
    activation = (features - checkpoint["feature_mean"]) / checkpoint["feature_scale"]
    activation = np.maximum(0.0, activation @ checkpoint["weight_0"] + checkpoint["bias_0"])
    activation = np.maximum(0.0, activation @ checkpoint["weight_1"] + checkpoint["bias_1"])
    logits = activation @ checkpoint["weight_2"] + checkpoint["bias_2"]
    return 1.0 / (1.0 + np.exp(-np.clip(logits.reshape(-1), -30.0, 30.0)))


def _matrix(bank) -> tuple[np.ndarray, np.ndarray]:
    x = np.vstack([row.feature_vector() for row in bank.visible])
    y = np.asarray([int(row.unsafe) for row in bank.hidden], dtype=np.int64)
    return x, y
