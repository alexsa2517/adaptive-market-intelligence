# V2.1 Macro Variable Discovery

Research-only. The locked V1.12 model is unchanged.
The previous failed cross-asset candidate pool is not reintroduced.

Assets tested: AAPL, NVDA, MSFT, AMZN, TSLA, XOM, JPM, GLD, SPY, QQQ
Candidate lags: 0, 1, 2, 3, 5, 10, 20

## Status rules
- KEEP: statistically screened and strong positive OOS evidence.
- INVESTIGATE: statistically screened and positive OOS evidence, but below the stronger gate.
- WEAK: statistically significant but insufficient OOS evidence.
- REMOVE: fails the statistical gate.
- Final promotion still requires cost testing, robustness, and an untouched holdout.

## Summary
KEEP=10
INVESTIGATE=3
WEAK=2
REMOVE=895

## Top candidates
- QQQ: macro_cpi_yoy lag 1 | status=INVESTIGATE | q=0.02895 | OOS Δ=0.4960% | positive=4/8
- QQQ: macro_cpi_yoy lag 2 | status=KEEP | q=0.02895 | OOS Δ=0.8929% | positive=6/8
- QQQ: macro_cpi_yoy lag 5 | status=KEEP | q=0.02895 | OOS Δ=0.5952% | positive=6/8
- QQQ: macro_cpi_yoy lag 3 | status=KEEP | q=0.02895 | OOS Δ=0.9921% | positive=5/8
- QQQ: macro_cpi_yoy lag 10 | status=KEEP | q=0.02895 | OOS Δ=1.0913% | positive=5/8
- QQQ: macro_cpi_yoy lag 20 | status=KEEP | q=0.02895 | OOS Δ=0.7937% | positive=5/8
- QQQ: macro_cpi_change_30d lag 20 | status=WEAK | q=0.04075 | OOS Δ=-0.0000% | positive=5/10
- QQQ: macro_cpi_yoy lag 0 | status=WEAK | q=0.02895 | OOS Δ=0.1984% | positive=3/8
- SPY: macro_cpi_yoy lag 1 | status=INVESTIGATE | q=0.02983 | OOS Δ=2.0833% | positive=4/8
- SPY: macro_cpi_yoy lag 20 | status=INVESTIGATE | q=0.02895 | OOS Δ=1.3889% | positive=4/8
- SPY: macro_cpi_yoy lag 5 | status=KEEP | q=0.02983 | OOS Δ=1.8849% | positive=6/8
- SPY: macro_cpi_yoy lag 10 | status=KEEP | q=0.02983 | OOS Δ=2.4802% | positive=6/8
- SPY: macro_cpi_yoy lag 0 | status=KEEP | q=0.02895 | OOS Δ=2.5794% | positive=5/8
- SPY: macro_cpi_yoy lag 2 | status=KEEP | q=0.02983 | OOS Δ=2.1825% | positive=5/8
- SPY: macro_cpi_yoy lag 3 | status=KEEP | q=0.02983 | OOS Δ=1.9841% | positive=5/8
