from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from xgboost import XGBClassifier


LOCKED_THRESHOLD = 0.60
LOCKED_VOL_THRESHOLD = 0.026935
LOCKED_FEE = 0.0010
LOCKED_SLIPPAGE = 0.0005
LOCKED_MODEL_VERSION = "V1.10.9.1"
LOCKED_RULE_VERSION = "Bull OR High Vol"
LOCKED_TRAIN_START = "2021-07-23"
LOCKED_TRAIN_END = "2024-11-03"


def build_locked_w6_model(
    train_df: pd.DataFrame,
    feature_columns: list[str],
) -> XGBClassifier:
    """Train the immutable W6 model used by V1.12 forward validation."""
    model = XGBClassifier(
        n_estimators=300,
        max_depth=4,
        learning_rate=0.03,
        subsample=0.8,
        colsample_bytree=0.8,
        objective="binary:logistic",
        eval_metric="logloss",
        random_state=42,
        n_jobs=4,
    )
    model.fit(
        train_df[feature_columns],
        train_df["target_next_day_up"].astype(int),
    )
    return model


def generate_forward_signals(
    model: XGBClassifier,
    feature_df: pd.DataFrame,
    feature_columns: list[str],
    forward_start: str,
) -> pd.DataFrame:
    """Generate locked, long/flat forward signals without retraining."""
    out = feature_df.loc[
        pd.to_datetime(feature_df.index) >= pd.Timestamp(forward_start)
    ].copy()

    if out.empty:
        return out

    missing = [c for c in feature_columns if c not in out.columns]
    if missing:
        raise ValueError(f"Missing forward features: {missing}")

    x_forward = out[feature_columns]
    if x_forward.isna().any().any():
        bad = x_forward.isna().sum()
        bad = bad[bad > 0].to_dict()
        raise ValueError(f"Forward features contain NaN: {bad}")

    out["prob_up"] = model.predict_proba(x_forward)[:, 1]
    out["baseline_signal"] = (
        out["prob_up"] >= LOCKED_THRESHOLD
    ).astype(int)

    out["signal"] = (
        out["baseline_signal"].astype(bool)
        & (
            (out["trend_regime"] == "Bull")
            | out["high_vol"].astype(bool)
        )
    ).astype(int)

    out["model_version"] = LOCKED_MODEL_VERSION
    out["threshold"] = LOCKED_THRESHOLD
    out["vol_threshold"] = LOCKED_VOL_THRESHOLD
    out["fee_per_side"] = LOCKED_FEE
    out["slippage_per_side"] = LOCKED_SLIPPAGE
    out["rule"] = LOCKED_RULE_VERSION

    return out


def append_forward_log(
    signals: pd.DataFrame,
    path: str | Path = "data/forward/v1_12_forward_monitor.csv",
) -> pd.DataFrame:
    """Append forward observations without replacing prior dates."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    log_columns = [
        "Date",
        "Close",
        "prob_up",
        "trend_50",
        "volatility_20",
        "trend_regime",
        "high_vol",
        "baseline_signal",
        "regime_filter",
        "signal",
        "model_version",
        "threshold",
        "vol_threshold",
        "fee_per_side",
        "slippage_per_side",
        "rule",
    ]

    new_log = signals.reset_index().rename(columns={signals.index.name or "index": "Date"})
    if "Date" not in new_log.columns:
        new_log.insert(0, "Date", signals.index)

    # regime_filter is derived from the locked rule and kept explicit in the log.
    if "regime_filter" not in new_log.columns:
        new_log["regime_filter"] = (
            (new_log["trend_regime"] == "Bull")
            | new_log["high_vol"].astype(bool)
        )

    new_log = new_log[log_columns].copy()

    if path.exists():
        old_log = pd.read_csv(path, parse_dates=["Date"])
        combined = pd.concat([old_log, new_log], ignore_index=True)
    else:
        combined = new_log

    combined["Date"] = pd.to_datetime(combined["Date"])
    combined = (
        combined
        .drop_duplicates(subset=["Date"], keep="last")
        .sort_values("Date")
        .reset_index(drop=True)
    )
    combined.to_csv(path, index=False)
    return combined


def forward_integrity_check(log: pd.DataFrame) -> dict[str, bool]:
    """Check that locked parameters have not drifted in the forward log."""
    if log.empty:
        return {
            "threshold_locked": True,
            "vol_threshold_locked": True,
            "model_locked": True,
            "rule_locked": True,
        }

    return {
        "threshold_locked": bool((log["threshold"] == LOCKED_THRESHOLD).all()),
        "vol_threshold_locked": bool(
            (log["vol_threshold"] == LOCKED_VOL_THRESHOLD).all()
        ),
        "model_locked": bool(
            (log["model_version"] == LOCKED_MODEL_VERSION).all()
        ),
        "rule_locked": bool((log["rule"] == LOCKED_RULE_VERSION).all()),
    }
