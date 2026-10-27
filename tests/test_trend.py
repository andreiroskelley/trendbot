"""
tests/test_trend.py

Unit tests for the trend detection logic.
"""

import pytest
import pandas as pd
import numpy as np
from src.analysis.trend import is_uptrend

@pytest.fixture
def config():
    """Mock configuration from settings.yaml."""
    return {
        'sma_short': 20,
        'sma_long': 50,
        'adx_period': 14,
        'adx_threshold': 20,
        'rel_strength_days': 20
    }

@pytest.fixture
def uptrend_data():
    """Generates 100 days of data in a clear, strong uptrend."""
    dates = pd.date_range(start="2023-01-01", periods=100, freq="D")
    # Straight line up
    close = np.linspace(100, 200, 100) 
    return pd.DataFrame({
        'high': close + 2,
        'low': close - 2,
        'close': close
    }, index=dates)

@pytest.fixture
def downtrend_data():
    """Generates 100 days of data in a clear downtrend."""
    dates = pd.date_range(start="2023-01-01", periods=100, freq="D")
    # Straight line down
    close = np.linspace(200, 100, 100)
    return pd.DataFrame({
        'high': close + 2,
        'low': close - 2,
        'close': close
    }, index=dates)

@pytest.fixture
def flat_market_data():
    """Generates 100 days of flat market data (e.g., SPY going nowhere)."""
    dates = pd.date_range(start="2023-01-01", periods=100, freq="D")
    close = np.full(100, 400.0) # Flat at 400
    return pd.DataFrame({'close': close}, index=dates)

def test_is_uptrend_true(uptrend_data, flat_market_data, config):
    """A strongly rising stock vs a flat market should be an uptrend."""
    result = is_uptrend(uptrend_data, flat_market_data, config)
    assert result is True

def test_is_uptrend_false_downtrend(downtrend_data, flat_market_data, config):
    """A falling stock should never be an uptrend."""
    result = is_uptrend(downtrend_data, flat_market_data, config)
    assert result is False

def test_is_uptrend_false_weak_adx(config):
    """A stock moving sideways with low volatility should fail the ADX check."""
    dates = pd.date_range(start="2023-01-01", periods=100, freq="D")
    
    # Create a tiny, random chop (prices moving between 100.0 and 100.1)
    np.random.seed(42)
    close = 100 + np.random.uniform(-0.1, 0.1, size=100)
    
    stock_data = pd.DataFrame({
        'high': close + 0.05,
        'low': close - 0.05,
        'close': close
    }, index=dates)
    
    market_data = pd.DataFrame({'close': np.full(100, 400.0)}, index=dates)
    
    # The price is going nowhere, so ADX will be very low.
    result = is_uptrend(stock_data, market_data, config)
    assert result is False