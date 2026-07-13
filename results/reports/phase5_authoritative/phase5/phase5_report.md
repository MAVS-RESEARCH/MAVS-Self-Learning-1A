# Phase 5 deep ablation, transfer, and anti-overfit report

Verdict: **NOT_SUPPORTED** under the pre-registered fail-closed gate policy.

## Executed scope

- 45,000 canonical opportunities: 15,000 in each of three disjoint generations.
- 50 authoritative ablations, 16 resolution-IV runs, and 5 four-cell targeted interactions under cumulative and fresh conditions.
- 10,740,000 complete primitive trace rows. Replays did not inflate the canonical budget.
- No model training and no post-holdout retuning.

## Reference results

| generation | objective | uar | frr | diagnostic_reuse_rate | novel_diagnostic_yield | scope_leakage_rate | update_stability |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.6991592002997951 | 0.005423512521933323 | 0.0059557897148093 | nan | 0.06798096532970768 | 0.0288 | 0.9967778544070415 |
| 2 | 0.6701102386941797 | 0.009971509971509971 | 0.009329647546648237 | 0.6345798865112463 | 0.03761869978086194 | 0.055466666666666664 | 0.9962411585709305 |
| 3 | 0.6459102120028652 | 0.0051468362095065095 | 0.00881582082439838 | 0.47289719626168225 | 0.03141614306428226 | 0.0892 | 0.9959017618961857 |

## Required evidence

Causal component rows: 150. Transfer-estimand rows: 2700. Factorial effect rows: 126. Targeted interaction rows: 30. Retention-bank rows: 1200.

All nonpositive effects and gate failures are published in `negative_results.csv`; undefined diagnosis acceleration is explicitly represented with a reason rather than imputed.
