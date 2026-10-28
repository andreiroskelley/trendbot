"""
scripts/optimize_yf.py
"""

import os
import sys
import random
import logging
import pandas as pd
import numpy as np
from datetime import datetime
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.analysis.trend import is_uptrend
from src.signals.pullback import check_pullback_signal
from src.signals.breakout import check_breakout_signal
from src.execution.risk import calculate_position_size, calculate_stop_loss_price, check_max_positions

load_dotenv()
logging.basicConfig(level=logging.ERROR) 
logger = logging.getLogger(__name__)

WATCHLIST = [
    "AAPL", "MSFT", "NVDA", "LLY", "TSLA", "AMD", "META", "GOOGL", 
    "AMZN", "JPM", "V", "WMT", "JNJ", "PG", "XOM", "HD", 
    "CVX", "MRK", "ABBV", "PEP", "KO", "COST", "AVGO", "ADBE", 
    "CRM", "NFLX", "CSCO", "INTC", "QCOM", "TXN"
]
BENCHMARK = "SPY"
START_DATE = "2008-01-01"
END_DATE = "2024-10-01"
INITIAL_CAPITAL = 10000.0
CACHE_DIR = "data/cache_yf"

def load_cached_data():
    data = {}
    all_tickers = WATCHLIST + [BENCHMARK]
    for ticker in all_tickers:
        cache_file = os.path.join(CACHE_DIR, f"{ticker}_{START_DATE}_{END_DATE}.csv")
        if os.path.exists(cache_file):
            df = pd.read_csv(cache_file, index_col='Date', parse_dates=True)
            data[ticker] = df
        else:
            print(f"Missing cache for {ticker}. Run backtest_yf.py first.")
            sys.exit(1)
    return data

RAW_DATA = load_cached_data()
BENCHMARK_DF = RAW_DATA[BENCHMARK]
TRADING_DAYS = BENCHMARK_DF.index

def run_backtest(chromosome):
    rsi_threshold = chromosome['rsi']
    support_prox = chromosome['prox']
    stop_loss_pct = chromosome['stop']
    adx_threshold = chromosome['adx']
    
    config = {
        'trend': {'sma_short': 20, 'sma_long': 50, 'adx_period': 14, 'adx_threshold': adx_threshold, 'rel_strength_days': 20},
        'signals': {
            'pullback': {'rsi_period': 14, 'rsi_threshold': rsi_threshold, 'support_proximity': support_prox},
            'breakout': {'lookback_period': 20, 'volume_multiplier': 1.5}
        },
        'risk': {'max_position_pct': 0.05, 'stop_loss_pct': stop_loss_pct, 'max_open_positions': 3}
    }

    cash = INITIAL_CAPITAL
    positions = {}
    
    for i, current_date in enumerate(TRADING_DAYS):
        if i < 50: continue

        for ticker in list(positions.keys()):
            if ticker not in RAW_DATA or current_date not in RAW_DATA[ticker].index: continue
            current_price = RAW_DATA[ticker].loc[current_date, 'close']
            pos = positions[ticker]
            
            stop_price = calculate_stop_loss_price(pos['entry_price'], stop_loss_pct)
            if current_price <= stop_price:
                cash += pos['qty'] * current_price
                del positions[ticker]

        total_equity = cash
        for ticker, pos in positions.items():
            if current_date in RAW_DATA[ticker].index:
                total_equity += pos['qty'] * RAW_DATA[ticker].loc[current_date, 'close']
            else:
                total_equity += pos['qty'] * pos['entry_price']

        open_count = len(positions)
        if check_max_positions(open_count, 3):
            for ticker in WATCHLIST:
                if ticker in positions: continue
                if ticker not in RAW_DATA or current_date not in RAW_DATA[ticker].index: continue

                stock_hist = RAW_DATA[ticker].loc[:current_date]
                bench_hist = BENCHMARK_DF.loc[:current_date]

                if len(stock_hist) < 55: continue

                if is_uptrend(stock_hist, bench_hist, config['trend']):
                    if check_pullback_signal(stock_hist, config['signals']['pullback']) or check_breakout_signal(stock_hist, config['signals']['breakout']):
                        current_price = stock_hist['close'].iloc[-1]
                        shares = calculate_position_size(total_equity, current_price, 0.05)
                        
                        if shares > 0 and cash >= (shares * current_price):
                            cash -= (shares * current_price)
                            positions[ticker] = {'qty': shares, 'entry_price': current_price}
                            open_count += 1
                            if open_count >= 3: break

    final_equity = cash
    for ticker, pos in positions.items():
        final_equity += pos['qty'] * RAW_DATA[ticker]['close'].iloc[-1]
        
    return ((final_equity - INITIAL_CAPITAL) / INITIAL_CAPITAL) * 100

def generate_random_chromosome():
    return {
        'rsi': random.randint(30, 60),
        'prox': round(random.uniform(0.01, 0.05), 3),
        'stop': round(random.uniform(0.02, 0.08), 3),
        'adx': random.randint(20, 35)
    }

def crossover(parent1, parent2):
    child = {}
    for key in parent1.keys():
        if random.random() < 0.5:
            child[key] = parent1[key]
        else:
            child[key] = parent2[key]
            
    if random.random() < 0.1: child['rsi'] = random.randint(30, 60)
    if random.random() < 0.1: child['prox'] = round(random.uniform(0.01, 0.05), 3)
    if random.random() < 0.1: child['stop'] = round(random.uniform(0.02, 0.08), 3)
    if random.random() < 0.1: child['adx'] = random.randint(20, 35)
    
    return child

def run_ga():
    population_size = 30
    generations = 10
    
    population = [generate_random_chromosome() for _ in range(population_size)]
    
    print(f"Evolving {population_size} strategies over {generations} generations (18 Years of Data)...\n")

    best_overall_score = -999
    best_overall_chromo = None

    for gen in range(generations):
        scored_population = []
        for chromo in population:
            score = run_backtest(chromo)
            scored_population.append((score, chromo))
            
        scored_population.sort(key=lambda x: x[0], reverse=True)
        
        best_score = scored_population[0][0]
        best_chromo = scored_population[0][1]
        
        if best_score > best_overall_score:
            best_overall_score = best_score
            best_overall_chromo = best_chromo
        
        print(f"Gen {gen+1}/{generations} | Best Return: {best_score:.2f}% | Params: RSI={best_chromo['rsi']}, Stop={best_chromo['stop']*100:.1f}%, ADX={best_chromo['adx']}")

        survivors = [chromo for score, chromo in scored_population[:population_size // 2]]
        
        next_gen = survivors.copy()
        while len(next_gen) < population_size:
            p1 = random.choice(survivors)
            p2 = random.choice(survivors)
            next_gen.append(crossover(p1, p2))
            
        population = next_gen

    print("\n" + "="*40)
    print("OPTIMAL PARAMETERS FOUND (2008-2024)")
    print("="*40)
    print(f"Total Return: {best_overall_score:.2f}%")
    print(f"RSI Threshold: {best_overall_chromo['rsi']}")
    print(f"Support Proximity: {best_overall_chromo['prox']*100:.2f}%")
    print(f"Stop Loss: {best_overall_chromo['stop']*100:.2f}%")
    print(f"ADX Threshold: {best_overall_chromo['adx']}")
    print("="*40)

if __name__ == "__main__":
    run_ga()