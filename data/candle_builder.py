from datetime import datetime, timedelta
import pandas as pd
from logger.logger import logger
import pytz

IST = pytz.timezone('Asia/Kolkata')

class CandleBuilder:
    def __init__(self, timeframe_minutes=15):
        self.timeframe = timeframe_minutes
        # Dictionary to store current candle state for each token
        # { token: { 'open': float, 'high': float, 'low': float, 'close': float, 'volume': int, 'start_time': datetime } }
        self.current_candles = {}
        # Store completed candles in a DataFrame-friendly format or just list
        # { token: [ {timestamp, open, high, low, close}, ... ] }
        self.history = {}
        # Store timeframes per symbol
        self.symbol_timeframes = {}

    def get_candle_start_time(self, timestamp: datetime, timeframe_override=None):
        """
        Calculates the start time of the candle for a given timestamp.
        15 min candles: 9:00, 9:15, 9:30...
        """
        # Ensure timestamp is datetime
        minute = timestamp.minute
        hour = timestamp.hour
        
        timeframe = timeframe_override if timeframe_override else self.timeframe
        
        # Round down to nearest timeframe interval
        start_minute = (minute // timeframe) * timeframe
        start_time = timestamp.replace(minute=start_minute, second=0, microsecond=0)
        return start_time

    def update_tick(self, token, ltp, timestamp: datetime, timeframe=None, on_candle_close_callback=None):
        """
        Updates the current candle with a new tick.
        If a new candle starts, closes the previous one and calls the callback.
        """
        if timeframe:
            self.symbol_timeframes[token] = timeframe
        else:
            timeframe = self.symbol_timeframes.get(token, self.timeframe)

        if token not in self.current_candles:
            # Initialize new candle
            candle_start = self.get_candle_start_time(timestamp, timeframe)
            self.current_candles[token] = {
                'open': ltp,
                'high': ltp,
                'low': ltp,
                'close': ltp,
                'start_time': candle_start
            }
            if token not in self.history:
                self.history[token] = []
            return

        current_candle = self.current_candles[token]
        tick_candle_start = self.get_candle_start_time(timestamp, timeframe)

        # Check if we moved to a new candle
        if tick_candle_start > current_candle['start_time']:
            # Close the current candle
            completed_candle = current_candle.copy()
            completed_candle['close_time'] = tick_candle_start # The start of next is effectively end of current for checking
            
            # Store it
            self.history[token].append(completed_candle)
            
            # Log
            logger.info(f"Candle closed for {token} at {completed_candle['start_time']}: {completed_candle}")
            
            # Trigger Callback (process logic for completed candle)
            if on_candle_close_callback:
                on_candle_close_callback(token, completed_candle)
            
            # Start new candle
            self.current_candles[token] = {
                'open': ltp,
                'high': ltp,
                'low': ltp,
                'close': ltp,
                'start_time': tick_candle_start
            }
        else:
            # Update current candle
            current_candle['high'] = max(current_candle['high'], ltp)
            current_candle['low'] = min(current_candle['low'], ltp)
            current_candle['close'] = ltp
            # Time update not strictly needed as start_time is fixed

    def get_history_df(self, token):
        """
        Returns the history of a token as a Pandas DataFrame
        """
        if token not in self.history:
            return pd.DataFrame()
        
        df = pd.DataFrame(self.history[token])
        if not df.empty:
            df = df.set_index('start_time')
            df.sort_index(inplace=True)
        return df
