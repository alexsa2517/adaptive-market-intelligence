"""V1.12 Forward Validation runner.

PROVE BEFORE TRADE

This runner uses the locked W6 model and locked parameters. It must not
retrain on forward observations or tune parameters from forward outcomes.

Expected workflow:
1. Load historical OHLCV through the latest available date.
2. Rebuild Feature Set C using historical + newly available OHLCV so rolling
   features are available for the newest observations.
3. Train the locked W6 model only on 2021-07-23 through 2024-11-03.
4. Generate probabilities/signals for observations after 2026-09-04.
5. Append observations to data/forward/v1_12_forward_monitor.csv.
6. Evaluate a signal only after its next-day close becomes available.

This file is intentionally a Python runner rather than a notebook artifact so
that the methodology remains reproducible outside Colab.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf
from xgboost import XGBClassifier

from src.forward_validation import (
    LOCKED_FEE,
    LOCKED_MODEL_VERSION,
    LOCKED_RULE_VERSION,
    LOCKED_SLIPPAGE,
    LOCKED_THRESHOLD,
    LOCKED_VOL_THRESHOLD,
)

FEATURES_C = [
    "return_1d", "return_5d", "volatility_10d", "momentum_10d",
    "close_sma7_gap", "close_sma21_gap", "ema12_ema26_gap",
    "rsi_14", "volume_change_1d", "trend_21_50", "momentum_20d",
    "volatility_20d", "range_pct", "volume_vs_ma20", "volatility_ratio",
]

FORWARD_START = pd.Timestamp("2026-09-05")
TRAIN_START = pd.Timestamp("2021-07-23")
TRAIN_END = pd.Timestamp("2024-11-03")


def load_market_data(start="2018-01-01", end=None):
    df = yf.download(
        "BTC-USD", start=start, end=end, auto_adjust=False, progress=False
    )
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df[["Open", "High", "Low", "Close", "Volume"]].dropna().sort_index()


def make_features_c(df):
    out = df.copy()
    close, high, low, volume = out["Close"], out["High"], out["Low"], out["Volume"]
    out["return_1d"] = close.pct_change()
    out["return_5d"] = close.pct_change(5)
    out["volatility_10d"] = out["return_1d"].rolling(10).std()
    out["momentum_10d"] = close / close.shift(10) - 1
    sma7, sma21 = close.rolling(7).mean(), close.rolling(21).mean()
    out["close_sma7_gap"] = close / sma7 - 1
    out["close_sma21_gap"] = close / sma21 - 1
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    out["ema12_ema26_gap"] = ema12 / ema26 - 1
    delta = close.diff()
    gain, loss = delta.clip(lower=0), -delta.clip(upper=0)
    rs = gain.rolling(14).mean() / loss.rolling(14).mean()
    out["rsi_14"] = 100 - (100 / (1 + rs))
    out["volume_change_1d"] = volume.pct_change()
    sma50 = close.rolling(50).mean()
    out["trend_21_50"] = sma21 / sma50 - 1
    out["momentum_20d"] = close / close.shift(20) - 1
    out["volatility_20d"] = out["return_1d"].rolling(20).std()
    out["range_pct"] = (high - low) / close
    volume_ma20 = volume.rolling(20).mean()
    out["volume_vs_ma20"] = volume / volume_ma20 - 1
    out["volatility_ratio"] = out["volatility_10d"] / out["volatility_20d"]
    future_close = close.shift(-1)
    out["target_next_day_up"] = np.where(
        future_close.isna(), np.nan, (future_close > close).astype(int)
    )
    return out


def main():
    market = load_market_data(end="2026-09-08")
    features = make_features_c(market)

    train = features.loc[TRAIN_START:TRAIN_END].dropna(
        subset=FEATURES_C + ["target_next_day_up"]
    )
    if len(train) != 1200:
        raise RuntimeError(f"Locked training window expected 1200 rows, got {len(train)}")

    model = XGBClassifier(
        n_estimators=300, max_depth=4, learning_rate=0.03,
        subsample=0.8, colsample_bytree=0.8,
        objective="binary:logistic", eval_metric="logloss",
        random_state=42, n_jobs=4,
    )
    model.fit(train[FEATURES_C], train["target_next_day_up"].astype(int))

    forward = features.loc[FORWARD_START:].copy()
    forward = forward.dropna(subset=FEATURES_C)
    forward["prob_up"] = model.predict_proba(forward[FEATURES_C])[:, 1]
    forward["trend_50"] = forward["Close"] / forward["Close"].rolling(50).mean() - 1
    forward["high_vol"] = forward["volatility_20"] >= LOCKED_VOL_THRESHOLD
    forward["trend_regime"] = np.select(
        [forward["trend_50"] > 0.05, forward["trend_50"] < -0.05],
        ["Bull", "Bear"], default="Sideways"
    )
    forward["baseline_signal"] = (forward["prob_up"] >= LOCKED_THRESHOLD).astype(int)
    forward["regime_filter"] = (
        (forward["trend_regime"] == "Bull") | forward["high_vol"]
    )
    forward["signal"] = (
        forward["baseline_signal"].astype(bool) & forward["regime_filter"]
    ).astype(int)
    forward["model_version"] = LOCKED_MODEL_VERSION
    forward["threshold"] = LOCKED_THRESHOLD
    forward["vol_threshold"] = LOCKED_VOL_THRESHOLD
    forward["fee_per_side"] = LOCKED_FEE
    forward["slippage_per_side"] = LOCKED_SLIPPAGE
    forward["rule"] = LOCKED_RULE_VERSION

    cols = [
        "Close", "prob_up", "trend_50", "volatility_20", "trend_regime",
        "high_vol", "baseline_signal", "regime_filter", "signal",
        "model_version", "threshold", "vol_threshold", "fee_per_side",
        "slippage_per_side", "rule",
    ]
    result = forward[cols].reset_index().rename(columns={"index": "Date"})
    print(result)
    print(f"Signals: {int(result['signal'].sum())}")


if __name__ == "__main__":
    main()
