"""
src/main.py
"""

import logging
import yaml
import time
from src.data.market import get_market_data, get_market_benchmark, get_account_capital
from src.data.news import get_recent_news
from src.analysis.trend import is_uptrend
from src.signals.pullback import check_pullback_signal
from src.signals.breakout import check_breakout_signal
from src.execution.risk import calculate_position_size, check_max_positions
from src.execution.broker import execute_buy_order, get_open_positions, execute_sell_order
from src.agent.news_judge import NewsJudgeAgent, OllamaClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
        
        # If the loss is greater than our stop-loss threshold (e.g., < -3%)
        if unrealized_plpc <= -stop_loss_pct:
            logger.warning(f"🛑 STOP LOSS HIT for {ticker}! Current P&L: {unrealized_plpc*100:.2f}%")
            execute_sell_order(ticker, pos['qty'])
        else:
            logger.info(f"[{ticker}] P&L is {unrealized_plpc*100:.2f}%. Holding.")

def run_bot_cycle(config: dict):
    logger.info("=== Starting Bot Cycle ===")
    
    # 1. First, check if we need to dump any bad positions
    check_stop_losses(config)
    
    # 2. Setup for new trades
    llm = OllamaClient()
    news_agent = NewsJudgeAgent(llm_client=llm, config=config['news'])
    
    account_capital = get_account_capital()
    if account_capital <= 0:
        logger.error("No buying power available. Aborting cycle.")
        return
    logger.info(f"Current Alpaca Buying Power: ${account_capital:.2f}")
    
    open_positions_list = get_open_positions()
    open_positions_count = len(open_positions_list)
    open_symbols = [pos['symbol'] for pos in open_positions_list]
    
    market_data = get_market_benchmark()
    if market_data.empty:
        logger.error("Could not fetch market benchmark. Aborting cycle.")
        return
    
    for ticker in config['watchlist']:
        logger.info(f"Scanning {ticker}...")
        
        if ticker in open_symbols:
            logger.info(f"[{ticker}] Already own this stock. Skipping.")
            continue
            
        if not check_max_positions(open_positions_count, config['risk']['max_open_positions']):
            logger.warning("Max positions reached. Stopping scan.")
            break

        stock_data = get_market_data(ticker)
        if stock_data.empty:
            logger.warning(f"[{ticker}] No data available. Skipping.")
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
        
        headlines = get_recent_news(ticker)
        if news_agent.should_veto_trade(ticker, headlines):
            logger.warning(f"[{ticker}] ❌ TRADE VETOED by News Judge.")
            continue
            
        max_dollar_amount = account_capital * config['risk']['max_position_pct']
        shares = calculate_position_size(
            account_capital=account_capital,
            current_price=current_price,
            max_position_pct=config['risk']['max_position_pct']
        )
        
        if shares > 0:
            logger.info(f"[{ticker}] ✅ Buying ${max_dollar_amount:.2f} of shares at ${current_price:.2f}.")
            if execute_buy_order(ticker, max_dollar_amount):
                open_positions_count += 1 
        else:
            logger.warning(f"[{ticker}] Signal valid, but account size too small.")

    logger.info("=== Bot Cycle Complete ===")

def main():
    config = load_config()
    logger.info(f"Bot starting in mode: {config['system']['mode']}")
    
    while True:
        run_bot_cycle(config)
        interval = config['system']['poll_interval_minutes'] * 60
        logger.info(f"Sleeping for {config['system']['poll_interval_minutes']} minutes...")
        time.sleep(interval)

if __name__ == "__main__":
    main()