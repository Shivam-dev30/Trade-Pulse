import os
import time
import sys
import pyotp
from datetime import datetime, timedelta
from SmartApi import SmartConnect
from config.settings import (
    API_KEY, CLIENT_ID, PASSWORD, TOTP_KEY, 
    SUPERTREND_PERIOD, SUPERTREND_MULTIPLIER,
    DELTA_WATCHLIST, DELTA_API_KEY, DELTA_API_SECRET
)
from broker.angel_websocket import AngelWebSocket
from broker.delta_exchange import DeltaExchange
from data.candle_builder import CandleBuilder
from data.token_lookup import get_token_info
from indicators.evaluator import evaluate_signals
from alerts.email_service import send_alert, format_generic_alert
from logger.logger import logger
import threading
import config_server

# Configuration
WATCHLIST_SYMBOLS = ["TCS", "RELIANCE", "CRUDEOIL", "GOLD"]

def get_smart_api_session():
    """Authenticates and returns the SmartConnect object and tokens."""
    try:
        smartApi = SmartConnect(api_key=API_KEY)
        try:
            totp = pyotp.TOTP(TOTP_KEY).now()
        except Exception as e:
            logger.error(f"Invalid TOTP Key: {e}")
            return None, None, None
        
        data = smartApi.generateSession(CLIENT_ID, PASSWORD, totp)
        if data['status'] == False:
            logger.error(f"Login failed: {data['message']}")
            return None, None, None
            
        auth_token = data['data']['jwtToken']
        feed_token = data['data']['feedToken']
        return smartApi, auth_token, feed_token
    except Exception as e:
        logger.error(f"Error during login: {e}")
        return None, None, None

def on_candle_close(token, candle_data, is_historical=False):
    """Callback when a candle closes."""
    symbol = token_to_symbol.get(token, token)
    df = candle_builder.get_history_df(token)
    
    # Pull dynamic configuration from the API state
    try:
        conf = config_server.load_config()
    except Exception as e:
        logger.error(f"Failed to load dynamic config: {e}")
        return

    # Determine market context
    is_crypto = symbol.endswith("USD") or symbol.endswith("USDT")
    if is_crypto and not conf.get('crypto_enabled', True):
        return
    if not is_crypto and not conf.get('indian_enabled', True):
        return
        
    # Get active algorithms for this market
    indicators = conf.get('crypto_indicators', []) if is_crypto else conf.get('indian_indicators', [])
    
    # Delegate to the generalized evaluator
    alerts = evaluate_signals(symbol, df, indicators)
    
    # Process alerts
    for alert in alerts:
        last_dt = df.index[-1]
        timestamp_str = last_dt.strftime('%I:%M %p IST')
        
        # We only send startup alerts if we are actively checking history and it happened on the CURRENT edge candle
        # To avoid spamming on a restart, evaluator returns flips on the *last* 2 candles anyway.
        algo_name = alert.get("algo_name", "Algorithm")
        direction = alert.get("direction", "Unknown")
        price = alert.get("close_price", 0.0)
        
        subject, body = format_generic_alert(symbol, direction, price, timestamp_str, algo_name)
        
        if is_historical:
            subject = f"🕒 Startup Signal: {symbol}"
            body = f"NOTE: Bot reboot detected recent activity.\n\n{body}"
            logger.info(f"Startup Alert: {symbol} via {algo_name}")
            send_alert(subject, body)
        else:
            logger.info(f"Live Alert: {symbol} via {algo_name}")
            send_alert(subject, body)

def websocket_tick_handler(message):
    """Parses WebSocket message and updates CandleBuilder."""
    ticks = message if isinstance(message, list) else [message]
    for tick in ticks:
        if 'token' not in tick: continue
        
        # Check if Indian market is enabled before processing
        # Optimizing: using a cached config check to avoid file I/O on every tick
        # (Assuming config state is updated occasionally in the main loop)
        # if not getattr(config_server, 'indian_enabled', True): return
        
        token = tick['token']
        ltp = tick.get('last_traded_price')
        if ltp is None: continue
            
        info = token_to_info.get(token, {})
        exchange = info.get('exchange', 'NSE')
        
        # Unit correction: Angel One WebSocket sends prices in Paise for all segments.
        # We divide by 100.0 to get standard Rupee units.
        price = float(ltp) / 100.0
        
        # Update live prices for UI
        symbol = token_to_symbol.get(token, token)
        config_server.live_prices[symbol] = price
        
        # Determine timeframe
        tf = symbol_to_params.get(symbol, {}).get('timeframe', 15)
            
        candle_builder.update_tick(token, price, datetime.now(), timeframe=tf, on_candle_close_callback=on_candle_close)

last_log_time = {}

