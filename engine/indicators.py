#!/usr/bin/env python3
"""Deterministic indicator / feature transforms.

Every function takes a pandas Series/DataFrame indexed by UTC hour and returns a
series aligned to the same index. The value at row T is computed from data up to
AND INCLUDING T. The backtest engine shifts features by one hour before any
decision uses them, so a rule evaluated at hour T only ever sees data strictly
before T (see engine/backtest.py and the no-lookahead guard).

All transforms are pure and order-independent given the same input → determinism.
"""
import numpy as np
import pandas as pd

HOURS_PER_YEAR = 24 * 365


def sma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window, min_periods=window).mean()


def delta(series: pd.Series, window: int) -> pd.Series:
    """Change over `window` hours: x[T] - x[T-window]."""
    return series - series.shift(window)


def realized_vol(series: pd.Series, window: int) -> pd.Series:
    """Annualized realized volatility of hourly log returns over `window`."""
    logret = np.log(series / series.shift(1))
    return logret.rolling(window, min_periods=window).std() * np.sqrt(HOURS_PER_YEAR)


def percentile_rank(series: pd.Series, window: int) -> pd.Series:
    """Rolling percentile (0..100) of the latest value within the trailing window.

    100 = current value is the highest in the window; 0 = the lowest.
    """
    def _rank(x):
        last = x[-1]
        return 100.0 * (np.sum(x <= last) - 1) / (len(x) - 1) if len(x) > 1 else 50.0
    return series.rolling(window, min_periods=window).apply(_rank, raw=True)


def breadth(close_panel: pd.DataFrame, threshold_window: int) -> pd.Series:
    """Fraction (0..1) of assets whose close is above their own trailing SMA.

    The signature market-internal feature: market breadth across the universe.
    """
    above = pd.DataFrame(index=close_panel.index)
    for col in close_panel.columns:
        m = close_panel[col].rolling(threshold_window, min_periods=threshold_window).mean()
        above[col] = (close_panel[col] > m).astype(float)
    # only count assets that have enough history (non-NaN sma) at each row
    valid = close_panel.rolling(threshold_window, min_periods=threshold_window).mean().notna()
    counts = valid.sum(axis=1)
    return (above.where(valid).sum(axis=1) / counts.replace(0, np.nan))
