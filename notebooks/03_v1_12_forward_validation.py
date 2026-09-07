"""V1.12 Forward Validation runner.

PROVE BEFORE TRADE

Uses the locked W6 model and locked parameters. Forward observations are
never used for retraining or parameter tuning.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

from src.forward_validation import (
    LOCKED_FEE,
    LOCKED_MODEL_VERSION,
    LOCKED_RULE_VERSION,
    LOCKED_SLIPPAGE,
    LOCKED_THRESHOLD,
    LOCKED_TRAIN_END,
    LOCKED_TRAIN_START,
    LOCKED_VOL_THRESHOLD,
    append_forward_log,
    build_locked_w6_model,
    forward_integrity_check,
)

FEATURES_C = [
    "return_1d", "return_5d", "volatility_10d", "momentum_10d",
    "close_sma7_gap", "close_sma21_gap", "ema12_ema26_gap",
    "rsi_14", "volume_change_1d", "trend_21_50", "momentum_20d",
    "volatility_20d", "range_pct", "volume_vs_ma20", "volatility_ratio",
]

FORWARD_START = pd.Timestamp("2026-09-05")
FORWARD_LOG = Path("data/forward/v1_12_forward_monitor.csv")


def load_market_data(start="2018-01-01", end=None):
    df = yf.download(
        "BTC-USD", start=start, end=end, auto_adjust=False, progress=False
    )
    if df.empty:
        raise RuntimeError("No BTC-USD market data returned.")
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
    out["trend_50"] = close / sma50 - 1
    out["high_vol"] = out["volatility_20d"] >= LOCKED_VOL_THRESHOLD
    out["trend_regime"] = np.select(
        [out["trend_50"] > 0.05, out["trend_50"] < -0.05],
        ["Bull", "Bear"], default="Sideways"
    )
    return out


def main():
    market = load_market_data(end="2026-09-08")
    features = make_features_c(market)

    train = features.loc[LOCKED_TRAIN_START:LOCKED_TRAIN_END].dropna(
        subset=FEATURES_C + ["target_next_day_up"]
    )
    if len(train) != 1200:
        raise RuntimeError(
            f"Locked training window expected 1200 rows, got {len(train)}"
        )

    model = build_locked_w6_model(train, FEATURES_C)

    forward = features.loc[FORWARD_START:].dropna(subset=FEATURES_C).copy()
    if forward.empty:
        raise RuntimeError("No forward observations available.")

    forward["prob_up"] = model.predict_proba(forward[FEATURES_C])[:, 1]
    forward["baseline_signal"] = (
        forward["prob_up"] >= LOCKED_THRESHOLD
    ).astype(int)
    forward["regime_filter"] = (
        (forward["trend_regime"] == "Bull") | forward["high_vol"]
    )
    forward["signal"] = (
        forward["baseline_signal"].astype(bool)
        & forward["regime_filter"]
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
    log = append_forward_log(result.set_index("Date"), FORWARD_LOG)

    integrity = forward_integrity_check(log)
    if not all(integrity.values()):
        raise RuntimeError(f"Forward integrity check failed: {integrity}")

    print(result.to_string(index=False))
    print(f"Signals: {int(result['signal'].sum())}")
    print(f"Forward observations stored: {len(log)}")
    print(f"Integrity: {integrity}")


if __name__ == "__main__":
    main()
