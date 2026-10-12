#!/usr/bin/env python3
"""Audit a CSV OHLCV file before model training or backtesting.

Examples:
  python scripts/audit_ohlcv.py data.csv
  python scripts/audit_ohlcv.py data.csv --timestamp-col timestamp --expected-interval 1D
  python scripts/audit_ohlcv.py data.csv --json-out reports/data_audit.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ALIASES = {
    "timestamp": ("timestamp", "time", "datetime", "date", "open_time"),
    "open": ("open",),
    "high": ("high",),
    "low": ("low",),
    "close": ("close",),
    "volume": ("volume", "vol"),
}


def resolve_column(columns: list[str], candidates: tuple[str, ...]) -> str | None:
    lookup = {str(col).strip().lower(): str(col) for col in columns}
    for candidate in candidates:
        if candidate in lookup:
            return lookup[candidate]
    return None


def audit_csv(path: Path, timestamp_col: str | None = None,
              expected_interval: str | None = None) -> dict:
    if not path.is_file():
        raise FileNotFoundError(f"CSV file not found: {path}")

    raw = pd.read_csv(path)
    if raw.empty:
        raise ValueError("CSV contains no data rows.")

    resolved: dict[str, str] = {}
    for field, candidates in ALIASES.items():
        if field == "timestamp" and timestamp_col:
            if timestamp_col not in raw.columns:
                raise ValueError(
                    f"Timestamp column {timestamp_col!r} not found. "
                    f"Available columns: {list(raw.columns)}"
                )
            resolved[field] = timestamp_col
        else:
            column = resolve_column(list(raw.columns), candidates)
            if column is not None:
                resolved[field] = column

    required = ("timestamp", "open", "high", "low", "close", "volume")
    missing_columns = [field for field in required if field not in resolved]
    if missing_columns:
        raise ValueError(
            f"Missing required OHLCV columns: {missing_columns}. "
            "Supported timestamp names: timestamp, time, datetime, date, open_time."
        )

    data = pd.DataFrame(index=raw.index)
    data["timestamp"] = pd.to_datetime(raw[resolved["timestamp"]], errors="coerce", utc=True)
    for field in ("open", "high", "low", "close", "volume"):
        data[field] = pd.to_numeric(raw[resolved[field]], errors="coerce")

    timestamp_invalid = int(data["timestamp"].isna().sum())
    missing_values = {
        field: int(data[field].isna().sum())
        for field in required if data[field].isna().any()
    }
    timestamp_valid = data["timestamp"].dropna()
    duplicate_timestamps = int(timestamp_valid.duplicated(keep=False).sum())
    out_of_order = int((timestamp_valid.diff().dropna() < pd.Timedelta(0)).sum())
    duplicate_rows = int(raw.duplicated().sum())

    valid_prices = data[["open", "high", "low", "close"]].notna().all(axis=1)
    invalid_nonpositive_prices = int(
        (valid_prices & (data[["open", "high", "low", "close"]] <= 0).any(axis=1)).sum()
    )
    invalid_ohlc = int((
        valid_prices
        & (
            (data["high"] < data[["open", "close", "low"]].max(axis=1))
            | (data["low"] > data[["open", "close", "high"]].min(axis=1))
        )
    ).sum())
    negative_volume = int((data["volume"].notna() & (data["volume"] < 0)).sum())

    gap_count = None
    gap_examples: list[dict] = []
    if expected_interval:
        interval = pd.Timedelta(expected_interval)
        if interval <= pd.Timedelta(0):
            raise ValueError("--expected-interval must be a positive duration, e.g. 1D or 1h.")
        ordered = timestamp_valid.sort_values().drop_duplicates()
        differences = ordered.diff()
        gap_positions = differences[differences > interval * 1.5]
        gap_count = int(len(gap_positions))
        for idx, delta in gap_positions.head(10).items():
            gap_examples.append({
                "timestamp": ordered.loc[idx].isoformat(),
                "gap_duration": str(delta),
            })

    sorted_timestamps = timestamp_valid.sort_values()
    report = {
        "file": str(path),
        "rows": int(len(raw)),
        "columns": list(raw.columns),
        "resolved_columns": resolved,
        "first_timestamp_utc": (
            sorted_timestamps.iloc[0].isoformat() if len(sorted_timestamps) else None
        ),
        "last_timestamp_utc": (
            sorted_timestamps.iloc[-1].isoformat() if len(sorted_timestamps) else None
        ),
        "timestamp_parse_failures": timestamp_invalid,
        "missing_values_by_required_column": missing_values,
        "duplicate_timestamp_rows": duplicate_timestamps,
        "out_of_order_timestamp_steps": out_of_order,
        "duplicate_full_rows": duplicate_rows,
        "nonpositive_price_rows": invalid_nonpositive_prices,
        "invalid_ohlc_rows": invalid_ohlc,
        "negative_volume_rows": negative_volume,
        "expected_interval": expected_interval,
        "gap_count": gap_count,
        "gap_examples_first_10": gap_examples,
    }

    critical_failures = []
    if timestamp_invalid:
        critical_failures.append("timestamp_parse_failures")
    if missing_values:
        critical_failures.append("missing_values")
    if duplicate_timestamps:
        critical_failures.append("duplicate_timestamp_rows")
    if out_of_order:
        critical_failures.append("out_of_order_timestamp_steps")
    if invalid_nonpositive_prices:
        critical_failures.append("nonpositive_price_rows")
    if invalid_ohlc:
        critical_failures.append("invalid_ohlc_rows")
    if negative_volume:
        critical_failures.append("negative_volume_rows")
    if gap_count:
        critical_failures.append("time_gaps")
    report["gate"] = "FAIL" if critical_failures else "PASS"
    report["critical_failures"] = critical_failures
    report["note"] = (
        "PASS means only that these structural checks passed; it does not prove "
        "predictive edge, absence of all data leakage, or profitability."
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_path", type=Path, help="Path to OHLCV CSV file")
    parser.add_argument("--timestamp-col", help="Explicit timestamp column name")
    parser.add_argument(
        "--expected-interval",
        help="Optional candle interval, e.g. 1D, 1h, 15min; gaps are checked only when set",
    )
    parser.add_argument("--json-out", type=Path, help="Optional path to save the JSON report")
    args = parser.parse_args()

    try:
        report = audit_csv(args.csv_path, args.timestamp_col, args.expected_interval)
    except (OSError, ValueError, pd.errors.ParserError) as exc:
        print(f"AUDIT ERROR: {exc}", file=sys.stderr)
        return 2

    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    print(rendered)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(rendered + "\n", encoding="utf-8")
        print(f"\nReport saved to: {args.json_out}")
    return 0 if report["gate"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
