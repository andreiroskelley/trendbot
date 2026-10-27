"""
src/signals/pullback.py

Detects high-quality pullback entries within an established uptrend.
"""

import pandas as pd
import logging
from src.analysis.indicators import calculate_rsi, calculate_sma

logger = logging.getLogger(__name__)

def check_pullback_signal(stock_data: pd.DataFrame, config: dict) -> bool:
    """
    Checks if the stock has pulled back to a support level in an uptrend.
    
    :param stock_data: DataFrame with 'high', 'low', 'close' for the stock.
    :param config: The 'signals.pullback' dictionary from settings.yaml.
    :return: True if a pullback entry is triggered, False otherwise.
    """
    if len(stock_data) < config['rsi_period']:
        return False

    close = stock_data['close']
    
    # 1. Calculate RSI
    rsi_series = calculate_rsi(close, config['rsi_period'])
    current_rsi = rsi_series.iloc[-1]
    
    if pd.isna(current_rsi):
        return False
        
    # 2. Calculate SMA (Support Level)
    # We use a standard 20-day SMA as the support line for the pullback
    sma_series = calculate_sma(close, 20)
    current_sma = sma_series.iloc[-1]
    current_price = close.iloc[-1]
    
    if pd.isna(current_sma):
        return False

    # 3. Check conditions
    # Condition A: RSI is oversold (dipping)
    is_rsi_dip = current_rsi <= config['rsi_threshold']
    
    # Condition B: Price is near the SMA (within the support proximity percentage)
    proximity_pct = config['support_proximity']
    distance_to_sma = abs(current_price - current_sma) / current_sma
    is_near_support = distance_to_sma <= proximity_pct

    # Trigger if both are true
    signal_triggered = bool(is_rsi_dip and is_near_support)

    if signal_triggered:
        logger.info(f"Pullback Signal Triggered! RSI: {current_rsi:.2f}, Price: {current_price:.2f}, SMA: {current_sma:.2f}")
    else:
        logger.debug(f"No pullback. RSI: {current_rsi:.2f} (Needs <={config['rsi_threshold']}), Distance to SMA: {distance_to_sma*100:.2f}% (Needs <={proximity_pct*100}%)")

    return signal_triggered