from __future__ import annotations

import numpy as np
import pandas as pd


FEATURE_COLUMNS = [
    "return_1d",
    "return_5d",
    "volatility_10d",
    "momentum_10d",
    "sma_7",
    "sma_21",
    "ema_12",
    "ema_26",
    "rsi_14",
    "volume_change_1d",
]


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Build leakage-safe daily features and a valid next-day direction target.

    All features use information available on the current trading day only.
    The final row is dropped because its next-day target is unknown.
    """
    out = df.copy()
    close = out["Close"]
    volume = out["Volume"]

    out["return_1d"] = close.pct_change(1)
    out["return_5d"] = close.pct_change(5)
    out["volatility_10d"] = out["return_1d"].rolling(10).std()
    out["momentum_10d"] = close / close.shift(10) - 1
    out["sma_7"] = close.rolling(7).mean()
    out["sma_21"] = close.rolling(21).mean()
    out["ema_12"] = close.ewm(span=12, adjust=False).mean()
    out["ema_26"] = close.ewm(span=26, adjust=False).mean()

    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    out["rsi_14"] = 100 - (100 / (1 + rs))
    out["volume_change_1d"] = volume.pct_change(1)

    # Keep the unknown final target as NaN instead of silently converting it to 0.
    future_close = close.shift(-1)
    out["target_next_day_up"] = np.where(
        future_close.isna(),
        np.nan,
        (future_close > close).astype(int),
    )

    out = out.replace([np.inf, -np.inf], np.nan)
    return out.dropna(subset=FEATURE_COLUMNS + ["target_next_day_up"])
