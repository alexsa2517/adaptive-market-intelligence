from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr
from statsmodels.stats.multitest import multipletests


@dataclass(frozen=True)
class SignificanceConfig:
    """Research-only screening rules. Nothing here promotes a feature to V1."""

    lags: tuple[int, ...] = (0, 1, 2, 3, 5, 10, 20, 60)
    min_observations: int = 120
    fdr_alpha: float = 0.05
    min_abs_correlation: float = 0.05
    min_abs_oos_delta: float = 0.0


def _future_return(close: pd.Series, horizon: int = 1) -> pd.Series:
    return close.shift(-horizon) / close - 1.0


def build_lagged_macro_matrix(
    asset: pd.DataFrame,
    macro: pd.DataFrame,
    *,
    close_col: str = "Close",
    config: SignificanceConfig | None = None,
) -> pd.DataFrame:
    """Create asset returns plus lagged macro variables.

    The macro frame must already contain only information that was available at
    each timestamp. For release data, callers should use an as-of join first.
    """
    cfg = config or SignificanceConfig()
    out = pd.DataFrame(index=asset.index).copy()
    out["future_return_1d"] = _future_return(asset[close_col].astype(float))

    macro = macro.copy().sort_index()
    for col in macro.columns:
        series = pd.to_numeric(macro[col], errors="coerce")
        for lag in cfg.lags:
            out[f"{col}_lag{lag}"] = series.reindex(out.index).shift(lag)
    return out


def _safe_corr(x: pd.Series, y: pd.Series, method: str) -> tuple[float, float, int]:
    frame = pd.concat([x, y], axis=1).dropna()
    n = len(frame)
    if n < 3 or frame.iloc[:, 0].nunique() < 2 or frame.iloc[:, 1].nunique() < 2:
        return np.nan, np.nan, n
    if method == "pearson":
        r, p = pearsonr(frame.iloc[:, 0], frame.iloc[:, 1])
    else:
        r, p = spearmanr(frame.iloc[:, 0], frame.iloc[:, 1])
    return float(r), float(p), n


def screen_macro_significance(
    matrix: pd.DataFrame,
    *,
    target_col: str = "future_return_1d",
    config: SignificanceConfig | None = None,
) -> pd.DataFrame:
    """Screen every macro variable/lag with descriptive correlation tests.

    P-values are corrected jointly using Benjamini-Hochberg FDR. This is a
    screening stage, not causal inference and not final feature selection.
    """
    cfg = config or SignificanceConfig()
    rows: list[dict] = []
    for col in matrix.columns:
        if col == target_col:
            continue
        r_p, p_p, n = _safe_corr(matrix[col], matrix[target_col], "pearson")
        r_s, p_s, _ = _safe_corr(matrix[col], matrix[target_col], "spearman")
        rows.append({
            "feature": col,
            "pearson_r": r_p,
            "pearson_p": p_p,
            "spearman_r": r_s,
            "spearman_p": p_s,
            "n": n,
        })

    result = pd.DataFrame(rows)
    if result.empty:
        return result

    p = result["pearson_p"].fillna(1.0).to_numpy()
    _, q, _, _ = multipletests(p, alpha=cfg.fdr_alpha, method="fdr_bh")
    result["pearson_q"] = q
    result["significant"] = (
        (result["pearson_q"] <= cfg.fdr_alpha)
        & (result["pearson_r"].abs() >= cfg.min_abs_correlation)
        & (result["n"] >= cfg.min_observations)
    )
    result["screen_status"] = np.where(result["significant"], "INVESTIGATE", "REMOVE")
    return result.sort_values(["significant", "pearson_q", "n"], ascending=[False, True, False]).reset_index(drop=True)


def economic_fingerprint(
    asset_name: str,
    screening: pd.DataFrame,
) -> pd.DataFrame:
    """Return a compact per-asset Economic Fingerprint."""
    out = screening.copy()
    out.insert(0, "asset", asset_name)
    return out[[
        "asset", "feature", "pearson_r", "pearson_p", "pearson_q",
        "spearman_r", "spearman_p", "n", "significant", "screen_status",
    ]]


def remove_weak_features(
    screening: pd.DataFrame,
    *,
    config: SignificanceConfig | None = None,
) -> list[str]:
    """Return features that fail the statistical screening gate."""
    cfg = config or SignificanceConfig()
    keep = screening[
        (screening["pearson_q"] <= cfg.fdr_alpha)
        & (screening["pearson_r"].abs() >= cfg.min_abs_correlation)
        & (screening["n"] >= cfg.min_observations)
    ]
    return keep["feature"].tolist()


def split_features_by_group(features: Iterable[str]) -> dict[str, list[str]]:
    """Classify surviving variables for audit/reporting."""
    groups = {"gold": [], "oil": [], "war": [], "crime": [], "macro": [], "other": []}
    for feature in features:
        name = feature.lower()
        if "gold" in name:
            groups["gold"].append(feature)
        elif "oil" in name:
            groups["oil"].append(feature)
        elif "war" in name or "geopolit" in name:
            groups["war"].append(feature)
        elif "crime" in name:
            groups["crime"].append(feature)
        elif any(k in name for k in ("cpi", "gdp", "unemployment", "fed", "yield", "dxy", "vix", "inflation")):
            groups["macro"].append(feature)
        else:
            groups["other"].append(feature)
    return groups
