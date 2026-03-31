import pandas as pd
import numpy as np

def calculate_supertrend(df: pd.DataFrame, period=31, multiplier=2):
    """
    Calculates Supertrend (period, multiplier) for a given DataFrame.
    Expected columns: 'open', 'high', 'low', 'close'
    Returns DataFrame with 'Supertrend', 'Trend' (1: Bullish, -1: Bearish)
    """
    # Ensure necessary columns exist
    for col in ['high', 'low', 'close']:
        if col not in df.columns:
            raise ValueError(f"DataFrame missing required column: {col}")

    high = df['high']
    low = df['low']
    close = df['close']
    
    # Calculate True Range (TR)
    # TR = max(high-low, abs(high-prev_close), abs(low-prev_close))
    price_diff = high - low
    h_c_diff = abs(high - close.shift(1))
    l_c_diff = abs(low - close.shift(1))
    
    tr = pd.concat([price_diff, h_c_diff, l_c_diff], axis=1).max(axis=1)
    
    # ATR Calculation using Wilder's Smoothing (EWM)
    # This matches standard TradingView/Groww Supertrend behavior
    atr = tr.ewm(alpha=1/period, min_periods=period).mean()

    # Basic Bands
    hl2 = (high + low) / 2
    basic_upper = hl2 + (multiplier * atr)
    basic_lower = hl2 - (multiplier * atr)

    # Final Bands Initialization
    final_upper = pd.Series(index=df.index, dtype='float64')
    final_lower = pd.Series(index=df.index, dtype='float64')
    trend = pd.Series(index=df.index, dtype='int64') # 1: Bullish, -1: Bearish
    supertrend = pd.Series(index=df.index, dtype='float64')

    # Iterative calculation for Supertrend (requires previous values)
    # Using numpy arrays for speed
    close_np = close.values
    bu_np = basic_upper.values
    bl_np = basic_lower.values
    fu_np = np.zeros(len(df))
    fl_np = np.zeros(len(df))
    st_np = np.zeros(len(df))
    trend_np = np.zeros(len(df))

    # Initialize first valid values (just to avoid errors, logic starts after 'period')
    for i in range(period, len(df)):
        # Final Upper
        # If Basic Upper < Prev Final Upper OR Prev Close > Prev Final Upper:
        #    Final Upper = Basic Upper
        # Else:
        #    Final Upper = Prev Final Upper
        if i == 0:
            fu_np[i] = bu_np[i]
            fl_np[i] = bl_np[i]
            trend_np[i] = 1 # default
            st_np[i] = fl_np[i]
        else:
            prev_fu = fu_np[i-1]
            prev_close = close_np[i-1]
            if (bu_np[i] < prev_fu) or (prev_close > prev_fu):
                fu_np[i] = bu_np[i]
            else:
                fu_np[i] = prev_fu
            
            # Final Lower
            prev_fl = fl_np[i-1]
            if (bl_np[i] > prev_fl) or (prev_close < prev_fl):
                fl_np[i] = bl_np[i]
            else:
                fl_np[i] = prev_fl

            # Trend
            # If Prev Trend == Bullish (1):
            #   If Close <= Final Lower: Trend = Bearish (-1)
            #   Else: Trend = Bullish (1)
            # Else (Prev Trend == Bearish):
            #   If Close > Final Upper: Trend = Bullish (1)
            #   Else: Trend = Bearish (-1)
            
            prev_trend = trend_np[i-1]
            if prev_trend == 1:
                if close_np[i] <= fl_np[i]:
                    trend_np[i] = -1
                    st_np[i] = fu_np[i]
                else:
                    trend_np[i] = 1
                    st_np[i] = fl_np[i]
            else: # prev_trend == -1 or 0
                # Initialize trend if 0 (first run)
                if prev_trend == 0:
                     # Initial assumption based on price vs bands
                     if close_np[i] > fu_np[i]:
                         trend_np[i] = 1
                         st_np[i] = fl_np[i]
                     else:
                         trend_np[i] = -1
                         st_np[i] = fu_np[i]
                elif close_np[i] >= fu_np[i]:
                    trend_np[i] = 1
                    st_np[i] = fl_np[i]
                else:
                    trend_np[i] = -1
                    st_np[i] = fu_np[i]

    df['Supertrend'] = st_np
    df['Trend'] = trend_np
    
    return df
