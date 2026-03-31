import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

def plot_results(stats, symbol):
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=False)
    
    # Equity Curve
    ax1.plot(stats['equity_curve'], color='blue', lw=2)
    ax1.set_title(f"Equity Curve - {symbol}", fontsize=14)
    ax1.set_ylabel("Capital")
    ax1.grid(True, alpha=0.3)
    
    # Drawdown Curve
    ax2.fill_between(range(len(stats['drawdown_curve'])), stats['drawdown_curve'], color='red', alpha=0.3)
    ax2.set_title("Drawdown %", fontsize=14)
    ax2.set_ylabel("Drawdown %")
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(f"backtester/results_{symbol}.png")
    plt.close()

def monte_carlo_simulation(trades_df, initial_capital, simulations=1000):
    """
    Randomly shuffles trade outcomes to test robustness.
    """
    if trades_df.empty:
        return None
    
    results = []
    pnl_outcomes = trades_df['pnl'].values
    
    for _ in range(simulations):
        shuffled = np.random.choice(pnl_outcomes, size=len(pnl_outcomes), replace=True)
        equity = initial_capital + np.cumsum(shuffled)
        results.append(equity[-1])
    
    results = np.array(results)
    
    print("\n--- Monte Carlo Simulation (1000 runs) ---")
    print(f"Median Final Equity: {np.median(results):.2f}")
    print(f"5th Percentile (Worst): {np.percentile(results, 5):.2f}")
    print(f"Probability of Profit: {(results > initial_capital).mean() * 100:.2f}%")
    
    return results

def print_performance_table(stats):
    print("\n" + "="*40)
    print("      STRATEGY PERFORMANCE METRICS")
    print("="*40)
    print(f"Net Profit:          Rs. {stats['net_profit']:.2f}")
    print(f"Win Rate:            {stats['win_rate']:.2f}%")
    print(f"Profit Factor:       {stats['profit_factor']:.2f}")
    print(f"Expectancy:          Rs. {stats['expectancy']:.2f}")
    print(f"Max Drawdown:        {stats['max_drawdown']:.2f}%")
    print(f"Sharpe Ratio:        {stats['sharpe_ratio']:.4f}")
    print(f"Max Cons. Losses:    {stats['consecutive_losses']}")
    print(f"Total Trades:        {stats['total_trades']}")
    print("="*40)
