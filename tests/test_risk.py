"""
tests/test_risk.py
"""

import pytest
from src.execution.risk import calculate_position_size, calculate_stop_loss_price, check_max_positions

def test_position_size_normal():
    """$500 account, 5% limit ($25), $10 stock -> 2 shares."""
    shares = calculate_position_size(account_capital=500, current_price=10, max_position_pct=0.05)
    assert shares == 2

def test_position_size_too_expensive():
    """$500 account, 5% limit ($25), $150 stock -> 0 shares (can't afford even 1 share within risk limits)."""
    shares = calculate_position_size(account_capital=500, current_price=150, max_position_pct=0.05)
    assert shares == 0

def test_position_size_large_account():
    """$10,000 account, 5% limit ($500), $150 stock -> 3 shares."""
    shares = calculate_position_size(account_capital=10000, current_price=150, max_position_pct=0.05)
    assert shares == 3

def test_stop_loss():
    """Buy at $100, 3% stop loss -> sell at $97."""
    stop_price = calculate_stop_loss_price(entry_price=100.0, stop_loss_pct=0.03)
    assert stop_price == 97.0

def test_stop_loss_rounding():
    """Buy at $15.55, 3% stop loss -> sell at $15.08 (rounded)."""
    stop_price = calculate_stop_loss_price(entry_price=15.55, stop_loss_pct=0.03)
    assert stop_price == 15.08

def test_max_positions_allowed():
    """0 open, max 3 -> True."""
    assert check_max_positions(current_open_positions=0, max_allowed=3) is True

def test_max_positions_blocked():
    """3 open, max 3 -> False."""
    assert check_max_positions(current_open_positions=3, max_allowed=3) is False