def delta_tick_handler(symbol, price, timestamp):
    """Callback for Delta Exchange ticks."""
    import time
    global last_log_time
    # Heartbeat log every 60 seconds to satisfy user visibility
    now_ts = time.time()
    if symbol not in last_log_time or (now_ts - last_log_time.get(symbol, 0)) > 60:
        formatted_price = f"{price:.5f}".rstrip('0').rstrip('.') if price < 10 else f"{price:.2f}"
        logger.info(f"D-LIVE: Captured tick for {symbol} at ${formatted_price}")
        last_log_time[symbol] = now_ts
        
    # Update live prices for UI
    config_server.live_prices[symbol] = price
    
    # Determine timeframe
    tf = symbol_to_params.get(symbol, {}).get('timeframe', 15)
        
    candle_builder.update_tick(symbol, price, timestamp, timeframe=tf, on_candle_close_callback=on_candle_close)

# Global Objects
candle_builder = CandleBuilder(timeframe_minutes=15)
token_to_symbol = {}
token_to_info = {}
# Cached map for symbology and parameters (to avoid frequent file I/O)
symbol_to_params = {}

def update_global_params(conf):
    """Refreshes the global symbol parameters from config to optimize tick processing."""
    global symbol_to_params
    new_params = {}
    for ind in conf.get('indian_indicators', []) + conf.get('crypto_indicators', []):
        if ind.get('symbol'):
            new_params[ind['symbol']] = ind
    symbol_to_params = new_params

def pre_populate_history(smartApi, symbol_data_map):
    """Fetches historical 15m candles."""
    import pytz
    logger.info("Pre-populating historical data...")
    end_date = datetime.now(pytz.timezone('Asia/Kolkata'))
    start_date = end_date - timedelta(days=5) 
    
    for symbol, info in symbol_data_map.items():
        token = info['token']
        exchange = info['exchange']
        try:
            params = {
                "exchange": exchange, "symboltoken": token, "interval": "FIFTEEN_MINUTE",
                "fromdate": start_date.strftime('%Y-%m-%d %H:%M'),
                "todate": end_date.strftime('%Y-%m-%d %H:%M')
            }
            response = smartApi.getCandleData(params)
            
            if response['status'] and response['data']:
                candles = response['data']
                history_list = []
                for c in candles:
                    ts = datetime.fromisoformat(c[0]).replace(tzinfo=None)
                    history_list.append({
                        'start_time': ts, 'open': float(c[1]), 'high': float(c[2]), 
                        'low': float(c[3]), 'close': float(c[4])
                    })
                # Identify if the last candle is the one currently in progress
                current_time_bin = candle_builder.get_candle_start_time(datetime.now())
                last_hist_candle = history_list[-1]
                
                if last_hist_candle['start_time'] == current_time_bin:
                    # Initialize the active candle so we have exact Open, High, Low from history
                    candle_builder.current_candles[token] = last_hist_candle
                    # The rest go to history (excluding the current one)
                    candle_builder.history[token] = history_list[:-1][-100:]
                else:
                    # All are completed candles
                    candle_builder.history[token] = history_list[-100:]
                
                # Report latest status for the 30-min flip check
                last_comp_candle = history_list[-1] if last_hist_candle['start_time'] != current_time_bin else history_list[-2]
                on_candle_close(token, last_comp_candle, is_historical=True)
            else:
                logger.warning(f"Failed history for {symbol}: {response.get('message')}")
        except Exception as e:
            logger.error(f"Error pre-populating {symbol}: {e}")

def pre_populate_delta_history(delta_exchange):
    """Fetches historical 15m candles for Delta Exchange."""
    import pytz
    logger.info("Pre-populating Delta Exchange history...")
    ist = pytz.timezone('Asia/Kolkata')
    
    for symbol in DELTA_WATCHLIST:
        try:
            history = delta_exchange.get_historical_data(symbol, resolution="15m")
            if not history:
                continue
            
            # Convert UTC timestamps to local/IST naive (to match system convention)
            converted_history = []
            for c in history:
                # c['start_time'] from Delta wrapper is UTC naive
                utc_dt = c['start_time'].replace(tzinfo=pytz.utc)
                local_dt = utc_dt.astimezone(ist)
                naive_dt = local_dt.replace(tzinfo=None)
                
                c['start_time'] = naive_dt
                converted_history.append(c)
            
            history_list = converted_history
            
            # Logic to separate current vs completed
            current_time_bin = candle_builder.get_candle_start_time(datetime.now())
            last_hist_candle = history_list[-1]
            
            if last_hist_candle['start_time'] == current_time_bin:
                candle_builder.current_candles[symbol] = last_hist_candle
                candle_builder.history[symbol] = history_list[:-1][-100:]
            else:
                candle_builder.history[symbol] = history_list[-100:]
                
            # Run initial check
            last_comp_candle = history_list[-1] if last_hist_candle['start_time'] != current_time_bin else history_list[-2]
            on_candle_close(symbol, last_comp_candle, is_historical=True)
            
        except Exception as e:
            logger.error(f"Error pre-populating Delta {symbol}: {e}")

