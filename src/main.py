"""
src/main.py
"""

import logging
import yaml
import time
from src.data.market import (
    get_market_data,
    get_market_benchmark,
    get_account_capital,
    get_account_equity,
    is_market_open,
)
from src.data.news import get_recent_news
from src.analysis.trend import is_uptrend
from src.analysis.anomaly import is_suspicious_drop
from src.signals.pullback import check_pullback_signal
from src.signals.breakout import check_breakout_signal
from src.execution.risk import calculate_position_size, check_max_positions
from src.execution.broker import execute_buy_order, get_open_positions, execute_sell_order
from src.execution.circuit_breaker import check_circuit_breaker
from src.agent.news_judge import NewsJudgeAgent
from src.notifications import notify_sell, notify_startup

# --- Setup Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- BYPASS AI: Auto-approve everything ---
class AutoApproveLLM:
    def analyze_news(self, ticker, headlines):
        logger.info(f"[{ticker}] Auto-approving news (Ollama bypassed).")
        return False # False means "No Veto", so we proceed with the trade
# --------------------------------------------

def load_config():
    with open("config/settings.yaml", "r") as f:
        return yaml.safe_load(f)

def check_stop_losses(config: dict):
    """Checks all open positions and sells if they drop below the stop-loss percentage."""
    logger.info("Checking stop-losses...")
    positions = get_open_positions()
    stop_loss_pct = config['risk']['stop_loss_pct']
    
    for pos in positions:
        ticker = pos['symbol']
        unrealized_plpc = pos['unrealized_plpc'] # e.g., -0.04 means -4%
        
        # If the loss is greater than our stop-loss threshold
        if unrealized_plpc <= -stop_loss_pct:
            logger.warning(f"🛑 STOP LOSS HIT for {ticker}! Current P&L: {unrealized_plpc*100:.2f}%")
            if execute_sell_order(ticker, pos['qty']):
                notify_sell(ticker, pos['qty'], reason="stop-loss", pnl_pct=unrealized_plpc)
        else:
            logger.info(f"[{ticker}] P&L is {unrealized_plpc*100:.2f}%. Holding.")

def run_bot_cycle(config: dict):
    logger.info("=== Starting Bot Cycle ===")
    
    # 0. Circuit breaker — highest priority, before anything else
    if check_circuit_breaker(config['risk']['circuit_breaker']):
        logger.critical("Trading disabled by circuit breaker. Skipping cycle.")
        return
    
    # 1. First, check if we need to dump any bad positions
    check_stop_losses(config)
    
    # 2. Setup for new trades
    llm = AutoApproveLLM()
    news_agent = NewsJudgeAgent(llm_client=llm, config=config['news'])
    
    account_equity = get_account_equity()
    if account_equity <= 0:
        logger.error("No account equity available. Aborting cycle.")
        return
    logger.info(f"Current Alpaca Buying Power: ${get_account_capital():.2f}")
    logger.info(f"Current Alpaca Equity: ${account_equity:.2f}")
    
    # 3. Market-hours gate
    equity_market_open = is_market_open()
    logger.info(f"US equity market open: {equity_market_open}")
    
    open_positions_list = get_open_positions()
    open_positions_count = len(open_positions_list)
    open_symbols = [pos['symbol'] for pos in open_positions_list]
    
    for ticker in config['watchlist']:
        logger.info(f"Scanning {ticker}...")
        
        if ticker in open_symbols:
            logger.info(f"[{ticker}] Already own this stock. Skipping.")
            continue
            
        if not check_max_positions(open_positions_count, config['risk']['max_open_positions']):
            logger.warning("Max positions reached. Stopping scan.")
            break

        is_crypto = "/" in ticker
        if not is_crypto and not equity_market_open:
            logger.info(f"[{ticker}] US equity market closed. Skipping stock.")
            continue

        stock_data = get_market_data(ticker)
        if stock_data.empty:
            logger.warning(f"[{ticker}] No data available. Skipping.")
            continue
        
        market_data = get_market_benchmark(ticker)
        if market_data.empty:
            logger.warning(f"[{ticker}] No benchmark data. Skipping.")
            continue
            
        current_price = stock_data['close'].iloc[-1]
        
        if not is_uptrend(stock_data, market_data, config['trend']):
            logger.info(f"[{ticker}] Not in an uptrend. Skipping.")
            continue
            
        is_pullback = check_pullback_signal(stock_data, config['signals']['pullback'])
        is_breakout = check_breakout_signal(stock_data, config['signals']['breakout'])
        
        if not (is_pullback or is_breakout):
            logger.info(f"[{ticker}] Uptrend confirmed, but no valid entry signal yet.")
            continue
            
        logger.info(f"[{ticker}] 🚨 ENTRY SIGNAL TRIGGERED!")
        
        # --- Z-SCORE ANOMALY DETECTION ---
        z_config = config['signals'].get('z_score', {'period': 20, 'threshold': -3.0})
        
        if is_suspicious_drop(stock_data, z_config):
            logger.warning(f"[{ticker}] ⚠️ Suspicious drop detected! Consulting AI...")
            headlines = get_recent_news(ticker)
            if news_agent.should_veto_trade(ticker, headlines):
                logger.warning(f"[{ticker}] ❌ TRADE VETOED BY AI.")
                continue
            else:
                logger.info(f"[{ticker}] AI says the news is NOISE. Proceeding with trade.")
        else:
            logger.info(f"[{ticker}] Price action is normal. Skipping AI check.")
            
        # --- EXECUTION ---
        # Calculate size based on ACCOUNT EQUITY, not Buying Power (Margin)
        max_dollar_amount = account_equity * config['risk']['max_position_pct']
        shares = calculate_position_size(
            account_capital=account_equity, 
            current_price=current_price,
            max_position_pct=config['risk']['max_position_pct']
        )
        
        if shares > 0:
            logger.info(f"[{ticker}] ✅ Buying ${max_dollar_amount:.2f} of shares at ${current_price:.2f}.")
            if execute_buy_order(ticker, max_dollar_amount):
                open_positions_count += 1
                # Note: notify_buy is now called inside broker.py to capture actual fill data
        else:
            logger.warning(f"[{ticker}] Signal valid, but account size too small.")

    logger.info("=== Bot Cycle Complete ===")

def main():
    config = load_config()
    logger.info(f"Bot starting in mode: {config['system']['mode']}")

    try:
        notify_startup(get_account_equity(), is_market_open())
    except Exception as e:
        logger.error(f"Startup notification failed: {e}")
    
    while True:
        run_bot_cycle(config)
        interval = config['system']['poll_interval_minutes'] * 60
        logger.info(f"Sleeping for {config['system']['poll_interval_minutes']} minutes...")
        time.sleep(interval)

if __name__ == "__main__":
    main()