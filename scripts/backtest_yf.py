"""
scripts/backtest_yf.py

18-Year Backtester using Yahoo Finance data (2008-2025).
"""

import os
import sys
import logging
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.analysis.trend import is_uptrend
from src.signals.pullback import check_pullback_signal
from src.signals.breakout import check_breakout_signal
from src.execution.risk import calculate_position_size, calculate_stop_loss_price, check_max_positions

load_dotenv()
logger = logging.getLogger(__name__)

WATCHLIST = [
    "AAPL", "MSFT", "NVDA", "LLY", "TSLA", "AMD", "META", "GOOGL", 
    "AMZN", "JPM", "V", "WMT", "JNJ", "PG", "XOM", "HD", 
    "CVX", "MRK", "ABBV", "PEP", "KO", "COST", "AVGO", "ADBE", 
    "CRM", "NFLX", "CSCO", "INTC", "QCOM", "TXN"
]
BENCHMARK = "SPY"
START_DATE = "2008-01-01"
END_DATE = "2024-10-01"  # Adjusting to 2024 for stable Yahoo data
INITIAL_CAPITAL = 10000.0

# Robust Middle Parameters
CONFIG = {
    'trend': {'sma_short': 20, 'sma_long': 50, 'adx_period': 14, 'adx_threshold': 28, 'rel_strength_days': 20},
    'signals': {
        'pullback': {'rsi_period': 14, 'rsi_threshold': 58, 'support_proximity': 0.04},
        'breakout': {'lookback_period': 20, 'volume_multiplier': 1.5}
    },
    'risk': {'max_position_pct': 0.05, 'stop_loss_pct': 0.05, 'max_open_positions': 3}
}

CACHE_DIR = "data/cache_yf"
os.makedirs(CACHE_DIR, exist_ok=True)

def fetch_data(tickers, start, end):
    data = {}
    for ticker in tickers:
        cache_file = os.path.join(CACHE_DIR, f"{ticker}_{start}_{end}.csv")
        
        if os.path.exists(cache_file):
            df = pd.read_csv(cache_file, index_col='Date', parse_dates=True)
            data[ticker] = df
            continue
            
        logger.info(f"Fetching {ticker} from Yahoo Finance...")
        try:
            # Download data
            ticker_data = yf.download(ticker, start=start, end=end, progress=False)
            if not ticker_data.empty:
                # yfinance returns a multi-index for multiple tickers, flatten it
                if isinstance(ticker_data.columns, pd.MultiIndex):
                    ticker_data.columns = ticker_data.columns.get_level_values(0)
                
                df = ticker_data[['High', 'Low', 'Close', 'Volume']]
                df.columns = ['high', 'low', 'close', 'volume']
                df.to_csv(cache_file)
                data[ticker] = df
        except Exception as e:
            logger.error(f"Failed to fetch {ticker}: {e}")
            
    return data

def run_backtest():
    logger.info("Loading data (this may take a minute for 18 years)...")
    all_tickers = WATCHLIST + [BENCHMARK]
    raw_data = fetch_data(all_tickers, START_DATE, END_DATE)
    
    if BENCHMARK not in raw_data:
        logger.error("Benchmark data missing. Aborting.")
        return
        
    benchmark_df = raw_data[BENCHMARK]
    trading_days = benchmark_df.index
    
    portfolio = {
        'cash': INITIAL_CAPITAL,
        'equity': INITIAL_CAPITAL,
        'positions': {},
        'history': []
    }

    logger.info(f"Running backtest over {len(trading_days)} trading days...")

    for i, current_date in enumerate(trading_days):
        if i < 50: continue

        for ticker in list(portfolio['positions'].keys()):
            if ticker not in raw_data or current_date not in raw_data[ticker].index: continue
            
            current_price = raw_data[ticker].loc[current_date, 'close']
            pos = portfolio['positions'][ticker]
            
            stop_price = calculate_stop_loss_price(pos['entry_price'], CONFIG['risk']['stop_loss_pct'])
            if current_price <= stop_price:
                proceeds = pos['qty'] * current_price
                portfolio['cash'] += proceeds
                logger.info(f"[{current_date.date()}] STOP LOSS SELL {ticker} @ ${current_price:.2f}")
                del portfolio['positions'][ticker]

        total_equity = portfolio['cash']
        for ticker, pos in portfolio['positions'].items():
            if current_date in raw_data[ticker].index:
                total_equity += pos['qty'] * raw_data[ticker].loc[current_date, 'close']
            else:
                total_equity += pos['qty'] * pos['entry_price']
        portfolio['equity'] = total_equity

        open_positions_count = len(portfolio['positions'])
        if check_max_positions(open_positions_count, CONFIG['risk']['max_open_positions']):
            for ticker in WATCHLIST:
                if ticker in portfolio['positions']: continue
                if ticker not in raw_data or current_date not in raw_data[ticker].index: continue

                stock_hist = raw_data[ticker].loc[:current_date]
                bench_hist = benchmark_df.loc[:current_date]

                if len(stock_hist) < 55: continue

                if is_uptrend(stock_hist, bench_hist, CONFIG['trend']):
                    is_pullback = check_pullback_signal(stock_hist, CONFIG['signals']['pullback'])
                    is_breakout = check_breakout_signal(stock_hist, CONFIG['signals']['breakout'])
                    
                    if is_pullback or is_breakout:
                        current_price = stock_hist['close'].iloc[-1]
                        shares = calculate_position_size(portfolio['equity'], current_price, CONFIG['risk']['max_position_pct'])
                        
                        if shares > 0:
                            cost = shares * current_price
                            if portfolio['cash'] >= cost:
                                portfolio['cash'] -= cost
                                portfolio['positions'][ticker] = {'qty': shares, 'entry_price': current_price}
                                logger.info(f"[{current_date.date()}] BUY {ticker} @ ${current_price:.2f}")
                                open_positions_count += 1
                                if open_positions_count >= CONFIG['risk']['max_open_positions']:
                                    break

        portfolio['history'].append({'date': current_date, 'equity': portfolio['equity']})

    final_equity = portfolio['equity']
    total_return = ((final_equity - INITIAL_CAPITAL) / INITIAL_CAPITAL) * 100
    
    print("\n" + "="*40)
    print("18-YEAR BACKTEST RESULTS (2008-2024)")
    print("="*40)
    print(f"Initial Capital: ${INITIAL_CAPITAL:,.2f}")
    print(f"Final Equity:    ${final_equity:,.2f}")
    print(f"Total Return:    {total_return:.2f}%")
    print("="*40)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%Y-%m-%d')
    run_backtest()