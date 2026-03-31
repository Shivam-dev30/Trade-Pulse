import pandas as pd
from .data_loader import get_backtest_data
from .engine import BacktestEngine
from .config import CAPITAL

def optimize_crude():
    symbol = "CRUDEOIL"
    exchange = "MCX"
    days = 90
    
    df_15m, df_1h = get_backtest_data(symbol, exchange, days)
    if df_15m is None:
        print("Failed to load data")
        return

    results = []
    
    # Define optimization ranges
    st_periods = [31, 40]
    st_multipliers = [2.0, 3.0]
    target_rrs = [1.0, 1.2, 1.5]
    be_triggers = [0.5, 0.8]
    adx_filters = [0, 20]
    
    print(f"Optimizing {symbol} with Win-Rate Improvements...")
    
    for p in st_periods:
        for m in st_multipliers:
            for rr in target_rrs:
                for be in be_triggers:
                    for adx in adx_filters:
                        params = {
                            'ema_fast': 9,
                            'ema_slow': 15,
                            'ema_filter': 20,
                            'st_period': p,
                            'st_multiplier': m,
                            'risk_per_trade': 1.0,
                            'target_rr': rr,
                            'adx_filter': adx,
                            'breakeven_trigger': be,
                            'trading_hours': (17, 23) # Evening session focus
                        }
                
                engine = BacktestEngine(df_15m, df_1h, CAPITAL, params)
                stats = engine.run()
                
                if "error" not in stats:
                    results.append({
                        'p': p, 'm': m, 'rr': rr, 'be': be, 'adx': adx,
                        'profit': stats['net_profit'],
                        'win_rate': stats['win_rate'],
                        'trades': stats['total_trades'],
                        'dd': stats['max_drawdown']
                    })
                    print(f"P:{p} M:{m} RR:{rr} BE:{be} ADX:{adx} -> Profit: {stats['net_profit']:.2f}")

    if results:
        res_df = pd.DataFrame(results)
        # Score = Profit / MaxDD (Return to Risk)
        res_df['score'] = res_df['profit'] / (res_df['dd'] + 0.1)
        best = res_df.sort_values('score', ascending=False).iloc[0]
        print("\n" + "="*40)
        print("          BEST PARAMETERS FOUND (Risk adjusted)")
        print("="*40)
        print(best)
        print("="*40)

if __name__ == "__main__":
    optimize_crude()
