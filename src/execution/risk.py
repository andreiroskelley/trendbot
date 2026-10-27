"""
src/execution/risk.py
Math for position sizing and stop-losses.
Protects the capital from blowing up.
"""

import logging

logger = logging.getLogger(__name__)

def calculate_position_size(
    account_capital: float, 
    current_price: float, 
    max_position_pct: float
) -> float: # Changed return type to float
    """
    Calculates how many fractional shares to buy based on total capital and risk limits.
    """
    if current_price <= 0:
        logger.error("Current price must be greater than 0.")
        return 0.0

    # How much cash are we allowed to spend on this trade?
    max_dollar_amount = account_capital * max_position_pct
    
    # Calculate fractional shares (rounded to 6 decimal places for Alpaca)
    shares = round(max_dollar_amount / current_price, 6)

    if shares < 0.001: # Arbitrary minimum threshold to avoid dust trades
        logger.warning(
            f"Not enough capital to buy a fractional share. "
            f"Price: ${current_price:.2f}, Max allowed: ${max_dollar_amount:.2f}"
        )
        return 0.0

    logger.info(
        f"Position Sizing: ${max_dollar_amount:.2f} / ${current_price:.2f} = {shares} shares."
    )
    return shares

def calculate_stop_loss_price(entry_price: float, stop_loss_pct: float) -> float:
    """Calculates the price at which we must sell to enforce a hard stop-loss."""
    if entry_price <= 0:
        return 0.0
    stop_price = entry_price * (1 - stop_loss_pct)
    return round(stop_price, 2)

def check_max_positions(current_open_positions: int, max_allowed: int) -> bool:
    """Checks if we are allowed to open another trade."""
    if current_open_positions >= max_allowed:
        logger.warning(f"Max open positions reached ({current_open_positions}/{max_allowed}). Skipping trade.")
        return False
    return True