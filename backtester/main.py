import sys
import os
import argparse
from .data_loader import get_backtest_data
from .engine import BacktestEngine
from .analytics import plot_results, monte_carlo_simulation, print_performance_table
from .config import CAPITAL

def run_backtest(symbol, exchange, days=30, period=None, multiplier=None, adx=None):
    print(f"Starting Professional Backtest for {symbol} ({exchange}) over {days} days...")
    
    # 1. Load Data
    df_15m, df_1h = get_backtest_data(symbol, exchange, days)
    
    if df_15m is None or df_1h is None:
        print("Failed to load data. Please check your API credentials or symbol.")
        return

    from .config import (
        EMA_FAST, EMA_SLOW, EMA_FILTER, SUPERTREND_PERIOD, SUPERTREND_MULTIPLIER,
        RISK_PER_TRADE_PERCENT, TARGET_RR
    )
    
    params = {
        'ema_fast': EMA_FAST,
        'ema_slow': EMA_SLOW,
        'ema_filter': EMA_FILTER,
        'st_period': period or SUPERTREND_PERIOD,
        'st_multiplier': multiplier or SUPERTREND_MULTIPLIER,
        'risk_per_trade': RISK_PER_TRADE_PERCENT,
        'target_rr': TARGET_RR,
        'adx_filter': adx if adx is not None else 0
    }

    # 2. Run Engine
    engine = BacktestEngine(df_15m, df_1h, initial_capital=CAPITAL, params=params)
    stats = engine.run()
    
    if 'error' in stats:
        print(f"Backtest error: {stats['error']}")
        return

    # 3. Analytics & Visualization
    print_performance_table(stats)
    plot_results(stats, symbol)
    print(f"Plots saved to backtester/results_{symbol}.png")
    
    monte_carlo_simulation(stats['trades'], CAPITAL)

def main():
    parser = argparse.ArgumentParser(description="Professional Trading Strategy Backtester")
    parser.add_argument("--symbol", default="BTCUSD", help="Symbol to backtest (e.g. TCS, RELIANCE, BTCUSD)")
    parser.add_argument("--exchange", default="DELTA", help="Exchange (NSE, MCX, DELTA)")
    parser.add_argument("--days", type=int, default=30, help="Number of days for historical data")
    parser.add_argument("--period", type=int, help="Supertrend Period override")
    parser.add_argument("--multiplier", type=float, help="Supertrend Multiplier override")
    parser.add_argument("--adx", type=int, help="ADX filter override")
    
    args = parser.parse_args()
    
    # Check if we should use Delta or Angel based on user input
    # Default to RELIANCE / NSE if not provided
    run_backtest(args.symbol, args.exchange.upper(), args.days, args.period, args.multiplier, args.adx)

if __name__ == "__main__":
    # If running as a module/script
    # Need to handle relative imports if run directly
    try:
        main()
    except Exception as e:
        print(f"Runtime error: {e}")
        import traceback
        traceback.print_exc()

# --- OPTIMIZATION SUGGESTION ---
"""
To perform parameter optimization, you can wrap the BacktestEngine in a loop:

results = []
for p in range(20, 41): # Supertrend Period
    for m in [1.5, 2.0, 2.5, 3.0]: # Multiplier
        # Update config/engine parameters
        # Run engine
        # Store (p, m, net_profit, sharpe)
"""

# --- VOLATILITY FILTER RECOMMENDATION ---
"""
Recommendation: ADX Filter
Add a rule: "No trades if ADX < 20 or ADX < 25"
This helps avoid sideways/choppy markets where trend-following strategies suffer from whipsaws.
"""
