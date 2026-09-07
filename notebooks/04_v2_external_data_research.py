"""V2 external-data research scaffold.

PROVE BEFORE TRADE

This script is intentionally research-only. It does not modify the locked
V1.12 forward model and does not promote news/macro features automatically.

Run after collecting timestamped datasets. Expected columns are documented in
`docs/v2_feature_spec.md` and `src/v2_external_data.py`.
"""

from pathlib import Path

import pandas as pd

from src.v2_external_data import (
    add_cross_asset_features,
    add_macro_release_features,
    build_news_daily_features,
)


DATA_DIR = Path("data/v2")


def main() -> None:
    print("V2 EXTERNAL DATA RESEARCH")
    print("Status: RESEARCH ONLY")
    print("Locked V1.12 forward model: UNCHANGED")

    market_path = DATA_DIR / "market.csv"
    news_path = DATA_DIR / "news.csv"
    macro_path = DATA_DIR / "macro_releases.csv"

    if not market_path.exists():
        print(f"Missing {market_path}; add timestamped market data before running.")
        return

    market = pd.read_csv(market_path, parse_dates=["Date"], index_col="Date")
    print(f"Market rows: {len(market):,}")

    if news_path.exists():
        news = pd.read_csv(news_path)
        news_features = build_news_daily_features(news)
        print(f"News feature rows: {len(news_features):,}")
    else:
        print("News data: not loaded yet")

    if macro_path.exists():
        macro = pd.read_csv(macro_path, parse_dates=["release_time"])
        print(f"Macro release rows: {len(macro):,}")
    else:
        print("Macro release data: not loaded yet")

    print("Next gate: compare V1 vs V2 using identical walk-forward windows.")
    print("No holdout promotion is performed by this script.")


if __name__ == "__main__":
    main()
