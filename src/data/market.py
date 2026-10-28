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

# Benchmarks per asset class. Stocks compare to SPY (04:00 UTC daily bars),
# crypto compares to BTC/USD (00:00 UTC). Mixing them yields zero aligned
# timestamps and permanently breaks Relative Strength.
BENCHMARKS = {
    "stock": "SPY",
    "crypto": "BTC/USD",
}


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


def get_market_benchmark(ticker: str) -> pd.DataFrame:
    """
    Fetches the benchmark for Relative Strength comparison.
    Equities are compared to SPY; crypto is compared to BTC/USD.
    Mixing the two breaks timestamp alignment (stocks 04:00 UTC, crypto 00:00 UTC).
    """
    asset_class = "crypto" if "/" in ticker else "stock"
    benchmark = BENCHMARKS[asset_class]
    logger.info(f"Fetching market benchmark ({benchmark}) for {ticker}...")
    return _fetch_bars(benchmark)


def get_account_capital() -> float:
    """Fetches the real buying power from your Alpaca Paper account."""
    try:
        account = trading_client.get_account()
        return float(account.buying_power)
    except Exception as e:
        logger.error(f"Failed to fetch account balance: {e}")
        return 0.0


def get_account_equity() -> float:
    """Fetches total account equity (cash + positions) from Alpaca."""
    try:
        account = trading_client.get_account()
        return float(account.equity)
    except Exception as e:
        logger.error(f"Failed to fetch account equity: {e}")
        return 0.0


def is_market_open() -> bool:
    """
    Returns True if the US equity market is currently open, per Alpaca's clock.
    This is the same source of truth Alpaca uses to accept/reject orders,
    so it correctly handles holidays and half-days.
    Fails safe: returns False on API error so we never queue a stock order while closed.
    """
    try:
        clock = trading_client.get_clock()
        return bool(clock.is_open)
    except Exception as e:
        logger.error(f"Failed to fetch market clock: {e}")
        return False