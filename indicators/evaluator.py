import pandas as pd
from indicators.supertrend import calculate_supertrend
from logger.logger import logger

def calculate_ema(df, fast, slow):
    df = df.copy()
    df[f'EMA_{fast}'] = df['close'].ewm(span=fast, adjust=False).mean()
    df[f'EMA_{slow}'] = df['close'].ewm(span=slow, adjust=False).mean()
    return df

def evaluate_signals(symbol, df, indicators_config):
    """
    Evaluates confluence: Only alerts when multiple (>=2) conditions agree.
    Triggers again if count improves (e.g. 2/3 -> 3/3).
    """
    if len(df) < 5: return []

    active_configs = [c for c in indicators_config if c.get('active', True) and (not c.get('symbol') or c.get('symbol') == symbol)]
    if not active_configs: return []

    def get_states(index):
        # Returns (bull_count, bear_count, names_bull, names_bear)
        bu, be = 0, 0
        n_bu, n_be = [], []
        
        for cfg in active_configs:
            try:
                itype = cfg['type']
                if itype == 'supertrend':
                    p, m = cfg.get('period', 31), cfg.get('multiplier', 2.0)
                    st = calculate_supertrend(df, p, m).iloc[index]['Trend']
                    if st == 1: bu += 1; n_bu.append(f"Supertrend({p},{m})")
                    else: be += 1; n_be.append(f"Supertrend({p},{m})")
                elif itype == 'ema':
                    length = cfg.get('length', 15)
                    ema_val = df['close'].ewm(span=length, adjust=False).mean().iloc[index]
                    if df.iloc[index]['close'] > ema_val: bu += 1; n_bu.append(f"EMA({length})")
                    else: be += 1; n_be.append(f"EMA({length})")
                elif itype == 'ema_cross':
                    short, long = cfg.get('short', 9), cfg.get('long', 15)
                    df_e = df.copy()
                    df_e['s'] = df_e['close'].ewm(span=short, adjust=False).mean()
                    df_e['l'] = df_e['close'].ewm(span=long, adjust=False).mean()
                    if df_e.iloc[index]['s'] > df_e.iloc[index]['l']: bu += 1; n_bu.append(f"EMA({short}/{long})")
                    else: be += 1; n_be.append(f"EMA({short}/{long})")
                elif itype == 'vwap':
                    src = cfg.get('source', 'hlc3')
                    df_v = df.iloc[:(len(df)+1+index)].copy()
                    df_v['date'] = pd.to_datetime(df_v['datetime']).dt.date
                    p_src = (df_v['high'] + df_v['low'] + df_v['close'])/3 if src=='hlc3' else df_v['close']
                    df_v['pv'] = p_src * df_v['volume']
                    g = df_v.groupby('date')
                    vwap = (g['pv'].cumsum() / g['volume'].cumsum()).iloc[-1]
                    if df_v.iloc[-1]['close'] > vwap: bu += 1; n_bu.append("VWAP")
                    else: be += 1; n_be.append("VWAP")
                elif itype == 'bb':
                    l, m = cfg.get('length', 20), cfg.get('mult', 2.0)
                    ma = df['close'].rolling(window=l).mean().iloc[index]
                    if df['close'].iloc[index] > ma: bu += 1; n_bu.append("BBands")
                    else: be += 1; n_be.append("BBands")
                elif itype == 'atr':
                    ma = df['close'].ewm(span=20, adjust=False).mean().iloc[index]
                    if df['close'].iloc[index] > ma: bu += 1; n_bu.append("ATR-Filter")
                    else: be += 1; n_be.append("ATR-Filter")
            except: pass
        return bu, be, n_bu, n_be

    c_bu, c_be, c_nb, c_nr = get_states(-1)
    p_bu, p_be, _, _ = get_states(-2)
    
    total = len(active_configs)
    threshold = 2 if total >= 2 else 1
    alerts = []
    
    if c_bu >= threshold:
        if p_bu < threshold or c_bu > p_bu:
            alerts.append({"algo_name": f"BUY ({c_bu}/{total})", "direction": f"BULLISH CONFLUENCE: {', '.join(c_nb)} 🚀", "close_price": df.iloc[-1]['close']})
    elif c_be >= threshold:
        if p_be < threshold or c_be > p_be:
            alerts.append({"algo_name": f"SELL ({c_be}/{total})", "direction": f"BEARISH CONFLUENCE: {', '.join(c_nr)} 🔻", "close_price": df.iloc[-1]['close']})

    return alerts
