"""
src/analysis/trend.py

Evaluates whether a stock is currently in a valid uptrend.
Uses moving averages, ADX, and relative strength vs. the market.
"""

import pandas as pd
import logging
from src.analysis.indicators import calculate_sma, calculate_adx, calculate_relative_strength

logger = logging.getLogger(__name__)

def is_uptrend(stock_data: pd.DataFrame, market_data: pd.DataFrame, config: dict, ticker: str = "") -> bool:
    """
    Determines if a stock is in an uptrend based on the provided configuration.
    
    :param stock_data: DataFrame with 'high', 'low', 'close' for the stock.
    :param market_data: DataFrame with 'close' for the broader market (e.g., SPY).
    :param config: The 'trend' dictionary from settings.yaml.
    :param ticker: The ticker symbol (used to bypass RS for Bitcoin).
    :return: True if in an uptrend, False otherwise.
    """
    if len(stock_data) < config.get('sma_long', 50):
        logger.warning("Not enough data to evaluate trend.")
        return False

    close = stock_data['close']
    high = stock_data['high']
    low = stock_data['low']

    # 1. Moving Averages (Short > Long)
    sma_short = calculate_sma(close, config['sma_short']).iloc[-1]
    sma_long = calculate_sma(close, config['sma_long']).iloc[-1]
    
    if pd.isna(sma_short) or pd.isna(sma_long):
        return False
        
    ma_trend = sma_short > sma_long

    # 2. ADX (Trend Strength)
    adx_series = calculate_adx(high, low, close, config['adx_period'])
    current_adx = adx_series.iloc[-1]
    
    if pd.isna(current_adx):
        return False
        
    adx_trend = current_adx > config['adx_threshold']

    # 3. Relative Strength (Stock vs Market)
    # Bitcoin is the crypto benchmark. Comparing it to itself yields a flat line (RS=100).
    # For crypto, we bypass RS and rely purely on MA + ADX.
    if ticker == "BTC/USD":
        rs_trend = True
    else:
        rs_series = calculate_relative_strength(close, market_data['close'], config['rel_strength_days'])
        
        if len(rs_series.dropna()) > config['rel_strength_days']:
            rs_now = rs_series.iloc[-1]
            rs_past = rs_series.iloc[-(config['rel_strength_days'] + 1)]
            rs_trend = rs_now > rs_past
        else:
            rs_trend = False

    # Log the breakdown for debugging
    rs_display = "BYPASSED" if ticker == "BTC/USD" else str(rs_trend)
    logger.info(f"Trend Check -> MA: {ma_trend}, ADX: {adx_trend} ({current_adx:.2f}), RS: {rs_display}")

    # Force standard python boolean to prevent NumPy type errors
    final_result = bool(ma_trend and adx_trend and rs_trend)
    
    return final_result