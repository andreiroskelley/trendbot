"""
tests/test_signals.py

Unit tests for entry signals.
"""

import pytest
import pandas as pd
import numpy as np
from src.signals.pullback import check_pullback_signal
from src.signals.breakout import check_breakout_signal

# ==========================================
# Pullback Tests
# ==========================================

@pytest.fixture
def pullback_config():
    return {
        'rsi_period': 14,
        'rsi_threshold': 40,
        'support_proximity': 0.02 # 2%
    }

def test_pullback_true(pullback_config):
    """Stock has a gentle pullback near the SMA and RSI is below 40."""
    # 70 days of uptrend, then a sharper 30-day drop
    close = np.concatenate([
        np.linspace(100, 120, 70),  # Strong uptrend
        np.linspace(120, 116, 30)   # Pullback that pushes RSI below 40
    ])
    
    stock_data = pd.DataFrame({
        'high': close + 1, 'low': close - 1, 'close': close
    })
    
    assert check_pullback_signal(stock_data, pullback_config) is True

def test_pullback_false_no_dip(pullback_config):
    """Stock is going straight up. RSI will be high, price is far from SMA."""
    close = np.linspace(100, 150, 100) # Straight line up
    stock_data = pd.DataFrame({
        'high': close + 1, 'low': close - 1, 'close': close
    })
    assert check_pullback_signal(stock_data, pullback_config) is False

# ==========================================
# Breakout Tests
# ==========================================

@pytest.fixture
def breakout_config():
    return {
        'lookback_period': 20,
        'volume_multiplier': 1.5
    }

def test_breakout_true(breakout_config):
    """Price makes a new 20-day high on 2x volume."""
    close = np.linspace(100, 120, 100)
    volume = np.full(100, 1000) # Average volume is 1000
    
    # Overwrite the last day to simulate a breakout
    close[-1] = 130 # New high
    volume[-1] = 2000 # 2x volume (above the 1.5x requirement)
    
    stock_data = pd.DataFrame({
        'high': close + 1, 'low': close - 1, 'close': close, 'volume': volume
    })
    
    assert check_breakout_signal(stock_data, breakout_config) is True

def test_breakout_false_low_volume(breakout_config):
    """Price makes a new high, but volume is average."""
    close = np.linspace(100, 120, 100)
    volume = np.full(100, 1000)
    
    close[-1] = 130 
    volume[-1] = 1000 # Only 1x volume (fails the 1.5x requirement)
    
    stock_data = pd.DataFrame({
        'high': close + 1, 'low': close - 1, 'close': close, 'volume': volume
    })
    
    assert check_breakout_signal(stock_data, breakout_config) is False