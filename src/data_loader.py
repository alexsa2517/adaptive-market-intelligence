from __future__ import annotations

import pandas as pd
import yfinance as yf


def load_ohlcv(symbol: str = "BTC-USD", start: str = "2018-01-01", end: str | None = None) -> pd.DataFrame:
    """Download daily OHLCV data. The returned frame uses a simple DateTimeIndex."""
    df = yf.download(symbol, start=start, end=end, auto_adjust=False, progress=False)
    if df.empty:
        raise ValueError(f"No market data returned for {symbol}.")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    required = ["Open", "High", "Low", "Close", "Volume"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing OHLCV columns: {missing}")
    return df[required].dropna().sort_index()
