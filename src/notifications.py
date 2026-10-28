"""
src/notifications.py

Discord notifications for trade events and system alerts.
All sends are best-effort: a webhook failure NEVER blocks trading.
"""

import logging
import os

import requests

logger = logging.getLogger(__name__)

_WEBHOOK_ENV = "DISCORD_WEBHOOK_URL"


def _webhook_url() -> str:
    return os.getenv(_WEBHOOK_ENV, "").strip()


def _post(content: str) -> bool:
    """POST to Discord. Returns True on success, False otherwise. Never raises."""
    url = _webhook_url()
    if not url:
        logger.warning(f"Discord webhook not configured ({_WEBHOOK_ENV}); message dropped: {content}")
        return False
    try:
        r = requests.post(url, json={"content": content}, timeout=10)
        r.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Discord notification failed: {e}")
        return False


def notify_buy(ticker: str, dollar_amount: float, price: float, shares: float) -> None:
    _post(
        f"🟢 **BUY** `{ticker}`\n"
        f"${dollar_amount:.2f} @ ${price:,.2f} ({shares:.6f} units)"
    )


def notify_sell(ticker: str, shares: float, reason: str, pnl_pct: float | None = None) -> None:
    pnl_line = f"\nP&L: {pnl_pct*100:+.2f}%" if pnl_pct is not None else ""
    _post(
        f"🔴 **SELL** `{ticker}`\n"
        f"{shares:.6f} units — reason: **{reason}**{pnl_line}"
    )


def notify_alert(message: str) -> None:
    _post(f"⚠️ **ALERT**\n{message}")


def notify_startup(equity: float, market_open: bool) -> None:
    state = "OPEN" if market_open else "CLOSED"
    _post(
        f"🤖 **TrendBot started**\n"
        f"Equity: ${equity:,.2f}\n"
        f"US market: {state}"
    )