def main():
    logger.info("Starting Supertrend Alert System...")
    smartApi, auth_token, feed_token = get_smart_api_session()
    if not smartApi: return

    global token_to_symbol, token_to_info, DELTA_WATCHLIST
    symbol_info = get_token_info(WATCHLIST_SYMBOLS)
    if not symbol_info:
        logger.error("No tokens found. Exiting.")
        return
        
    token_to_symbol = {v['token']: k for k, v in symbol_info.items()}
    token_to_info = {v['token']: v for k, v in symbol_info.items()}
    logger.info(f"Monitoring: {list(symbol_info.keys())}")
    
    # --- Internal Config Server API (Start Early) ---
    logger.info("Starting UI Configuration Dashboard (Port 5000)...")
    server_thread = threading.Thread(target=config_server.start_server)
    server_thread.daemon = True
    server_thread.start()
    # ----------------------------------

    ws = AngelWebSocket(auth_token, API_KEY, CLIENT_ID, feed_token)
    ws.add_callback(websocket_tick_handler)
    
    subscriptions = []
    nse_tokens = [v['token'] for v in symbol_info.values() if v['exchange'] == 'NSE']
    mcx_tokens = [v['token'] for v in symbol_info.values() if v['exchange'] == 'MCX']
    
    if nse_tokens: subscriptions.append({"exchangeType": 1, "tokens": nse_tokens})
    if mcx_tokens: subscriptions.append({"exchangeType": 5, "tokens": mcx_tokens})
    
    # Start Angel WebSocket and its history in a separate thread
    def start_angel():
        pre_populate_history(smartApi, symbol_info)
        ws.connect(subscribe_tokens=subscriptions, mode=1)

    angel_thread = threading.Thread(target=start_angel)
    angel_thread.daemon = True
    angel_thread.start()

    # --- Delta Exchange Setup ---
    # Merge symbols from stored config into watchlist at startup
    stored_conf = config_server.load_config()
    stored_crypto = [ind.get('symbol') for ind in stored_conf.get('crypto_indicators', []) if ind.get('symbol')]
    DELTA_WATCHLIST = list(set(DELTA_WATCHLIST + stored_crypto))
    
    if DELTA_WATCHLIST:
        logger.info(f"Starting Delta Exchange for: {DELTA_WATCHLIST}")
        # Add to token map (Symbol -> Symbol)
        for sym in DELTA_WATCHLIST:
            token_to_symbol[sym] = sym
            
        delta_ex = DeltaExchange(
            on_tick_callback=delta_tick_handler,
            api_key=DELTA_API_KEY,
            api_secret=DELTA_API_SECRET
        )
        # delta_ex.connect_websocket(DELTA_WATCHLIST)
        # Wrap delta connection and history in a thread to prevent blocking main dashboard
        def start_delta():
            pre_populate_delta_history(delta_ex)
            delta_ex.connect_websocket(DELTA_WATCHLIST)
        
        delta_thread = threading.Thread(target=start_delta)
        delta_thread.daemon = True
        delta_thread.start()
    # ----------------------------


    # Keep main thread alive and watch for dynamically added symbols
    while True:
        try:
            conf = config_server.load_config()
            crypto_inds = conf.get('crypto_indicators', [])
            active_crypto = list(set([ind.get('symbol') for ind in crypto_inds if ind.get('symbol')]))
            
            if 'delta_ex' in locals():
                missing_symbols = [s for s in active_crypto if s not in delta_ex.symbols]
                excess_symbols = [s for s in delta_ex.symbols if s not in active_crypto]
                
                if missing_symbols:
                    logger.info(f"Dynamically adding new Crypto pairs to active streams: {missing_symbols}")
                    for sym in missing_symbols:
                        token_to_symbol[sym] = sym
                    
                    # Temporarily push them to WATCHLIST for prepopulation loop to find them
                    old_watchlist = DELTA_WATCHLIST.copy()
                    DELTA_WATCHLIST = [s for s in DELTA_WATCHLIST if s not in excess_symbols] + missing_symbols
                    pre_populate_delta_history(delta_ex)
                    
                    delta_ex.add_symbols(missing_symbols)
                    
                    delta_ex.remove_symbols(excess_symbols)
                    DELTA_WATCHLIST = [s for s in DELTA_WATCHLIST if s not in excess_symbols]
                    
            # --- Sync Indian (Angel) Watchlist ---
            update_global_params(conf)
            indian_inds = conf.get('indian_indicators', [])
            active_indian = [ind.get('symbol') for ind in indian_inds if ind.get('symbol') and ind.get('active')]
            
            # Unsubscribe from NSE if global Indian toggle is off
            if not conf.get('indian_enabled', True):
                active_indian = []
                
            # If logic for Angel One unsubscription is needed...
            # Note: Angel WebSocket doesn't support 'unsubscribe' as easily in some wrapper versions
            # but we can at least filter them in the tick handler.
            
            # --- Sync Live Prices Removal (Optional Cleanup) ---
            # Remove symbols that are no longer active from the live dashboard
            current_active_all = active_indian + active_crypto
            keys_to_del = [k for k in config_server.live_prices.keys() if k not in current_active_all]
            for k in keys_to_del: del config_server.live_prices[k]
        except Exception as e:
            logger.error(f"Dynamic subscription loop error: {e}")
            
        time.sleep(5)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Stopping...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Bot Crashed. Error: {e}")
        # Ideally we shouldn't just restart blindly in a loop if it's a config error, 
        # but for now we follow the user's previous pattern or just exit.
        sys.exit(1)
