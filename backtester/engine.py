import pandas as pd
import numpy as np
from datetime import datetime, time
from .indicators import calculate_ema, calculate_supertrend, calculate_vwap, calculate_adx
from .config import (
    EMA_FAST, EMA_SLOW, EMA_FILTER, SUPERTREND_PERIOD, SUPERTREND_MULTIPLIER,
    CAPITAL, RISK_PER_TRADE_PERCENT, TARGET_RR, MAX_CONSECUTIVE_LOSSES,
    MAX_DAILY_DRAWDOWN_PERCENT, MAX_DISTANCE_FROM_EMA_PERCENT
)

class BacktestEngine:
    def __init__(self, df_15m, df_1h, initial_capital=CAPITAL, params=None):
        self.df_15m = df_15m.copy()
        self.df_1h = df_1h.copy()
        self.capital = initial_capital
        self.equity_curve = [initial_capital]
        self.drawdown_curve = [0]
        self.trades = []
        self.max_equity = initial_capital
        
        # Strategy Parameters
        self.params = params or {
            'ema_fast': EMA_FAST,
            'ema_slow': EMA_SLOW,
            'ema_filter': EMA_FILTER,
            'st_period': SUPERTREND_PERIOD,
            'st_multiplier': SUPERTREND_MULTIPLIER,
            'risk_per_trade': RISK_PER_TRADE_PERCENT,
            'target_rr': TARGET_RR,
            'adx_filter': 0,
            'breakeven_trigger': 0.8, # Move SL to BE at 0.8R profit
            'trading_hours': (9, 23)   # Start/End hour
        }
        
        # Risk State
        self.current_day = None
        self.daily_pnl = 0
        self.daily_losses = 0
        self.stop_trading_today = False
        self.consecutive_losses = 0
        self.max_consecutive_losses = 0
        self.is_breakeven = False # Tracking state per trade

    def prepare_indicators(self):
        # 15m Indicators
        self.df_15m['ema_9'] = calculate_ema(self.df_15m, self.params['ema_fast'])
        self.df_15m['ema_15'] = calculate_ema(self.df_15m, self.params['ema_slow'])
        st, trend = calculate_supertrend(self.df_15m, self.params['st_period'], self.params['st_multiplier'])
        self.df_15m['supertrend'] = st
        self.df_15m['st_trend'] = trend
        self.df_15m['vwap'] = calculate_vwap(self.df_15m)
        self.df_15m['adx'] = calculate_adx(self.df_15m)
        
        # Slopes (Approximated by diff)
        self.df_15m['ema_9_slope'] = self.df_15m['ema_9'].diff()
        self.df_15m['ema_15_slope'] = self.df_15m['ema_15'].diff()
        
        # 1H Indicators
        self.df_1h['ema_20'] = calculate_ema(self.df_1h, self.params['ema_filter'])
        
        # Forward fill 1H data to 15m
        self.df_1h_mapped = self.df_1h[['ema_20', 'close']].shift(1).rename(columns={'close': 'close_1h'})
        self.df_15m = self.df_15m.join(self.df_1h_mapped, how='left', rsuffix='_1h')
        self.df_15m['ema_20_1h'] = self.df_15m['ema_20'].ffill()
        self.df_15m['close_1h'] = self.df_15m['close_1h'].ffill()

    def run(self):
        self.prepare_indicators()
        
        position = None # {'type': 'LONG'/'SHORT', 'entry_price': float, 'sl': float, 'tp': float, 'qty': int}
        
        for i in range(1, len(self.df_15m)):
            current_row = self.df_15m.iloc[i]
            timestamp = self.df_15m.index[i]
            
            # Reset daily limits
            if self.current_day != timestamp.date():
                self.current_day = timestamp.date()
                self.daily_pnl = 0
                self.daily_losses = 0
                self.stop_trading_today = False

            # Check for exits if in position
            if position:
                exit_price = None
                exit_reason = None
                
                # Dynamic Breakeven Tracking
                if not self.is_breakeven:
                    # SL is at original sl. Check if profit hit trigger.
                    profit_at_risk = abs(current_row['close'] - position['entry_price']) / abs(position['entry_price'] - position['sl'])
                    if profit_at_risk >= self.params['breakeven_trigger']:
                        position['sl'] = position['entry_price']
                        self.is_breakeven = True

                # SL/TP Checks
                if position['type'] == 'LONG':
                    if current_row['low'] <= position['sl']:
                        exit_price = position['sl']
                        exit_reason = 'SL/BE'
                    elif current_row['high'] >= position['tp']:
                        exit_price = position['tp']
                        exit_reason = 'TP'
                    # More lenient trailing: only exit if trend flips or huge drop
                    elif current_row['st_trend'] == -1: 
                        exit_price = current_row['close']
                        exit_reason = 'Trend Flip'
                else: # SHORT
                    if current_row['high'] >= position['sl']:
                        exit_price = position['sl']
                        exit_reason = 'SL/BE'
                    elif current_row['low'] <= position['tp']:
                        exit_price = position['tp']
                        exit_reason = 'TP'
                    elif current_row['st_trend'] == 1:
                        exit_price = current_row['close']
                        exit_reason = 'Trend Flip'
                
                if exit_price:
                    pnl = (exit_price - position['entry_price']) * position['qty']
                    if position['type'] == 'SHORT': pnl = -pnl
                    
                    self.capital += pnl
                    self.daily_pnl += pnl
                    
                    if pnl < 0:
                        self.daily_losses += 1
                        self.consecutive_losses += 1
                        self.max_consecutive_losses = max(self.max_consecutive_losses, self.consecutive_losses)
                    else:
                        self.consecutive_losses = 0
                        
                    self.trades.append({
                        'exit_time': timestamp,
                        'entry_time': position['entry_time'],
                        'type': position['type'],
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price,
                        'pnl': pnl,
                        'reason': exit_reason,
                        'equity': self.capital
                    })
                    
                    # Check daily risk rules
                    if self.daily_losses >= MAX_CONSECUTIVE_LOSSES:
                        self.stop_trading_today = True
                    if self.daily_pnl <= -(self.equity_curve[-1] * MAX_DAILY_DRAWDOWN_PERCENT / 100):
                        self.stop_trading_today = True
                        
                    position = None
                    self.is_breakeven = False # Reset for next trade

            # Equity Tracking
            self.equity_curve.append(self.capital)
            self.max_equity = max(self.max_equity, self.capital)
            self.drawdown_curve.append((self.max_equity - self.capital) / self.max_equity * 100)

            # Look for Entries if NOT in position and NOT stopped for the day
            if not position and not self.stop_trading_today:
                # Time Filter
                h_start, h_end = self.params.get('trading_hours', (0, 24))
                if not (h_start <= timestamp.hour < h_end):
                    continue

                # Volatility Filter
                if self.params['adx_filter'] > 0 and current_row['adx'] < self.params['adx_filter']:
                    continue

                # 1H Filter
                if pd.isna(current_row['close_1h']) or pd.isna(current_row['ema_20_1h']):
                    continue
                
                bias = 'LONG' if current_row['close_1h'] > current_row['ema_20_1h'] else 'SHORT'
                
                # 15m Rules
                dist_ema9 = abs(current_row['close'] - current_row['ema_9']) / current_row['ema_9'] * 100
                
                if bias == 'LONG':
                    if (current_row['st_trend'] == 1 and 
                        current_row['ema_9'] > current_row['ema_15'] and 
                        current_row['ema_9_slope'] > 0 and 
                        current_row['ema_15_slope'] > 0 and 
                        current_row['close'] > current_row['vwap'] and 
                        dist_ema9 < MAX_DISTANCE_FROM_EMA_PERCENT):
                        
                        sl_dist = current_row['close'] - min(current_row['low'], current_row['ema_15'])
                        sl_price = current_row['close'] - sl_dist
                        
                        max_sl_dist = current_row['close'] * 0.01
                        if sl_dist > max_sl_dist:
                            sl_dist = max_sl_dist
                            sl_price = current_row['close'] - sl_dist
                        
                        risk_amt = self.capital * (self.params['risk_per_trade'] / 100)
                        qty = int(risk_amt / sl_dist) if sl_dist > 0 else 0
                        
                        if qty > 0:
                            position = {
                                'type': 'LONG',
                                'entry_price': current_row['close'],
                                'entry_time': timestamp,
                                'sl': sl_price,
                                'tp': current_row['close'] + (sl_dist * self.params['target_rr']),
                                'qty': qty
                            }
                
                elif bias == 'SHORT':
                    if (current_row['st_trend'] == -1 and 
                        current_row['ema_9'] < current_row['ema_15'] and 
                        current_row['ema_9_slope'] < 0 and 
                        current_row['ema_15_slope'] < 0 and 
                        current_row['close'] < current_row['vwap'] and 
                        dist_ema9 < MAX_DISTANCE_FROM_EMA_PERCENT):
                        
                        sl_dist = max(current_row['high'], current_row['ema_15']) - current_row['close']
                        sl_price = current_row['close'] + sl_dist
                        
                        max_sl_dist = current_row['close'] * 0.01
                        if sl_dist > max_sl_dist:
                            sl_dist = max_sl_dist
                            sl_price = current_row['close'] + sl_dist
                            
                        risk_amt = self.capital * (self.params['risk_per_trade'] / 100)
                        qty = int(risk_amt / sl_dist) if sl_dist > 0 else 0
                        
                        if qty > 0:
                            position = {
                                'type': 'SHORT',
                                'entry_price': current_row['close'],
                                'entry_time': timestamp,
                                'sl': sl_price,
                                'tp': current_row['close'] - (sl_dist * self.params['target_rr']),
                                'qty': qty
                            }

        return self.get_stats()

    def get_stats(self):
        if not self.trades:
            return {"error": "No trades executed"}
            
        trade_df = pd.DataFrame(self.trades)
        net_profit = self.capital - CAPITAL
        win_rate = (len(trade_df[trade_df['pnl'] > 0]) / len(trade_df)) * 100
        
        gross_profit = trade_df[trade_df['pnl'] > 0]['pnl'].sum()
        gross_loss = abs(trade_df[trade_df['pnl'] < 0]['pnl'].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        expectancy = (win_rate/100 * (gross_profit/len(trade_df[trade_df['pnl']>0]) if any(trade_df['pnl']>0) else 0)) + \
                     ((1-win_rate/100) * (trade_df[trade_df['pnl']<0]['pnl'].mean() if any(trade_df['pnl']<0) else 0))
                     
        returns = pd.Series(self.equity_curve).pct_change().dropna()
        sharpe = (returns.mean() / returns.std()) * np.sqrt(252 * 6.5 * 4) if len(returns) > 1 else 0 # 15m bars in a year? approx
        
        return {
            'net_profit': net_profit,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'expectancy': expectancy,
            'max_drawdown': max(self.drawdown_curve),
            'sharpe_ratio': sharpe,
            'consecutive_losses': self.max_consecutive_losses,
            'total_trades': len(trade_df),
            'equity_curve': self.equity_curve,
            'drawdown_curve': self.drawdown_curve,
            'trades': trade_df
        }
