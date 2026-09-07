from __future__ import annotations

import numpy as np
import pandas as pd


def build_regime_features(df: pd.DataFrame) -> pd.DataFrame:
    """Build leakage-safe market regime features from current/past prices.

    Bull/Bear thresholds are intentionally fixed at +/-5% from the 50-day SMA.
    The volatility threshold should be supplied from the training window during
    walk-forward evaluation; this module does not calculate it from future data.
    """
    out = df.copy()
    close = out["Close"]

    out["sma_50"] = close.rolling(50).mean()
    out["trend_50"] = close / out["sma_50"] - 1
    out["volatility_20"] = close.pct_change().rolling(20).std()

    out["trend_regime"] = np.select(
        [
            out["trend_50"] > 0.05,
            out["trend_50"] < -0.05,
        ],
        ["Bull", "Bear"],
        default="Sideways",
    )

    return out


def add_high_volatility_flag(
    df: pd.DataFrame,
    volatility_threshold: float,
) -> pd.DataFrame:
    """Add a high-volatility flag using a training-derived threshold."""
    out = df.copy()
    out["high_vol"] = (
        out["volatility_20"] >= volatility_threshold
    )
    return out


def add_moderate_regime_signal(
    df: pd.DataFrame,
    baseline_signal_column: str = "baseline_signal",
) -> pd.DataFrame:
    """Apply the locked Moderate regime rule.

    Moderate = baseline signal AND (Bull OR High Volatility).
    """
    out = df.copy()
    out["moderate_signal"] = (
        out[baseline_signal_column].astype(bool)
        & (
            (out["trend_regime"] == "Bull")
            | out["high_vol"].astype(bool)
        )
    ).astype(int)
    return out
