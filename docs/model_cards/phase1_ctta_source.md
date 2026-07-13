# Phase 1 CTTA Source Predictor Model Card

## Purpose and claim boundary

This is a lightweight source-risk predictor used only by the Phase 1 CTTA entropy and confidence-filtered pseudo-label benchmark adaptations. It is not MAVS-SL, is not a safety certificate, and cannot bypass the governance decision interface.

## Architecture and training

- Input: eight visible synthetic world features; no hidden regime, label, future feedback, evaluation manifest, or final metric.
- Network: `8 -> 64 ReLU -> 64 ReLU -> 1 sigmoid`.
- Optimizer: Adam.
- Batch size: 256.
- Maximum epochs: 100 with external development-validation early stopping, patience 8.
- Grid: learning rate `{0.0001, 0.0003, 0.001}` across seeds `{11,23,37,53,71}`; 15 complete trials.
- Training bank: 1,500 opportunities, seeds 1000-1014, domains `synthetic_control`, `retrieval_qa`, and `medical_triage_proxy`.
- Validation bank: 1,500 opportunities, seeds 10000-10014, the same development-only domain class but disjoint worlds and identities.
- Training opportunity-ID digest: `c4ed99a5f521c906dccaf037d30d7747f6e0b566746f5f9221b6b7ace7b6f5c7`.
- Validation opportunity-ID digest: `7a0189997f1187a59f98a57eaefca011662b8aefa4b71e343580e9f7a883376a`.

## Selection result

- Selected seed: 53.
- Selected learning rate: 0.0001.
- Selected epoch: 9.
- Development-validation UAR at threshold 0.5: 0.45255474452554745.
- Development-validation Brier score: 0.2507645038782588.
- Checkpoint SHA-256: `48d35d9f49c306bcc17fbb490f864cad2bc8afaf07a3a30f930a25f91fc05319`.
- Training-manifest semantic hash: `ae75490058585c3bec49cd5a1a8b7736b5a39ed1dd49c275dbf5e2e142a8c018`.

## Entirely different blind evaluation

The checkpoint is frozen before Phase 1 evaluation ledgers are compiled. Blind evaluation uses only `text_safety`, `tool_use`, `cyber_triage`, `financial_approval_proxy`, and `multi_agent_operations`; generation seed ranges are 100000-199999, 300000-399999, and 500000-599999. Evaluation changes domain identities, priors, policy namespace, surface-template namespace, schedule namespace, and shift intensity. No evaluation failure may trigger retraining or model selection.

## Limitations

The validation UAR is high and the model is intentionally retained as a named weak source predictor so CTTA behavior is not silently improved using evaluation evidence. The predictor is synthetic, binary, and does not establish calibrated safety under shift. Final reporting must expose blind UAR, FRR, ECE, Brier score, catastrophic episodes, adaptation/recovery lag, regret, and tail behavior.
