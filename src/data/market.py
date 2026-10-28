"""
src/data/market.py
Real market data provider using Alpaca API (Supports both Stocks and Crypto).
"""

import os
import logging
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
from alpaca.data.historical import StockHistoricalDataClient, CryptoHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, CryptoBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.client import TradingClient

# Load .env variables
load_dotenv()

logger = logging.getLogger(__name__)

# Initialize the Alpaca clients
ALPACA_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET = os.getenv("ALPACA_SECRET_KEY")

if not ALPACA_KEY or not ALPACA_SECRET:
    logger.error("Alpaca API keys not found in .env file!")

data_client = StockHistoricalDataClient(ALPACA_KEY, ALPACA_SECRET)
crypto_client = CryptoHistoricalDataClient(ALPACA_KEY, ALPACA_SECRET)
trading_client = TradingClient(ALPACA_KEY, ALPACA_SECRET, paper=True)

def _fetch_bars(symbol: str, days_back: int = 150) -> pd.DataFrame:
    """Helper function to fetch historical bars from Alpaca (Stocks or Crypto)."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)

    # Check if it's a crypto pair (contains a slash)
    is_crypto = "/" in symbol

    try:
        if is_crypto:
            request_params = CryptoBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame.Day,
                start=start_date,
                end=end_date
            )
            bars = crypto_client.get_crypto_bars(request_params)
        else:
            request_params = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame.Day,
                start=start_date,
                end=end_date,
                feed="iex" # Use IEX feed for free tier
            )
            bars = data_client.get_stock_bars(request_params)
        
        # Convert to pandas DataFrame
        df = bars.df
        
        if df.empty:
            logger.warning(f"No data returned for {symbol}")
            return pd.DataFrame()

        # Drop the multi-index level if it exists
        if isinstance(df.index, pd.MultiIndex):
            df = df.xs(symbol, level='symbol')
            
        df.index.name = 'timestamp'
        
        # We only need high, low, close, volume
        return df[['high', 'low', 'close', 'volume']]
        
    except Exception as e:
        logger.error(f"Failed to fetch data for {symbol}: {e}")
        return pd.DataFrame()

def get_market_data(ticker: str) -> pd.DataFrame:
    """Fetches the last 100 days of daily data for a given ticker (Stock or Crypto)."""
    logger.info(f"Fetching market data for {ticker}...")
    return _fetch_bars(ticker)

def get_market_benchmark() -> pd.DataFrame:
    """Fetches the benchmark for Relative Strength comparison. Using BTC/USD for crypto testing."""
    logger.info("Fetching market benchmark (BTC/USD)...")
    return _fetch_bars("BTC/USD")

def get_account_capital() -> float:
    """Fetches the real buying power from your Alpaca Paper account."""
    try:
        account = trading_client.get_account()
        return float(account.buying_power)
    except Exception as e:
        logger.error(f"Failed to fetch account balance: {e}")
        return 0.0