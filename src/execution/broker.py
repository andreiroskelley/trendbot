"""
src/execution/broker.py
Handles order execution via Alpaca for both Stocks and Crypto.
"""

import os
import logging
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce, AssetClass
from src.notifications import notify_buy

load_dotenv()
logger = logging.getLogger(__name__)

ALPACA_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET = os.getenv("ALPACA_SECRET_KEY")

trading_client = TradingClient(ALPACA_KEY, ALPACA_SECRET, paper=True)

def execute_buy_order(ticker: str, dollar_amount: float) -> bool:
    """Places a market buy order for a given dollar amount."""
    if dollar_amount <= 0:
        return False
        
    is_crypto = "/" in ticker
    asset_class = AssetClass.CRYPTO if is_crypto else AssetClass.US_EQUITY
    time_in_force = TimeInForce.GTC if is_crypto else TimeInForce.DAY
        
    try:
        order_data = MarketOrderRequest(
            symbol=ticker,
            notional=round(dollar_amount, 2), 
            side=OrderSide.BUY,
            time_in_force=time_in_force,
            asset_class=asset_class
        )
        
        order = trading_client.submit_order(order_data)
        logger.info(f"✅ ORDER PLACED: Bought ${dollar_amount:.2f} of {ticker}. Order ID: {order.id}")
        
        # --- NOTIFICATION LOGIC ---
        # Attempt to get actual fill data. If not filled yet, estimate.
        filled_price = float(order.filled_avg_price) if order.filled_avg_price else 0.0
        filled_qty = float(order.filled_qty) if order.filled_qty else 0.0
        
        if filled_qty > 0 and filled_price > 0:
            notify_buy(ticker, dollar_amount, filled_price, filled_qty)
        else:
            # Fallback if Alpaca hasn't returned fill data yet (e.g., crypto or slow fills)
            # We estimate the shares based on requested notional / current market price
            from src.data.market import get_market_data
            try:
                current_price = get_market_data(ticker)['close'].iloc[-1]
                estimated_shares = dollar_amount / current_price
                notify_buy(ticker, dollar_amount, current_price, estimated_shares)
            except Exception:
                logger.warning(f"Order submitted but fill data unavailable. Notification skipped or estimated.")
                # Send a generic notification so you know it happened
                notify_buy(ticker, dollar_amount, 0.0, 0.0)
                
        return True
        
    except Exception as e:
        logger.error(f"❌ FAILED to place order for {ticker}: {e}")
        return False

def execute_sell_order(ticker: str, shares: float) -> bool:
    """Sells a specific number of shares (supports fractional)."""
    if shares <= 0:
        return False
        
    is_crypto = "/" in ticker
    asset_class = AssetClass.CRYPTO if is_crypto else AssetClass.US_EQUITY
    time_in_force = TimeInForce.GTC if is_crypto else TimeInForce.DAY
        
    try:
        order_data = MarketOrderRequest(
            symbol=ticker,
            qty=str(round(shares, 6)),
            side=OrderSide.SELL,
            time_in_force=time_in_force,
            asset_class=asset_class
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
                "unrealized_plpc": float(pos.unrealized_plpc)
            })
        return pos_list
    except Exception as e:
        logger.error(f"Failed to fetch positions: {e}")
        return []