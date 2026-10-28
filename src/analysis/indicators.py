"""
src/analysis/indicators.py

Wrapper functions around TA-Lib to calculate technical indicators.
These functions take pandas DataFrames and return pandas Series.
"""

import pandas as pd
import numpy as np
import talib
import logging

logger = logging.getLogger(__name__)

def calculate_sma(close_prices: pd.Series, period: int) -> pd.Series:
    """Calculate the Simple Moving Average (SMA)."""
    if len(close_prices) < period:
        logger.warning(f"Not enough data to calculate SMA. Need {period}, got {len(close_prices)}")
        return pd.Series(index=close_prices.index, dtype=float)
        
    return talib.SMA(close_prices, timeperiod=period)

def calculate_rsi(close_prices: pd.Series, period: int = 14) -> pd.Series:
    """Calculate the Relative Strength Index (RSI)."""
    if len(close_prices) < period:
        logger.warning(f"Not enough data to calculate RSI. Need {period}, got {len(close_prices)}")
        return pd.Series(index=close_prices.index, dtype=float)

    return talib.RSI(close_prices, timeperiod=period)

def calculate_adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Calculate the Average Directional Index (ADX)."""
    if len(close) < (period * 2):
        logger.warning(f"Not enough data to calculate ADX. Need > {period * 2}, got {len(close)}")
        return pd.Series(index=close.index, dtype=float)

    return talib.ADX(high, low, close, timeperiod=period)

def calculate_relative_strength(stock_close: pd.Series, market_close: pd.Series, period: int = 20) -> pd.Series:
    """Calculate Relative Strength (RS) of a stock vs. the broader market."""
    aligned = pd.concat([stock_close, market_close], axis=1, join='inner')
    aligned.columns = ['stock', 'market']

    if len(aligned) < period:
        logger.warning(
            f"Not enough aligned data for RS: stock={len(stock_close)} bars, "
            f"market={len(market_close)} bars, aligned={len(aligned)}, need={period}."
        )
        return pd.Series(index=stock_close.index, dtype=float)

    rs_ratio = (aligned['stock'] / aligned['market']) * 100
    return rs_ratio.reindex(stock_close.index)

def calculate_zscore(close_prices: pd.Series, period: int = 20) -> pd.Series:
    """
    Calculates the Z-Score of the price. 
    Measures how many standard deviations the current price is from the rolling mean.
    A Z-Score < -3 indicates a statistically significant, abnormal drop.
    """
    if len(close_prices) < period:
        return pd.Series(index=close_prices.index, dtype=float)
        
    rolling_mean = close_prices.rolling(window=period).mean()
    rolling_std = close_prices.rolling(window=period).std()
    
    # Prevent division by zero if the stock is perfectly flat
    z_score = (close_prices - rolling_mean) / rolling_std.replace(0, np.nan)
    
    return z_score