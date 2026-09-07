from __future__ import annotations

import numpy as np
import pandas as pd


def calculate_backtest(
    df: pd.DataFrame,
    signal_column: str,
    fee: float = 0.0010,
    slippage: float = 0.0005,
) -> pd.DataFrame:
    """Backtest a long/flat signal with close-to-close execution.

    signal(t) is assumed to be executable at the close of t and captures the
    return from close(t) to close(t+1). Each position change pays one fee plus
    one slippage charge. For a complete entry/exit cycle this is approximately
    2 * (fee + slippage).
    """
    data = df.copy()
    data["signal"] = data[signal_column].astype(int)
    data["market_return"] = data["close"].shift(-1) / data["close"] - 1

    data["position_change"] = data["signal"].diff().abs()
    data.loc[data.index[0], "position_change"] = abs(
        data.loc[data.index[0], "signal"]
    )

    data["gross_return"] = data["signal"] * data["market_return"]
    data["transaction_cost"] = data["position_change"] * (
        fee + slippage
    )
    data["net_return"] = (
        data["gross_return"] - data["transaction_cost"]
    )

    # The final row has no next-day market return and cannot be evaluated.
    data = data.iloc[:-1].copy()
    data["equity"] = (1 + data["net_return"]).cumprod()
    running_max = data["equity"].cummax()
    data["drawdown"] = data["equity"] / running_max - 1

    return data


def summarize_backtest(bt: pd.DataFrame) -> dict:
    """Return core long/flat performance metrics."""
    if bt.empty:
        return {
            "Return": np.nan,
            "Max DD": np.nan,
            "Sharpe": np.nan,
            "Profit Factor": np.nan,
            "Win Rate": np.nan,
            "Exposure": np.nan,
            "Position Changes": 0,
        }

    total_return = bt["equity"].iloc[-1] - 1
    max_dd = bt["drawdown"].min()
    daily_std = bt["net_return"].std()
    sharpe = (
        np.sqrt(365) * bt["net_return"].mean() / daily_std
        if daily_std > 0
        else np.nan
    )

    active = bt[bt["signal"] == 1]
    exposure = len(active) / len(bt)
    win_rate = (
        (active["market_return"] > 0).mean()
        if len(active) > 0
        else np.nan
    )

    gross_profit = bt.loc[
        bt["net_return"] > 0, "net_return"
    ].sum()
    gross_loss = abs(
        bt.loc[bt["net_return"] < 0, "net_return"].sum()
    )
    profit_factor = (
        gross_profit / gross_loss
        if gross_loss > 0
        else np.nan
    )

    return {
        "Return": total_return,
        "Max DD": max_dd,
        "Sharpe": sharpe,
        "Profit Factor": profit_factor,
        "Win Rate": win_rate,
        "Exposure": exposure,
        "Position Changes": bt["position_change"].sum(),
    }
