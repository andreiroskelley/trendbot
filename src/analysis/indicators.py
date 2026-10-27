"""
src/analysis/indicators.py

Wrapper functions around TA-Lib to calculate technical indicators.
These functions take pandas DataFrames and return pandas Series.
"""

import pandas as pd
import talib
import logging

logger = logging.getLogger(__name__)

def calculate_sma(close_prices: pd.Series, period: int) -> pd.Series:
    """
    Calculate the Simple Moving Average (SMA).
    """
    if len(close_prices) < period:
        logger.warning(f"Not enough data to calculate SMA. Need {period}, got {len(close_prices)}")
        return pd.Series(index=close_prices.index, dtype=float)
        
    return talib.SMA(close_prices, timeperiod=period)

def calculate_rsi(close_prices: pd.Series, period: int = 14) -> pd.Series:
    """
    Calculate the Relative Strength Index (RSI).
    """
    if len(close_prices) < period:
        logger.warning(f"Not enough data to calculate RSI. Need {period}, got {len(close_prices)}")
        return pd.Series(index=close_prices.index, dtype=float)

    return talib.RSI(close_prices, timeperiod=period)

def calculate_adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """
    Calculate the Average Directional Index (ADX).
    Requires High, Low, and Close prices.
    """
    if len(close) < (period * 2): # ADX requires more data to smooth properly
        logger.warning(f"Not enough data to calculate ADX. Need > {period * 2}, got {len(close)}")
        return pd.Series(index=close.index, dtype=float)

    return talib.ADX(high, low, close, timeperiod=period)

def calculate_relative_strength(stock_close: pd.Series, market_close: pd.Series, period: int = 20) -> pd.Series:
    """
    Calculate Relative Strength (RS) of a stock vs. the broader market (e.g., SPY).
    RS = (Stock Price / Market Price) * 100
    A rising RS line means the stock is outperforming the market.
    """
    # Align the two series on their dates to ensure we are comparing the same days
    aligned = pd.concat([stock_close, market_close], axis=1, join='inner')
    aligned.columns = ['stock', 'market']
    
    if len(aligned) < period:
        logger.warning(f"Not enough aligned data to calculate RS.")
        return pd.Series(index=stock_close.index, dtype=float)

    # Calculate the raw ratio
    rs_ratio = (aligned['stock'] / aligned['market']) * 100
    
    # Reindex back to the original stock index to maintain alignment
    return rs_ratio.reindex(stock_close.index)