import os
import sys
import pandas as pd
from datetime import datetime, timedelta
import pytz

# Add parent directory to path to access existing modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import API_KEY, CLIENT_ID, PASSWORD, TOTP_KEY, DELTA_API_KEY, DELTA_API_SECRET
from data.token_lookup import get_token_info
from broker.delta_exchange import DeltaExchange
import pyotp
from SmartApi import SmartConnect

def get_session():
    smartApi = SmartConnect(api_key=API_KEY)
    totp = pyotp.TOTP(TOTP_KEY).now()
    data = smartApi.generateSession(CLIENT_ID, PASSWORD, totp)
    if not data['status']:
        print(f"Login failed: {data['message']}")
        return None
    return smartApi

def fetch_angel_data(smartApi, symbol, exchange, interval, days=30):
    token_map = get_token_info([symbol])
    if symbol not in token_map:
        print(f"Token not found for {symbol}")
        return None
    
    info = token_map[symbol]
    token = info['token']
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    params = {
        "exchange": info['exchange'],
        "symboltoken": token,
        "interval": interval,
        "fromdate": start_date.strftime('%Y-%m-%d %H:%M'),
        "todate": end_date.strftime('%Y-%m-%d %H:%M')
    }
    
    response = smartApi.getCandleData(params)
    if response['status'] and response['data']:
        df = pd.DataFrame(response['data'], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        # Convert to numeric
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col])
        return df
    else:
        print(f"Error fetching data: {response.get('message')}")
        return None

def fetch_delta_data(symbol, resolution="15m", days=30):
    delta = DeltaExchange(on_tick_callback=None, api_key=DELTA_API_KEY, api_secret=DELTA_API_SECRET)
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=days)
    
    # Delta returns newest first? No, the code sorts it.
    candles = delta.get_historical_data(symbol, resolution=resolution, start_time=start_time, end_time=end_time)
    if candles:
        df = pd.DataFrame(candles)
        df.rename(columns={'start_time': 'timestamp'}, inplace=True)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        return df
    return None

def get_backtest_data(symbol, exchange='NSE', days=30):
    """
    Fetches data for both execution (15m) and filter (1H) timeframes.
    """
    cache_path = f"data/{symbol}_{days}d.csv"
    if os.path.exists(cache_path):
        print(f"Loading {symbol} from cache...")
        df_15m = pd.read_csv(cache_path, index_col='timestamp', parse_dates=True)
    else:
        print(f"Fetching fresh data for {symbol}...")
        if exchange in ['NSE', 'MCX']:
            api = get_session()
            df_15m = fetch_angel_data(api, symbol, exchange, "FIFTEEN_MINUTE", days=days)
        else:
            df_15m = fetch_delta_data(symbol, resolution="15m", days=days)
        
        if df_15m is not None:
             # Create directory if not exists
             os.makedirs('data', exist_ok=True)
             df_15m.to_csv(cache_path)
             
    if df_15m is None:
        return None, None

    # Resample to 1H for the filter
    df_1h = df_15m.resample('1H').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    
    return df_15m, df_1h
