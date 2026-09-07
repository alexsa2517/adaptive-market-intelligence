# Adaptive Market Intelligence

**PROVE BEFORE TRADE**

An evidence-first market intelligence and forecasting system. The project is designed to test whether a measurable predictive edge exists before any real-money trading is allowed.

## Current Research Status — V1.10.8

The current research candidate is an XGBoost-based daily BTC direction model using Feature Set C, walk-forward threshold selection, and a Moderate market-regime filter.

### Locked research configuration

- XGBoost classifier
- Feature Set C: returns, volatility, momentum, SMA/EMA gaps, RSI, volume, trend and range features
- Walk-forward structure: 1,200-day train / 300-day validation / 250-day test
- Candidate thresholds: 0.50, 0.55, 0.60, 0.65, 0.70
- Moderate regime: baseline signal AND (Bull OR High Volatility)
- Bull regime: price > 50-day SMA by more than 5%
- Bear regime: price < 50-day SMA by more than 5%
- Volatility threshold: median 20-day volatility calculated from the training window only
- Base transaction cost assumption: 0.10% fee + 0.05% slippage per position change

### V1.10.8 research results

The Moderate regime candidate showed positive aggregate backtest performance under the base cost assumption and remained positive across the tested cost-sensitivity scenarios. However, this is **not proof of a future trading edge**. The regime hypothesis was developed through exploratory research and therefore requires an untouched holdout evaluation before it can be considered validated.

The current research process has passed a final methodology/data-alignment audit. The untouched final holdout is reserved separately and must not be used for parameter selection.

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
PASS → Paper Trading
  ↓
Sustained Paper Trading
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
