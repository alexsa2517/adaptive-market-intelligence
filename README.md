# Adaptive Market Intelligence

**PROVE BEFORE TRADE**

An evidence-first market intelligence and forecasting system. The project is designed to test whether a measurable predictive edge exists before any real-money trading is allowed.

## Current Research Status — V1.12 Forward Validation

The current research candidate is an XGBoost-based daily BTC direction model using Feature Set C and a locked Moderate market-regime filter. The final untouched holdout (2026-05-08 to 2026-09-04) produced +20.43% return, -1.97% max drawdown, Sharpe 3.09 and profit factor 5.61 under the base cost assumption. V1.11 robustness scored 6/7 and was classified **PROMISING — MORE VALIDATION REQUIRED**, not proven. The main weakness was a very small number of active holdout days and failed outlier robustness.

### V1.12 locked forward configuration

- Locked model: XGBoost configuration from V1.10.9.1
- Locked training window: 2021-07-23 to 2024-11-03 (1,200 rows)
- Feature Set C: returns, volatility, momentum, SMA/EMA gaps, RSI, volume, trend and range features
- Probability threshold: 0.60
- Moderate regime: baseline signal AND (Bull OR High Volatility)
- Bull regime: price > 50-day SMA by more than 5%
- Bear regime: price < 50-day SMA by more than 5%
- Locked volatility threshold: 0.026935
- Base transaction cost assumption: 0.10% fee + 0.05% slippage per position change
- **No retraining with forward observations**
- **No threshold or rule tuning from forward outcomes**

### Forward validation status

Forward observations began after the untouched holdout. The first two observations currently recorded are:

- 2026-09-05: `prob_up` 0.423468 → no signal
- 2026-09-07: `prob_up` 0.433182 → no signal

Both observations were Bull / High Volatility, but remained below the locked 0.60 probability threshold. They are recorded as forward evidence and must not be used to modify the model.

The forward monitor is implemented in `src/forward_validation.py`. The forward evidence remains separate from model training and is intended to accumulate future observations without look-ahead or parameter drift.

## Data integrity

The feature pipeline explicitly preserves an unknown final next-day target as `NaN` and removes that row instead of silently converting it to class `0`. This prevents an invalid final-label artifact from entering model evaluation.

## Research gates

```text
Research
  ↓
Temporal / Walk-Forward Validation
  ↓
Robustness + Cost Sensitivity
  ↓
Final Untouched Holdout
  ↓
Forward Validation / Paper Trading
  ↓
Sustained Evidence
  ↓
Future Live-Trading Gate
```

A failed gate means the system returns to research. The project does not force a trade when evidence is insufficient.

## Google Colab

Use `notebooks/01_v1_baseline.ipynb` as the starting research notebook. Experiments may be performed in Colab without committing every intermediate result to GitHub. Only validated research code and reproducible methodology should be promoted to the repository.

## Roadmap

V1 Market Baseline → V2 Advanced Features → V3 Multi-Horizon Forecast → V4 News Intelligence → V5 Sentiment/NLP → V6 On-chain → V7 Anomaly/Early Warning → V8 Ensemble/AI Router → V9 Paper Trading 24/7 → V10 Live Trading Gate

## Disclaimer

This is a research and software project, not financial advice. Historical or paper performance does not guarantee future results.
