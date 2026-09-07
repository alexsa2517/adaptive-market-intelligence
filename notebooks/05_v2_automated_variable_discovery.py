"""V2 Automated Variable Discovery Engine.

Research only. All variables tested in the previous V2 discovery run failed
the configured statistical/OOS gate. They are therefore removed from the
active candidate pool.

The locked V1.12 model is not modified.
"""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports" / "v2"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

SYMBOLS = [s.strip() for s in os.getenv("V2_SYMBOLS", "AAPL,NVDA,MSFT,AMZN,TSLA,XOM,JPM,GLD,SPY,QQQ").split(",") if s.strip()]

# All previously tested external variables failed the discovery gate.
# Keep the active candidate pool empty until new variables are researched.
CROSS_ASSETS: dict[str, str] = {}


def write_empty_reports() -> None:
    columns = [
        "asset", "feature", "lag", "pearson_r", "pearson_p",
        "spearman_r", "spearman_p", "n", "oos_delta_accuracy",
        "oos_median_delta", "oos_folds", "oos_positive_folds",
        "pearson_q", "oos_positive_rate", "status", "evidence_score",
    ]
    pd.DataFrame(columns=columns).to_csv(REPORT_DIR / "variable_scorecard.csv", index=False)
    pd.DataFrame(columns=columns).to_csv(REPORT_DIR / "removed_variables.csv", index=False)
    pd.DataFrame(columns=columns).to_csv(REPORT_DIR / "economic_fingerprint.csv", index=False)

    lines = [
        "# V2 Automated Variable Discovery",
        "",
        "Research-only. V2 results do not modify the locked V1.12 model.",
        "",
        f"Assets configured: {', '.join(SYMBOLS)}",
        "",
        "## Active external variables",
        "None.",
        "",
        "## Previous discovery result",
        "All previously tested external variables failed the configured discovery gate.",
        "They have been removed from the active candidate pool.",
        "",
        "## Rule",
        "A new variable may be added only as a research candidate and must pass statistical screening, walk-forward OOS testing, cost testing, robustness testing, and an untouched holdout before promotion.",
    ]
    (REPORT_DIR / "v2_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    print("V2 AUTOMATED VARIABLE DISCOVERY — ACTIVE CANDIDATE POOL EMPTY")
    print("All previously tested external variables failed the discovery gate and have been removed.")
    write_empty_reports()
    print(f"Reports written to {REPORT_DIR}")


if __name__ == "__main__":
    main()
