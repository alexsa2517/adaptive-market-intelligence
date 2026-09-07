"""V2 Automated Variable Discovery Engine.

Research only. The engine compares each candidate external variable with a
market-only baseline for each asset using time-ordered out-of-sample folds.
It writes an auditable Scorecard and Economic Fingerprint.

No result here promotes a feature to the locked V1.12 model.
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf
from scipy.stats import pearsonr, spearmanr
from statsmodels.stats.multitest import multipletests
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports" / "v2"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

SYMBOLS = [s.strip() for s in os.getenv("V2_SYMBOLS", "AAPL,NVDA,MSFT,AMZN,TSLA,XOM,JPM,GLD,SPY,QQQ").split(",") if s.strip()]
START = os.getenv("V2_START", "2018-01-01")
HORIZON = 1
LAGS = (0, 1, 2, 3, 5, 10, 20, 60)
MIN_N = 250
FDR_ALPHA = 0.05
MIN_ABS_R = 0.05
TRAIN = 756
TEST = 126
STEP = 126

# Candidate external variables. These are deliberately broad; the gate removes
# variables that do not demonstrate useful evidence for an individual asset.
CROSS_ASSETS = {
    "gold": "GC=F",
    "oil": "CL=F",
    "dxy": "DX-Y.NYB",
    "sp500": "^GSPC",
    "nasdaq": "^IXIC",
    "vix": "^VIX",
    "us10y": "^TNX",
    "copper": "HG=F",
    "silver": "SI=F",
    "bitcoin": "BTC-USD",
}


def download_close(symbol: str) -> pd.Series:
    df = yf.download(symbol, start=START, auto_adjust=False, progress=False)
    if df.empty:
        raise RuntimeError(f"No data returned for {symbol}")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df["Close"].astype(float).rename(symbol).sort_index()


def make_external_features() -> pd.DataFrame:
    frames = []
    for name, symbol in CROSS_ASSETS.items():
        try:
            close = download_close(symbol)
            frames.append(pd.DataFrame({
                f"{name}_return_1d": close.pct_change(),
                f"{name}_return_5d": close.pct_change(5),
                f"{name}_level": close if name == "vix" else np.nan,
            }))
        except Exception as exc:
            print(f"WARN: {name} unavailable: {exc}")
    if not frames:
        raise RuntimeError("No external market data could be downloaded")
    out = pd.concat(frames, axis=1)
    # Drop synthetic level columns for non-VIX assets.
    out = out[[c for c in out.columns if not c.endswith("_level") or c == "vix_level"]]
    return out


def market_features(close: pd.Series) -> pd.DataFrame:
    ret = close.pct_change()
    out = pd.DataFrame(index=close.index)
    out["return_1d"] = ret
    out["return_5d"] = close.pct_change(5)
    out["return_20d"] = close.pct_change(20)
    out["volatility_20d"] = ret.rolling(20).std()
    out["momentum_20d"] = close / close.shift(20) - 1
    out["sma_20_gap"] = close / close.rolling(20).mean() - 1
    out["sma_50_gap"] = close / close.rolling(50).mean() - 1
    return out


def make_dataset(symbol: str, external: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    close = download_close(symbol)
    market = market_features(close)
    target = (close.shift(-HORIZON) > close).astype(float).rename("target")
    target.iloc[-HORIZON:] = np.nan
    return market.join(external, how="inner").join(target, how="inner"), close


def corr_test(x: pd.Series, y: pd.Series) -> tuple[float, float, float, float, int]:
    z = pd.concat([x, y], axis=1).dropna()
    if len(z) < 3 or z.iloc[:, 0].nunique() < 2:
        return np.nan, np.nan, np.nan, np.nan, len(z)
    pr, pp = pearsonr(z.iloc[:, 0], z.iloc[:, 1])
    sr, sp = spearmanr(z.iloc[:, 0], z.iloc[:, 1])
    return float(pr), float(pp), float(sr), float(sp), len(z)


def accuracy(y: pd.Series, pred: np.ndarray) -> float:
    return float((y.to_numpy() == pred).mean()) if len(y) else np.nan


def oos_delta(dataset: pd.DataFrame, feature: str) -> tuple[float, int, int, float]:
    cols = ["return_1d", "return_5d", "return_20d", "volatility_20d", "momentum_20d", "sma_20_gap", "sma_50_gap"]
    frame = dataset[cols + [feature, "target"]].dropna()
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
        base.fit(tr[cols], tr["target"])
        ext.fit(tr[cols + [feature]], tr["target"])
        base_acc = accuracy(te["target"], base.predict(te[cols]))
        ext_acc = accuracy(te["target"], ext.predict(te[cols + [feature]]))
        deltas.append(ext_acc - base_acc)
        positive += int(ext_acc > base_acc)
        folds += 1
    return float(np.mean(deltas)), folds, positive, float(np.median(deltas))


def run_asset(symbol: str, external: pd.DataFrame) -> pd.DataFrame:
    dataset, _ = make_dataset(symbol, external)
    rows = []
    for base_feature in external.columns:
        for lag in LAGS:
            feature = dataset[base_feature].shift(lag)
            pr, pp, sr, sp, n = corr_test(feature, dataset["target"])
            if n < MIN_N:
                delta, folds, positive, median_delta = np.nan, 0, 0, np.nan
            else:
                tmp = dataset.copy()
                tmp["candidate"] = feature
                delta, folds, positive, median_delta = oos_delta(tmp, "candidate")
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
    p = out["pearson_p"].fillna(1).to_numpy()
    _, q, _, _ = multipletests(p, alpha=FDR_ALPHA, method="fdr_bh")
    out["pearson_q"] = q
    out["oos_positive_rate"] = out["oos_positive_folds"] / out["oos_folds"].replace(0, np.nan)
    significant = (out["pearson_q"] <= FDR_ALPHA) & (out["pearson_r"].abs() >= MIN_ABS_R) & (out["n"] >= MIN_N)
    oos_good = (out["oos_delta_accuracy"] > 0) & (out["oos_positive_rate"] >= 0.50) & (out["oos_folds"] >= 3)
    out["status"] = np.select([significant & oos_good, significant], ["KEEP", "INVESTIGATE"], default="REMOVE")
    out["evidence_score"] = (
        significant.astype(int) * 40
        + oos_good.astype(int) * 40
        + (out["oos_positive_rate"].fillna(0) * 20)
    ).round(2)
    return out.sort_values(["asset", "status", "evidence_score"], ascending=[True, True, False])


def write_reports(results: pd.DataFrame) -> None:
    results.to_csv(REPORT_DIR / "variable_scorecard.csv", index=False)
    results[results["status"] == "REMOVE"].to_csv(REPORT_DIR / "removed_variables.csv", index=False)
    keep = results[results["status"] == "KEEP"]
    investigate = results[results["status"] == "INVESTIGATE"]
    keep.to_csv(REPORT_DIR / "economic_fingerprint.csv", index=False)
    lines = [
        "# V2 Automated Variable Discovery",
        "",
        "Research-only. V2 results do not modify the locked V1.12 model.",
        "",
        f"Assets tested: {', '.join(SYMBOLS)}",
        f"Candidate lags: {', '.join(map(str, LAGS))}",
        "",
        "## Interpretation",
        "- KEEP: statistically screened and positive OOS accuracy delta across at least half of walk-forward folds.",
        "- INVESTIGATE: statistically significant but not yet strong enough for promotion.",
        "- REMOVE: fails the statistical/OOS gate.",
        "- This is not causal proof. Final promotion requires independent holdout and cost/robustness testing.",
        "",
        "## KEEP summary",
    ]
    if keep.empty:
        lines.append("No variables passed the current gate.")
    else:
        for _, r in keep.iterrows():
            lines.append(f"- {r.asset}: {r.feature} lag {r.lag} | q={r.pearson_q:.4g} | OOS Δ={r.oos_delta_accuracy:.4%} | positive folds={int(r.oos_positive_folds)}/{int(r.oos_folds)}")
    lines += ["", "## INVESTIGATE summary"]
    if investigate.empty:
        lines.append("None.")
    else:
        for _, r in investigate.head(30).iterrows():
            lines.append(f"- {r.asset}: {r.feature} lag {r.lag} | q={r.pearson_q:.4g} | OOS Δ={r.oos_delta_accuracy if pd.notna(r.oos_delta_accuracy) else np.nan}")
    (REPORT_DIR / "v2_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    print("V2 AUTOMATED VARIABLE DISCOVERY — RESEARCH ONLY")
    external = make_external_features()
    all_results = []
    for symbol in SYMBOLS:
        print(f"Testing {symbol}...")
        try:
            all_results.append(run_asset(symbol, external))
        except Exception as exc:
            print(f"WARN: {symbol} skipped: {exc}")
    if not all_results:
        raise RuntimeError("No assets were successfully tested")
    results = classify(pd.concat(all_results, ignore_index=True))
    write_reports(results)
    print(results[results["status"] != "REMOVE"][["asset", "feature", "lag", "pearson_q", "oos_delta_accuracy", "status"]].to_string(index=False))
    print(f"Reports written to {REPORT_DIR}")


if __name__ == "__main__":
    main()
