"""V2.1 Macro Variable Discovery Engine.

Research only. The previous V2 cross-asset candidate pool produced no KEEP or
INVESTIGATE variables and was intentionally emptied. This version tests a new,
previously untested macro candidate family from FRED.

Rules:
- Previous failed cross-asset variables are NOT reintroduced.
- Macro observations are conservatively lagged before they can enter a model.
- Candidates are screened statistically and by time-ordered OOS comparison.
- No result promotes a feature to the locked V1.12 model.
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from statsmodels.stats.multitest import multipletests

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports" / "v2"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

SYMBOLS = [s.strip() for s in os.getenv("V2_SYMBOLS", "AAPL,NVDA,MSFT,AMZN,TSLA,XOM,JPM,GLD,SPY,QQQ").split(",") if s.strip()]
START = os.getenv("V2_START", "2018-01-01")
HORIZON = 1
LAGS = (0, 1, 2, 3, 5, 10, 20)
MIN_N = 250
FDR_ALPHA = 0.05
MIN_ABS_R = 0.05
TRAIN = 756
TEST = 126
STEP = 126

# New macro family only. The old failed cross-asset pool remains empty.
FRED_SERIES = {
    "fed_funds": "DFF",
    "us10y": "DGS10",
    "us2y": "DGS2",
    "hy_spread": "BAMLH0A0HYM2",
    "financial_conditions": "NFCI",
    "cpi": "CPIAUCSL",
    "unemployment": "UNRATE",
}


def download_fred(series_id: str) -> pd.Series:
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    df = pd.read_csv(url, parse_dates=["observation_date"])
    value_col = [c for c in df.columns if c != "observation_date"][0]
    s = pd.to_numeric(df[value_col], errors="coerce")
    s.index = pd.DatetimeIndex(df["observation_date"]).tz_localize(None)
    return s.rename(series_id).dropna().sort_index()


def build_macro_features(index: pd.DatetimeIndex) -> pd.DataFrame:
    out = pd.DataFrame(index=index)
    for name, series_id in FRED_SERIES.items():
        try:
            raw = download_fred(series_id)
            daily = raw.reindex(index).ffill()
            # Conservative availability lag: daily market rates get 2 days;
            # monthly/weekly macro releases get 30 days.
            availability_lag = 30 if name in {"cpi", "unemployment", "financial_conditions"} else 2
            available = daily.shift(availability_lag)
            if name == "fed_funds":
                out["macro_fed_funds_change_5d"] = available.diff(5)
            elif name == "us10y":
                out["macro_us10y_change_1d"] = available.diff(1)
                out["macro_us10y_change_5d"] = available.diff(5)
            elif name == "us2y":
                out["macro_us2y_change_1d"] = available.diff(1)
                out["macro_us2y_change_5d"] = available.diff(5)
            elif name == "hy_spread":
                out["macro_hy_spread_change_5d"] = available.diff(5)
            elif name == "financial_conditions":
                out["macro_financial_conditions_change_5d"] = available.diff(5)
            elif name == "cpi":
                out["macro_cpi_yoy"] = available.pct_change(252)
                out["macro_cpi_change_30d"] = available.pct_change(30)
            elif name == "unemployment":
                out["macro_unemployment_level"] = available
                out["macro_unemployment_change"] = available.diff(30)
        except Exception as exc:
            print(f"WARN: FRED {name} unavailable: {exc}")
    # A new derived macro feature: the 10Y-2Y yield curve.
    try:
        us10y = download_fred(FRED_SERIES["us10y"]).reindex(index).ffill().shift(2)
        us2y = download_fred(FRED_SERIES["us2y"]).reindex(index).ffill().shift(2)
        out["macro_yield_curve_10y2y"] = us10y - us2y
        out["macro_yield_curve_change_5d"] = out["macro_yield_curve_10y2y"].diff(5)
    except Exception as exc:
        print(f"WARN: yield curve unavailable: {exc}")
    return out.replace([np.inf, -np.inf], np.nan)


def download_asset_close(symbol: str) -> pd.Series:
    import yfinance as yf
    df = yf.download(symbol, start=START, auto_adjust=False, progress=False)
    if df.empty:
        raise RuntimeError(f"No market data returned for {symbol}")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    s = df["Close"].astype(float)
    s.index = pd.DatetimeIndex(s.index).tz_localize(None)
    return s.rename(symbol).sort_index()


def market_features(close: pd.Series) -> pd.DataFrame:
    ret = close.pct_change()
    return pd.DataFrame({
        "return_1d": ret,
        "return_5d": close.pct_change(5),
        "return_20d": close.pct_change(20),
        "volatility_20d": ret.rolling(20).std(),
        "momentum_20d": close / close.shift(20) - 1,
        "sma_20_gap": close / close.rolling(20).mean() - 1,
        "sma_50_gap": close / close.rolling(50).mean() - 1,
    }, index=close.index)


def make_dataset(symbol: str, macro: pd.DataFrame) -> pd.DataFrame:
    close = download_asset_close(symbol)
    market = market_features(close)
    target = (close.shift(-HORIZON) > close).astype(float).rename("target")
    target.iloc[-HORIZON:] = np.nan
    return market.join(macro, how="inner").join(target, how="inner")


def corr_test(x: pd.Series, y: pd.Series):
    z = pd.concat([x, y], axis=1).dropna()
    if len(z) < 3 or z.iloc[:, 0].nunique() < 2:
        return np.nan, np.nan, np.nan, np.nan, len(z)
    pr, pp = pearsonr(z.iloc[:, 0], z.iloc[:, 1])
    sr, sp = spearmanr(z.iloc[:, 0], z.iloc[:, 1])
    return float(pr), float(pp), float(sr), float(sp), len(z)


def oos_delta(dataset: pd.DataFrame, feature: str):
    base_cols = ["return_1d", "return_5d", "return_20d", "volatility_20d", "momentum_20d", "sma_20_gap", "sma_50_gap"]
    frame = dataset[base_cols + [feature, "target"]].dropna()
    if len(frame) < TRAIN + TEST:
        return np.nan, 0, 0, np.nan
    deltas = []
    positive = 0
    folds = 0
    for start in range(0, len(frame) - TRAIN - TEST + 1, STEP):
        tr = frame.iloc[start:start + TRAIN]
        te = frame.iloc[start + TRAIN:start + TRAIN + TEST]
        base = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, random_state=42))
        ext = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, random_state=42))
        base.fit(tr[base_cols], tr["target"])
        ext.fit(tr[base_cols + [feature]], tr["target"])
        base_acc = (base.predict(te[base_cols]) == te["target"].to_numpy()).mean()
        ext_acc = (ext.predict(te[base_cols + [feature]]) == te["target"].to_numpy()).mean()
        delta = float(ext_acc - base_acc)
        deltas.append(delta)
        positive += int(delta > 0)
        folds += 1
    return float(np.mean(deltas)), folds, positive, float(np.median(deltas))


def run_asset(symbol: str, macro: pd.DataFrame) -> pd.DataFrame:
    dataset = make_dataset(symbol, macro)
    rows = []
    for base_feature in macro.columns:
        for lag in LAGS:
            feature_series = dataset[base_feature].shift(lag)
            pr, pp, sr, sp, n = corr_test(feature_series, dataset["target"])
            tmp = dataset.copy()
            tmp["candidate"] = feature_series
            delta, folds, positive, median_delta = oos_delta(tmp, "candidate") if n >= MIN_N else (np.nan, 0, 0, np.nan)
            rows.append({
                "asset": symbol,
                "feature": base_feature,
                "lag": lag,
                "pearson_r": pr,
                "pearson_p": pp,
                "spearman_r": sr,
                "spearman_p": sp,
                "n": n,
                "oos_delta_accuracy": delta,
                "oos_median_delta": median_delta,
                "oos_folds": folds,
                "oos_positive_folds": positive,
            })
    return pd.DataFrame(rows)


def classify(results: pd.DataFrame) -> pd.DataFrame:
    out = results.copy()
    _, q, _, _ = multipletests(out["pearson_p"].fillna(1).to_numpy(), alpha=FDR_ALPHA, method="fdr_bh")
    out["pearson_q"] = q
    out["oos_positive_rate"] = out["oos_positive_folds"] / out["oos_folds"].replace(0, np.nan)
    significant = (out["pearson_q"] <= FDR_ALPHA) & (out["pearson_r"].abs() >= MIN_ABS_R) & (out["n"] >= MIN_N)
    oos_good = (out["oos_delta_accuracy"] > 0) & (out["oos_positive_rate"] >= 0.50) & (out["oos_folds"] >= 3)
    strong_oos = (out["oos_delta_accuracy"] >= 0.005) & (out["oos_positive_rate"] >= 0.60) & (out["oos_folds"] >= 4)
    out["status"] = np.select(
        [significant & strong_oos, significant & oos_good, significant],
        ["KEEP", "INVESTIGATE", "WEAK"],
        default="REMOVE",
    )
    out["evidence_score"] = (
        significant.astype(int) * 30
        + oos_good.astype(int) * 30
        + strong_oos.astype(int) * 25
        + (out["oos_positive_rate"].fillna(0) * 15)
    ).round(2)
    return out.sort_values(["asset", "status", "evidence_score"], ascending=[True, True, False])


def write_reports(results: pd.DataFrame) -> None:
    results.to_csv(REPORT_DIR / "variable_scorecard.csv", index=False)
    results[results["status"] == "REMOVE"].to_csv(REPORT_DIR / "removed_variables.csv", index=False)
    results[results["status"].isin(["KEEP", "INVESTIGATE"])].to_csv(REPORT_DIR / "economic_fingerprint.csv", index=False)
    top = results[results["status"].isin(["KEEP", "INVESTIGATE", "WEAK"])].head(100)
    top.to_csv(REPORT_DIR / "v2_macro_candidates.csv", index=False)
    lines = [
        "# V2.1 Macro Variable Discovery",
        "",
        "Research-only. The locked V1.12 model is unchanged.",
        "The previous failed cross-asset candidate pool is not reintroduced.",
        "",
        f"Assets tested: {', '.join(SYMBOLS)}",
        f"Candidate lags: {', '.join(map(str, LAGS))}",
        "",
        "## Status rules",
        "- KEEP: statistically screened and strong positive OOS evidence.",
        "- INVESTIGATE: statistically screened and positive OOS evidence, but below the stronger gate.",
        "- WEAK: statistically significant but insufficient OOS evidence.",
        "- REMOVE: fails the statistical gate.",
        "- Final promotion still requires cost testing, robustness, and an untouched holdout.",
        "",
        "## Summary",
        f"KEEP={int((results.status == 'KEEP').sum())}",
        f"INVESTIGATE={int((results.status == 'INVESTIGATE').sum())}",
        f"WEAK={int((results.status == 'WEAK').sum())}",
        f"REMOVE={int((results.status == 'REMOVE').sum())}",
        "",
        "## Top candidates",
    ]
    if top.empty:
        lines.append("No candidate reached WEAK/INVESTIGATE/KEEP status.")
    else:
        for _, r in top.iterrows():
            lines.append(f"- {r.asset}: {r.feature} lag {int(r.lag)} | status={r.status} | q={r.pearson_q:.4g} | OOS Δ={r.oos_delta_accuracy:.4%} | positive={int(r.oos_positive_folds)}/{int(r.oos_folds)}")
    (REPORT_DIR / "v2_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    print("V2.1 MACRO VARIABLE DISCOVERY — RESEARCH ONLY")
    probe_index = download_asset_close(SYMBOLS[0]).index
    macro = build_macro_features(probe_index)
    if macro.empty or not len(macro.columns):
        raise RuntimeError("No new macro variables could be loaded")
    all_results = []
    for symbol in SYMBOLS:
        print(f"Testing {symbol}...")
        try:
            all_results.append(run_asset(symbol, macro))
        except Exception as exc:
            print(f"WARN: {symbol} skipped: {exc}")
    if not all_results:
        raise RuntimeError("No assets were successfully tested")
    results = classify(pd.concat(all_results, ignore_index=True))
    write_reports(results)
    print(results[results["status"].isin(["KEEP", "INVESTIGATE", "WEAK"])]
          [["asset", "feature", "lag", "pearson_q", "oos_delta_accuracy", "oos_positive_folds", "oos_folds", "status"]]
          .head(100).to_string(index=False))
    print(f"Reports written to {REPORT_DIR}")


if __name__ == "__main__":
    main()
