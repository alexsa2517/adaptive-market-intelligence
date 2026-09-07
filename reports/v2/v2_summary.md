# V2 Automated Variable Discovery

Research-only. V2 results do not modify the locked V1.12 model.

Assets tested: AAPL, NVDA, MSFT, AMZN, TSLA, XOM, JPM, GLD, SPY, QQQ
Candidate lags: 0, 1, 2, 3, 5, 10, 20, 60

## Interpretation
- KEEP: statistically screened and positive OOS accuracy delta across at least half of walk-forward folds.
- INVESTIGATE: statistically significant but not yet strong enough for promotion.
- REMOVE: fails the statistical/OOS gate.
- This is not causal proof. Final promotion requires independent holdout and cost/robustness testing.

## KEEP summary
No variables passed the current gate.

## INVESTIGATE summary
None.
