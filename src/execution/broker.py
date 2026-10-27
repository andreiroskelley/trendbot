"""
src/execution/broker.py
Handles order execution via Alpaca.
"""

import os
import logging
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

load_dotenv()
logger = logging.getLogger(__name__)

ALPACA_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET = os.getenv("ALPACA_SECRET_KEY")

trading_client = TradingClient(ALPACA_KEY, ALPACA_SECRET, paper=True)

def execute_buy_order(ticker: str, dollar_amount: float) -> bool:
    """
    Places a market buy order for a given dollar amount (fractional shares).
    """
    if dollar_amount <= 0:
        return False
        
    try:
        # Using 'notional' tells Alpaca to buy this exact dollar amount 
        # and calculate the fractional shares for us.
        order_data = MarketOrderRequest(
            symbol=ticker,
            notional=round(dollar_amount, 2), # Alpaca requires 2 decimal places
            side=OrderSide.BUY,
            time_in_force=TimeInForce.DAY
        )
        
        order = trading_client.submit_order(order_data)
        logger.info(f"✅ ORDER PLACED: Bought ${dollar_amount:.2f} of {ticker}. Order ID: {order.id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ FAILED to place order for {ticker}: {e}")
        return False

def get_open_positions() -> list:
    """Fetches a list of currently open positions from Alpaca."""
    try:
        positions = trading_client.get_all_positions()
        return [pos.symbol for pos in positions]
    except Exception as e:
        logger.error(f"Failed to fetch positions: {e}")
        return []

def execute_sell_order(ticker: str, shares: float) -> bool:
    """Sells a specific number of shares (supports fractional)."""
    if shares <= 0:
        return False
        
    try:
        order_data = MarketOrderRequest(
            symbol=ticker,
            qty=str(round(shares, 6)), # Alpaca requires fractional qty as a string
            side=OrderSide.SELL,
            time_in_force=TimeInForce.DAY
        )
        order = trading_client.submit_order(order_data)
        logger.info(f"✅ ORDER PLACED: Sold {shares} shares of {ticker}.")
        return True
    except Exception as e:
        logger.error(f"❌ FAILED to sell {ticker}: {e}")
        return False

def get_open_positions() -> list:
    """Fetches open positions with their entry prices and unrealized P&L."""
    try:
        positions = trading_client.get_all_positions()
        pos_list = []
        for pos in positions:
            pos_list.append({
                "symbol": pos.symbol,
                "qty": float(pos.qty),
                "avg_entry_price": float(pos.avg_entry_price),
                "current_price": float(pos.current_price),
                "unrealized_plpc": float(pos.unrealized_plpc) # Percentage gain/loss
            })
        return pos_list
    except Exception as e:
        logger.error(f"Failed to fetch positions: {e}")
        return []