import pandas as pd
import numpy as np

def calculate_ema(df, period, column='close'):
    return df[column].ewm(span=period, adjust=False).mean()

def calculate_supertrend(df, period=31, multiplier=2):
    high = df['high']
    low = df['low']
    close = df['close']
    
    price_diff = high - low
    h_c_diff = abs(high - close.shift(1))
    l_c_diff = abs(low - close.shift(1))
    tr = pd.concat([price_diff, h_c_diff, l_c_diff], axis=1).max(axis=1)
    
    # ATR Calculation using Wilder's Smoothing (EWM) to match main indicators
    atr = tr.ewm(alpha=1/period, min_periods=period).mean()

    hl2 = (high + low) / 2
    basic_upper = hl2 + (multiplier * atr)
    basic_lower = hl2 - (multiplier * atr)

    fu_np = np.zeros(len(df))
    fl_np = np.zeros(len(df))
    st_np = np.zeros(len(df))
    trend_np = np.zeros(len(df))

    close_np = close.values
    bu_np = basic_upper.values
    bl_np = basic_lower.values

    for i in range(1, len(df)):
        if i < period:
            # Skip until we have enough ATR data
            continue
            
        # Final Upper
        if (bu_np[i] < fu_np[i-1]) or (close_np[i-1] > fu_np[i-1]):
            fu_np[i] = bu_np[i]
        else:
            fu_np[i] = fu_np[i-1]
        
        # Final Lower
        if (bl_np[i] > fl_np[i-1]) or (close_np[i-1] < fl_np[i-1]):
            fl_np[i] = bl_np[i]
        else:
            fl_np[i] = fl_np[i-1]

        # Trend and Supertrend
        prev_trend = trend_np[i-1]
        if prev_trend == 1:
            if close_np[i] <= fl_np[i]:
                trend_np[i] = -1
                st_np[i] = fu_np[i]
            else:
                trend_np[i] = 1
                st_np[i] = fl_np[i]
        elif prev_trend == -1:
            if close_np[i] >= fu_np[i]:
                trend_np[i] = 1
                st_np[i] = fl_np[i]
            else:
                trend_np[i] = -1
                st_np[i] = fu_np[i]
        else:
            # First assignment of trend
            if close_np[i] > fu_np[i]:
                trend_np[i] = 1
                st_np[i] = fl_np[i]
            else:
                trend_np[i] = -1
                st_np[i] = fu_np[i]

    return st_np, trend_np

def calculate_vwap(df):
    """Calculates VWAP with daily reset."""
    v = df['volume']
    tp = (df['high'] + df['low'] + df['close']) / 3
    
    # Group by date to reset
    groups = df.groupby(df.index.date)
    
    def vwap_group(group):
        q = group['volume']
        p = (group['high'] + group['low'] + group['close']) / 3
        return (p * q).cumsum() / q.cumsum()
    
    return groups.apply(vwap_group).reset_index(level=0, drop=True)

def calculate_adx(df, period=14):
    """Average Directional Index using Wilder's Smoothing."""
    high = df['high']
    low = df['low']
    close = df['close']
    
    # DM (Directional Movement)
    up_move = high.diff()
    down_move = low.diff().abs()
    
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    
    # TR (True Range)
    tr = pd.concat([high - low, abs(high - close.shift(1)), abs(low - close.shift(1))], axis=1).max(axis=1)
    
    # ATR and Smoothed DM
    tr_s = tr.ewm(alpha=1/period, adjust=False).mean()
    plus_dm_s = pd.Series(plus_dm, index=df.index).ewm(alpha=1/period, adjust=False).mean()
    minus_dm_s = pd.Series(minus_dm, index=df.index).ewm(alpha=1/period, adjust=False).mean()
    
    # DI
    plus_di = 100 * (plus_dm_s / tr_s)
    minus_di = 100 * (minus_dm_s / tr_s)
    
    # DX and ADX
    dx = 100 * (abs(plus_di - minus_di) / (plus_di + minus_di))
    adx = dx.ewm(alpha=1/period, adjust=False).mean()
    
    return adx
