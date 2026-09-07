from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class V2FeatureConfig:
    """Research-only configuration for external-information features."""

    news_window_hours: int = 24
    news_7d_window_days: int = 7


def add_cross_asset_features(
    base: pd.DataFrame,
    assets: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """Add lagged cross-asset returns/levels without changing the V1 model.

    `assets` should contain timestamp-indexed DataFrames with a `Close` column.
    Features are calculated from information available on the same observation
    date. Callers are responsible for aligning release timestamps for assets
    whose observations are published after the market close.
    """
    out = base.copy()
    for name, asset in assets.items():
        close = asset["Close"].astype(float).sort_index()
        daily = pd.DataFrame(index=close.index)
        daily[f"{name}_return_1d"] = close.pct_change()
        daily[f"{name}_return_5d"] = close.pct_change(5)
        if name == "vix":
            daily["vix_level"] = close
            daily["vix_change_1d"] = close.diff()
        elif name == "us10y":
            daily["us10y_yield_change_1d"] = close.diff()
        out = out.join(daily, how="left")
    return out


def add_macro_release_features(
    base: pd.DataFrame,
    releases: pd.DataFrame,
    *,
    value_columns: Iterable[str],
) -> pd.DataFrame:
    """As-of join macro releases using publication timestamps.

    `releases` must have a UTC-aware `release_time` column and one or more value
    columns. The base index represents the prediction timestamp. This function
    deliberately uses an as-of join so future releases cannot leak backward.
    """
    out = base.copy()
    if not isinstance(out.index, pd.DatetimeIndex):
        raise TypeError("base must use a DatetimeIndex")
    rel = releases.copy()
    rel["release_time"] = pd.to_datetime(rel["release_time"], utc=True)
    rel = rel.sort_values("release_time")
    left = out.reset_index().rename(columns={out.index.name or "index": "prediction_time"})
    left["prediction_time"] = pd.to_datetime(left["prediction_time"], utc=True)
    keep = ["release_time", *value_columns]
    rel = rel[keep]
    merged = pd.merge_asof(
        left.sort_values("prediction_time"),
        rel,
        left_on="prediction_time",
        right_on="release_time",
        direction="backward",
    )
    merged = merged.drop(columns=["release_time"])
    merged = merged.set_index("prediction_time")
    merged.index = merged.index.tz_convert(None)
    return merged.reindex(out.index)


def build_news_daily_features(
    news: pd.DataFrame,
    *,
    timestamp_col: str = "published_at",
    sentiment_col: str = "sentiment",
    source_col: str | None = "source",
    bitcoin_flag_col: str | None = "is_bitcoin",
) -> pd.DataFrame:
    """Aggregate timestamped news into daily research features.

    Sentiment is expected to be a numeric score already produced by a separately
    validated NLP component. No sentiment model is silently selected here.
    """
    if news.empty:
        return pd.DataFrame()
    df = news.copy()
    df[timestamp_col] = pd.to_datetime(df[timestamp_col], utc=True)
    df["date"] = df[timestamp_col].dt.floor("D").dt.tz_localize(None)
    df[sentiment_col] = pd.to_numeric(df[sentiment_col], errors="coerce")

    grouped = df.groupby("date")
    out = grouped[sentiment_col].agg(
        news_sentiment_score="mean",
        news_count_24h="count",
    )
    out["positive_news_ratio"] = grouped[sentiment_col].apply(lambda x: (x > 0.05).mean())
    out["negative_news_ratio"] = grouped[sentiment_col].apply(lambda x: (x < -0.05).mean())
    out["neutral_news_ratio"] = grouped[sentiment_col].apply(lambda x: ((x >= -0.05) & (x <= 0.05)).mean())
    out["news_sentiment_change_24h"] = out["news_sentiment_score"].diff()
    out["news_count_7d"] = out["news_count_24h"].rolling(7, min_periods=1).sum()

    if source_col and source_col in df.columns:
        out["macro_news_share"] = grouped[source_col].apply(
            lambda x: x.astype(str).str.contains("macro|fed|cpi|inflation|rates", case=False, regex=True).mean()
        )
    else:
        out["macro_news_share"] = np.nan

    if bitcoin_flag_col and bitcoin_flag_col in df.columns:
        out["bitcoin_news_share"] = grouped[bitcoin_flag_col].mean().astype(float)
    else:
        out["bitcoin_news_share"] = np.nan

    median_count = out["news_count_24h"].rolling(30, min_periods=10).median()
    median_negative = out["negative_news_ratio"].rolling(30, min_periods=10).median()
    out["breaking_news_flag"] = (out["news_count_24h"] > 2 * median_count).astype(int)
    out["negative_news_spike"] = (out["negative_news_ratio"] > 2 * median_negative).astype(int)
    out["positive_news_spike"] = (out["positive_news_ratio"] > 2 * out["positive_news_ratio"].rolling(30, min_periods=10).median()).astype(int)
    return out
