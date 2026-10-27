"""
src/data/market.py
Real market data provider using Alpaca API.
"""

import os
import logging
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

# Load .env variables
load_dotenv()

logger = logging.getLogger(__name__)

# Initialize the Alpaca client
ALPACA_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET = os.getenv("ALPACA_SECRET_KEY")

if not ALPACA_KEY or not ALPACA_SECRET:
    logger.error("Alpaca API keys not found in .env file!")

data_client = StockHistoricalDataClient(ALPACA_KEY, ALPACA_SECRET)

def _fetch_bars(symbol: str, days_back: int = 150) -> pd.DataFrame:
    """Helper function to fetch historical bars from Alpaca."""
    # Calculate start date
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)

    request_params = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=TimeFrame.Day,
        start=start_date,
        end=end_date,
        feed="iex" # Use IEX feed for free tier
    )

    try:
        bars = data_client.get_stock_bars(request_params)
        
        # The SDK returns a specialized object. Let's convert it to a pandas DataFrame.
        df = bars.df
        
        if df.empty:
            logger.warning(f"No data returned for {symbol}")
            return pd.DataFrame()

        # If the symbol is the index level, drop it so we have standard columns
        if isinstance(df.index, pd.MultiIndex):
            df = df.xs(symbol, level='symbol')
            
        # Alpaca returns 'timestamp' as the index. Let's ensure standard column names.
        df.index.name = 'timestamp'
        
        # We only need high, low, close, volume
        return df[['high', 'low', 'close', 'volume']]
        
    except Exception as e:
        logger.error(f"Failed to fetch data for {symbol}: {e}")
        return pd.DataFrame()

def get_market_data(ticker: str) -> pd.DataFrame:
    """Fetches the last 100 days of daily data for a given ticker."""
    logger.info(f"Fetching market data for {ticker}...")
    return _fetch_bars(ticker)

def get_market_benchmark() -> pd.DataFrame:
    """Fetches the SPY benchmark for Relative Strength comparison."""
    logger.info("Fetching market benchmark (SPY)...")
    return _fetch_bars("SPY")

from alpaca.trading.client import TradingClient

def get_account_capital() -> float:
    """Fetches the real buying power from your Alpaca Paper account."""
    try:
        trading_client = TradingClient(ALPACA_KEY, ALPACA_SECRET, paper=True)
        account = trading_client.get_account()
        return float(account.buying_power)
    except Exception as e:
        logger.error(f"Failed to fetch account balance: {e}")
        return 0.0