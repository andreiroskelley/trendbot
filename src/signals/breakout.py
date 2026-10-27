"""
src/signals/breakout.py

Detects momentum breakout entries (price making new highs on high volume).
"""

import pandas as pd
import logging

logger = logging.getLogger(__name__)

def check_breakout_signal(stock_data: pd.DataFrame, config: dict) -> bool:
    """
    Checks if the stock has broken out to a new high with strong volume.
    
    :param stock_data: DataFrame with 'high', 'low', 'close', 'volume' for the stock.
    :param config: The 'signals.breakout' dictionary from settings.yaml.
    :return: True if a breakout entry is triggered, False otherwise.
    """
    lookback = config['lookback_period']
    vol_multiplier = config['volume_multiplier']

    if len(stock_data) < (lookback + 1):
        return False

    close = stock_data['close']
    volume = stock_data['volume']
    
    # Current data
    current_close = close.iloc[-1]
    current_volume = volume.iloc[-1]

    # 1. Check for 20-day High
    # We look at the previous 20 days (excluding today) and see if today's close is higher
    recent_high = close.iloc[-(lookback + 1):-1].max()
    is_new_high = bool(current_close > recent_high)

    # 2. Check Volume
    # Calculate the average volume over the last 20 days (excluding today)
    avg_volume = volume.iloc[-(lookback + 1):-1].mean()
    is_high_volume = bool(current_volume > (avg_volume * vol_multiplier))

    signal_triggered = bool(is_new_high and is_high_volume)

    if signal_triggered:
        logger.info(f"Breakout Signal Triggered! Close: {current_close:.2f} (High: {recent_high:.2f}), Volume: {current_volume} (Avg: {avg_volume:.0f})")
    else:
        logger.debug(f"No breakout. New High: {is_new_high}, High Vol: {is_high_volume}")

    return signal_triggered