"""V2 Model Comparison Lab — Colab friendly.

Purpose:
    Compare market-only V1-style features against external-variable models.

Research-only:
    - Uses time-ordered walk-forward evaluation.
    - Does not touch or modify the locked V1.12 forward model.
    - If reports/v2/variable_scorecard.csv exists, only variables marked KEEP are
      used in the promoted-candidate comparison. INVESTIGATE variables remain
      visible but are not promoted automatically.

Run in Google Colab or from the repository root:
    pip install -r requirements.txt
    python notebooks/06_v2_model_comparison.py
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports" / "v2"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

SYMBOLS = [s.strip() for s in os.getenv("V2_COMPARE_SYMBOLS", "AAPL,NVDA,MSFT,AMZN,TSLA,XOM,JPM,GLD,SPY,QQQ,BTC-USD").split(",") if s.strip()]
START = os.getenv("V2_COMPARE_START", "2018-01-01")
TRAIN = int(os.getenv("V2_COMPARE_TRAIN", "756"))
TEST = int(os.getenv("V2_COMPARE_TEST", "126"))
STEP = int(os.getenv("V2_COMPARE_STEP", "126"))
MIN_FOLDS = int(os.getenv("V2_COMPARE_MIN_FOLDS", "4"))

CROSS_ASSETS = {
    "gold": "GC=F", "oil": "CL=F", "dxy": "DX-Y.NYB", "sp500": "^GSPC",
    "nasdaq": "^IXIC", "vix": "^VIX", "us10y": "^TNX", "copper": "HG=F",
    "silver": "SI=F", "bitcoin": "BTC-USD",
}

MARKET_FEATURES = [
    "return_1d", "return_5d", "return_20d", "volatility_20d",
    "momentum_20d", "sma_20_gap", "sma_50_gap",
]


def download_close(symbol: str) -> pd.Series:
    df = yf.download(symbol, start=START, auto_adjust=False, progress=False)
    if df.empty:
        raise RuntimeError(f"No data returned for {symbol}")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df["Close"].astype(float).rename(symbol).sort_index()


def build_market(close: pd.Series) -> pd.DataFrame:
    ret = close.pct_change()
    out = pd.DataFrame(index=close.index)
    out["return_1d"] = ret
    out["return_5d"] = close.pct_change(5)
    out["return_20d"] = close.pct_change(20)
    out["volatility_20d"] = ret.rolling(20).std()
    out["momentum_20d"] = close / close.shift(20) - 1
    out["sma_20_gap"] = close / close.rolling(20).mean() - 1
    out["sma_50_gap"] = close / close.rolling(50).mean() - 1
    future = close.shift(-1)
    out["target"] = np.where(future.isna(), np.nan, (future > close).astype(float))
    return out


def build_external() -> pd.DataFrame:
    frames = []
    for name, symbol in CROSS_ASSETS.items():
        try:
            close = download_close(symbol)
            frame = pd.DataFrame(index=close.index)
            frame[f"{name}_return_1d"] = close.pct_change()
            frame[f"{name}_return_5d"] = close.pct_change(5)
            if name == "vix":
                frame["vix_level"] = close
            elif name == "us10y":
                frame["us10y_level"] = close
            frames.append(frame)
        except Exception as exc:
            print(f"WARN external {name}: {exc}")
    if not frames:
        raise RuntimeError("No external data available")
    return pd.concat(frames, axis=1).sort_index()


def load_keep_variables() -> list[str]:
    path = REPORT_DIR / "variable_scorecard.csv"
    if not path.exists():
        return []
    score = pd.read_csv(path)
    if "status" not in score.columns or "feature" not in score.columns or "lag" not in score.columns:
        return []
    keep = score[score["status"].eq("KEEP")].copy()
    # Use the strongest KEEP row per feature/asset, then apply the recorded lag.
    if keep.empty:
        return []
    keep = keep.sort_values(["asset", "evidence_score"], ascending=[True, False])
    names = []
    for _, row in keep.iterrows():
        names.append(f"{row['feature']}__lag{int(row['lag'])}")
    return sorted(set(names))


def apply_lagged_external(external: pd.DataFrame, selected: list[str]) -> pd.DataFrame:
    out = pd.DataFrame(index=external.index)
    for item in selected:
        feature, lag_text = item.rsplit("__lag", 1)
        if feature in external.columns:
            out[item] = external[feature].shift(int(lag_text))
    return out


def evaluate_variant(frame: pd.DataFrame, features: list[str]) -> dict:
    data = frame[features + ["target"]].dropna()
    if len(data) < TRAIN + TEST:
        return {"folds": 0, "positive_folds": 0, "mean_accuracy": np.nan, "mean_delta": np.nan}
    accuracies = []
    for start in range(0, len(data) - TRAIN - TEST + 1, STEP):
        train = data.iloc[start:start + TRAIN]
        test = data.iloc[start + TRAIN:start + TRAIN + TEST]
        model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, random_state=42))
        model.fit(train[features], train["target"])
        pred = model.predict(test[features])
        accuracies.append(float((pred == test["target"].to_numpy()).mean()))
    return {
        "folds": len(accuracies),
        "positive_folds": int(sum(a > 0.5 for a in accuracies)),
        "mean_accuracy": float(np.mean(accuracies)),
        "median_accuracy": float(np.median(accuracies)),
    }


def compare_asset(symbol: str, external: pd.DataFrame, keep: list[str]) -> list[dict]:
    close = download_close(symbol)
    market = build_market(close)
    frame = market.join(external, how="inner")
    selected_external = apply_lagged_external(external, keep)
    frame = frame.join(selected_external, rsuffix="__selected")
    base = [c for c in MARKET_FEATURES if c in frame.columns]
    selected = [c for c in selected_external.columns if c in frame.columns]
    variants = [("V1_market_only", base), ("V2_keep_variables", base + selected)]
    results = []
    base_result = None
    for name, features in variants:
        r = evaluate_variant(frame, features)
        if name == "V1_market_only":
            base_result = r
        results.append({
            "asset": symbol,
            "variant": name,
            "features": ",".join(features),
            **r,
        })
    if base_result is not None:
        for r in results:
            r["accuracy_delta_vs_v1"] = r["mean_accuracy"] - base_result["mean_accuracy"] if pd.notna(r["mean_accuracy"]) else np.nan
            r["status"] = "PASS" if r["variant"] == "V2_keep_variables" and r["folds"] >= MIN_FOLDS and r["accuracy_delta_vs_v1"] > 0 and r["positive_folds"] >= (r["folds"] / 2) else "RESEARCH"
    return results


def main() -> None:
    print("V2 MODEL COMPARISON — RESEARCH ONLY")
    print(f"Assets: {SYMBOLS}")
    external = build_external()
    keep = load_keep_variables()
    print(f"KEEP variables loaded from scorecard: {len(keep)}")
    all_rows = []
    for symbol in SYMBOLS:
        try:
            all_rows.extend(compare_asset(symbol, external, keep))
        except Exception as exc:
            print(f"WARN {symbol}: {exc}")
    if not all_rows:
        raise RuntimeError("No assets evaluated")
    result = pd.DataFrame(all_rows)
    result.to_csv(REPORT_DIR / "model_comparison.csv", index=False)

    summary_lines = [
        "# V2 Model Comparison",
        "",
        "Research-only comparison of market-only V1-style features against variables already marked KEEP by the V2 discovery scorecard.",
        "",
        "## Rule",
        "A V2 candidate is not promoted merely because accuracy improves. It must have enough walk-forward folds and improve the baseline without relying on random splits. Final promotion still requires cost stress, robustness and an untouched holdout.",
        "",
        "## Results",
    ]
    for _, r in result[result["variant"].eq("V2_keep_variables")].iterrows():
        delta = "n/a" if pd.isna(r["accuracy_delta_vs_v1"]) else f"{r['accuracy_delta_vs_v1']:+.3%}"
        summary_lines.append(f"- {r['asset']}: OOS accuracy {r['mean_accuracy']:.3%} vs V1 delta {delta}; positive folds {int(r['positive_folds'])}/{int(r['folds'])}; status={r['status']}")
    (REPORT_DIR / "model_comparison_summary.md").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    print(result[["asset", "variant", "mean_accuracy", "accuracy_delta_vs_v1", "folds", "positive_folds", "status"]].to_string(index=False))
    print(f"Saved: {REPORT_DIR / 'model_comparison.csv'}")


if __name__ == "__main__":
    main()
