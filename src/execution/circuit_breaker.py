"""
src/execution/circuit_breaker.py

Hard equity floor. If total account equity drops below the configured
minimum, liquidate all positions, persist a "trading disabled" flag,
and alert. The flag survives systemd restarts.
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import requests

from src.data.market import get_account_equity
from src.execution.broker import execute_sell_order, get_open_positions

logger = logging.getLogger(__name__)

# Resolve state path relative to repo root (works under `python -m src.main`)
_REPO_ROOT = Path(__file__).resolve().parents[2]


def _resolve_state_path(config: dict) -> Path:
    rel = config.get("state_file", "data/bot_state.json")
    p = Path(rel)
    return p if p.is_absolute() else _REPO_ROOT / p


def load_state(path: Path) -> dict:
    try:
        with open(path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception as e:
        logger.error(f"Failed to read state file {path}: {e}")
        return {}


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2)
    os.replace(tmp, path)  # atomic


def is_trading_disabled(state_path: Path) -> bool:
    return bool(load_state(state_path).get("trading_disabled", False))


def send_alert(config: dict, message: str) -> None:
    webhook = os.getenv("DISCORD_WEBHOOK_URL", "").strip()
    if not webhook:
        logger.critical(f"CIRCUIT BREAKER ALERT (no webhook configured): {message}")
        return
    try:
        requests.post(webhook, json={"content": f"🛑 **Circuit Breaker**\n{message}"}, timeout=10)
    except Exception as e:
        logger.error(f"Failed to send alert: {e}")
        logger.critical(f"CIRCUIT BREAKER ALERT (delivery failed): {message}")


def check_circuit_breaker(config: dict) -> bool:
    """
    Returns True if the breaker is tripped (trading should stop now).
    Trips when equity < min_equity; liquidates if configured.
    """
    if not config.get("enabled", True):
        return False

    state_path = _resolve_state_path(config)
    if is_trading_disabled(state_path):
        logger.critical("Circuit breaker previously tripped; trading disabled. Manual reset required.")
        return True

    equity = get_account_equity()
    min_equity = float(config.get("min_equity", 400.0))

    if equity >= min_equity:
        logger.info(f"Equity ${equity:.2f} >= floor ${min_equity:.2f}. OK.")
        return False

    logger.critical(f"🛑 CIRCUIT BREAKER TRIPPED: equity ${equity:.2f} < ${min_equity:.2f}")

    if config.get("liquidate_on_trigger", True):
        for pos in get_open_positions():
            logger.critical(f"Liquidating {pos['symbol']} ({pos['qty']} units)")
            execute_sell_order(pos["symbol"], pos["qty"])

    state = {
        "trading_disabled": True,
        "disabled_at": datetime.now(timezone.utc).isoformat(),
        "reason": "circuit_breaker",
        "equity_at_trigger": equity,
    }
    save_state(state_path, state)

    send_alert(
        config,
        f"Equity fell to ${equity:.2f} (floor ${min_equity:.2f}). "
        f"Positions liquidated: {config.get('liquidate_on_trigger', True)}. Trading disabled.",
    )
    return True