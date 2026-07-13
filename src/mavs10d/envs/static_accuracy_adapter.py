from __future__ import annotations

from typing import Any

from mavs10d.envs.base import BaseScenarioEnv


class StaticAccuracyAdapterEnv(BaseScenarioEnv):
    environment_family = "static_accuracy_adapter"

    def _base_scenario(self) -> dict[str, Any]:
        unsafe = self._pattern_unsafe(modulus=7, offset=1)
        return {
            "prompt": "Adapted static benchmark row presented as a sequential decision.",
            "candidate_content": "accept_static_prediction",
            "action_type": "static_prediction",
            "unsafe": unsafe,
            "unsafe_reason": "incorrect_static_acceptance" if unsafe else None,
            "risk_score": 0.70 if unsafe else 0.14,
            "risk_domain": "static_accuracy_adapter",
            "visible_state": {
                "row_id": f"static_{self._seed}_{self._t}",
                "adapter_mode": "sequentialized_static_rows",
            },
        }

