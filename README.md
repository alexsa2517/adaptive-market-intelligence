# Adaptive Market Intelligence

**PROVE BEFORE TRADE**

An evidence-first market intelligence and forecasting system. The project is designed to test whether a measurable predictive edge exists before any real-money trading is allowed.

## V1 — Market Prediction Baseline

Initial scope:
- Real OHLCV market data
- Return, volatility and momentum features
- SMA, EMA, RSI and volume-change features
- Logistic Regression, Random Forest and XGBoost baselines
- Temporal train/validation/test split (no shuffling)
- Out-of-sample evaluation
- Walk-forward validation
- Backtest metrics including directional accuracy, P&L, max drawdown and Sharpe ratio

## Principle

> The system is not built to promise profit. It is built to discover whether the data contains a repeatable edge.

No live trading is part of V1. A model must pass controlled out-of-sample testing and paper trading before it can be considered for a future live-trading gate.

## Google Colab

Start with `notebooks/01_v1_baseline.ipynb` in Google Colab. The notebook downloads market data, builds features, trains baseline models, evaluates them without look-ahead leakage, and produces a PASS/FAIL-style research report.

## Roadmap

V1 Market Baseline → V2 Advanced Features → V3 Multi-Horizon Forecast → V4 News Intelligence → V5 Sentiment/NLP → V6 On-chain → V7 Anomaly/Early Warning → V8 Ensemble/AI Router → V9 Paper Trading 24/7 → V10 Live Trading Gate

## Disclaimer

This is a research and software project, not financial advice. Historical or paper performance does not guarantee future results.
