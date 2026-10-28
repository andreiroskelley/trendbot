"""
src/analysis/anomaly.py

Detects statistical anomalies (suspicious drops) using Z-Scores.
"""

import logging
import pandas as pd
from src.analysis.indicators import calculate_zscore

logger = logging.getLogger(__name__)

def is_suspicious_drop(stock_data, config: dict) -> bool:
    """
    Returns True if the current price drop is an extreme statistical anomaly.
    """
    period = config.get('period', 20)
    threshold = config.get('threshold', -3.0)
    
    if len(stock_data) < period:
        return False
        
    z_scores = calculate_zscore(stock_data['close'], period)
    current_z = z_scores.iloc[-1]
    
    if pd.isna(current_z):
        return False
        
    is_anomaly = bool(current_z <= threshold)
    
    if is_anomaly:
        logger.warning(f"🚨 Z-SCORE ANOMALY DETECTED! Z-Score: {current_z:.2f} (Threshold: {threshold})")
        
    return is_anomaly