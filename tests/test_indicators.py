"""
tests/test_indicators.py

Unit tests for the indicator wrappers.
We use synthetic (fake) data here to ensure the math is outputting 
the correct types and lengths, without relying on live market data.
"""

import pytest
import pandas as pd
import numpy as np
from src.analysis.indicators import calculate_sma, calculate_rsi, calculate_adx, calculate_relative_strength

@pytest.fixture
def sample_price_data():
    """
    Generates 100 days of fake OHLCV data for testing.
    """
    np.random.seed(42) # Ensures the "random" data is the same every time we run tests
    dates = pd.date_range(start="2023-01-01", periods=100, freq="D")
    
    # Generate a random walk for close prices starting at 100
    close = np.random.normal(loc=0, scale=1, size=100).cumsum() + 100
    
    # Create fake High and Low based on the close
    high = close + np.random.uniform(0.5, 2.0, size=100)
    low = close - np.random.uniform(0.5, 2.0, size=100)
    
    return pd.DataFrame({
        'open': close - np.random.uniform(0, 1, size=100),
        'high': high,
        'low': low,
        'close': close,
        'volume': np.random.randint(1000, 5000, size=100)
    }, index=dates)

@pytest.fixture
def sample_market_data():
    """
    Generates 100 days of fake market data (e.g., SPY) for RS testing.
    """
    np.random.seed(99)
    dates = pd.date_range(start="2023-01-01", periods=100, freq="D")
    close = np.random.normal(loc=0, scale=0.5, size=100).cumsum() + 400
    return pd.Series(close, index=dates, name="SPY_Close")


def test_sma(sample_price_data):
    sma = calculate_sma(sample_price_data['close'], period=20)
    
    assert len(sma) == len(sample_price_data)
    # First 19 values should be NaN because SMA needs 20 periods to calculate
    assert pd.isna(sma.iloc[18]) 
    # The 20th value (index 19) should be a valid number
    assert not pd.isna(sma.iloc[19])
    assert isinstance(sma.iloc[19], (float, np.floating))

def test_rsi(sample_price_data):
    rsi = calculate_rsi(sample_price_data['close'], period=14)
    
    assert len(rsi) == len(sample_price_data)
    assert pd.isna(rsi.iloc[13])
    assert not pd.isna(rsi.iloc[14])
    
    # RSI must always be between 0 and 100
    valid_rsi = rsi.dropna()
    assert (valid_rsi >= 0).all()
    assert (valid_rsi <= 100).all()

def test_adx(sample_price_data):
    adx = calculate_adx(
        sample_price_data['high'], 
        sample_price_data['low'], 
        sample_price_data['close'], 
        period=14
    )
    
    assert len(adx) == len(sample_price_data)
    assert pd.isna(adx.iloc[0])
    assert not pd.isna(adx.iloc[40]) # ADX needs time to stabilize

def test_relative_strength(sample_price_data, sample_market_data):
    rs = calculate_relative_strength(
        sample_price_data['close'], 
        sample_market_data, 
        period=20
    )
    
    assert len(rs) == len(sample_price_data)
    
    # Calculate manual RS for the first valid day to check math
    # (Stock Close / Market Close) * 100
    day_0_stock = sample_price_data['close'].iloc[0]
    day_0_market = sample_market_data.iloc[0]
    expected_rs = (day_0_stock / day_0_market) * 100
    
    assert pytest.approx(rs.iloc[0], rel=1e-4) == expected_rs