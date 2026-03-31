import requests
import json
import threading
import time
import websocket
from datetime import datetime, timedelta
from logger.logger import logger

class DeltaExchange:
    def __init__(self, on_tick_callback, api_key=None, api_secret=None):
        self.base_url = "https://api.delta.exchange"
        self.socket_url = "wss://socket.delta.exchange"
        self.on_tick_callback = on_tick_callback
        self.api_key = api_key
        self.api_secret = api_secret
        self.ws = None
        self.wst = None
        self.symbols = []
        self.should_continue = True

    def _generate_signature(self, method, timestamp, path, query_string, payload=""):
        import hmac
        import hashlib
        if not self.api_secret:
            return None
        
        signature_data = method + timestamp + path + query_string + payload
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            signature_data.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature

    def _get_headers(self, method, path, query_string="", payload=""):
        if not self.api_key or not self.api_secret:
            return {}
            
        timestamp = str(int(time.time()))
        signature = self._generate_signature(method, timestamp, path, query_string, payload)
        
        return {
            "api-key": self.api_key,
            "timestamp": timestamp,
            "signature": signature,
            "User-Agent": "SupertrendBot/1.0"
        }

    def get_historical_data(self, symbol, resolution="15m", start_time=None, end_time=None):
        """
        Fetches historical k-line data from Delta Exchange.
        """
        endpoint = "/v2/history/candles"
        url = self.base_url + endpoint
        
        # Default to last 5 days if not provided
        if not end_time:
            end_time = datetime.utcnow()
        if not start_time:
            start_time = end_time - timedelta(days=2)

        params = {
            "symbol": symbol,
            "resolution": resolution,
            "start": int(start_time.timestamp()),
            "end": int(end_time.timestamp())
        }
        # Prepare query string for signature (without ?)
        # import urllib.parse
        # query_string = urllib.parse.urlencode(params)
        # headers = self._get_headers("GET", endpoint, query_string)
        
        try:
            # Historical data is public, no auth needed
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data['success'] and data['result']:
                # Delta returns: [timestamp, open, high, low, close, volume]
                # timestamp is in seconds
                candles = []
                for c in data['result']:
                    ts = datetime.utcfromtimestamp(c['time'])
                    candles.append({
                        'start_time': ts,
                        'open': float(c['open']),
                        'high': float(c['high']),
                        'low': float(c['low']),
                        'close': float(c['close']),
                        'volume': float(c['volume'])
                    })
                # Delta returns newest first? or oldest first? 
                # Usually APIs return newest first or range. 
                # Let's sort by time to be safe.
                candles.sort(key=lambda x: x['start_time'])
                return candles
            else:
                logger.error(f"Delta API error for {symbol}: {data}")
                return []
        except Exception as e:
            logger.error(f"Error fetching history for {symbol}: {e}")
            return []

    def connect_websocket(self, symbols):
        self.symbols = symbols
        # Start WebSocket in a separate thread
        self.wst = threading.Thread(target=self._run_websocket)
        self.wst.daemon = True
        self.wst.start()

    def _run_websocket(self):
        websocket.enableTrace(False)
        self.ws = websocket.WebSocketApp(
            self.socket_url,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close
        )
        while self.should_continue:
            try:
                self.ws.run_forever(ping_interval=30, ping_timeout=10)
            except Exception as e:
                logger.error(f"Delta WebSocket connection error: {e}")
                time.sleep(5)

    def _on_open(self, ws):
        logger.info("Connected to Delta Exchange WebSocket")
        self.subscribe_symbols(self.symbols)

    def subscribe_symbols(self, symbols_list):
        if not symbols_list: return
        payload = {
            "type": "subscribe",
            "payload": {
                "channels": [
                    {
                        "name": "v2/ticker",
                        "symbols": symbols_list
                    }
                ]
            }
        }
        try:
            self.ws.send(json.dumps(payload))
            logger.info(f"Subscribed to Delta Exchange channels: {symbols_list}")
        except Exception as e:
            logger.error(f"Error subscribing Delta symbols {symbols_list}: {e}")
            
    def unsubscribe_symbols(self, symbols_list):
        if not symbols_list: return
        payload = {
            "type": "unsubscribe",
            "payload": {
                "channels": [
                    {
                        "name": "v2/ticker",
                        "symbols": symbols_list
                    }
                ]
            }
        }
        try:
            self.ws.send(json.dumps(payload))
            logger.info(f"Unsubscribed from Delta Exchange channels: {symbols_list}")
        except Exception as e:
            logger.error(f"Error unsubscribing Delta symbols {symbols_list}: {e}")

    def add_symbols(self, new_symbols):
        to_add = [s for s in new_symbols if s not in self.symbols]
        if not to_add: return
        self.symbols.extend(to_add)
        if hasattr(self, 'ws') and getattr(self.ws, 'sock', None) and self.ws.sock.connected:
            self.subscribe_symbols(to_add)
            
    def remove_symbols(self, old_symbols):
        to_remove = [s for s in old_symbols if s in self.symbols]
        if not to_remove: return
        for s in to_remove:
            self.symbols.remove(s)
        if hasattr(self, 'ws') and getattr(self.ws, 'sock', None) and self.ws.sock.connected:
            self.unsubscribe_symbols(to_remove)
        
    def _send_heartbeat(self, ws):
        payload = {"type": "ping"}
        try:
            ws.send(json.dumps(payload))
        except Exception:
            pass

    def _on_message(self, ws, message):
        try:
            data = json.loads(message)
            # Check for ticker update
            # Ticker updates might be in a wrapper or direct
            # Example: {"type": "v2/ticker", "symbol": "BTCUSD", "mark_price": ...}
            
            if isinstance(data, dict):
                symbol = data.get('symbol')
                price = None
                
                # Try to get LTP (close) or Mark Price
                if 'close' in data:
                    price = data['close']
                elif 'mark_price' in data:
                    price = data['mark_price']
                
                if symbol and price:
                    try:
                        price = float(price)
                        # Use current time for the tick
                        timestamp = datetime.now()
                        self.on_tick_callback(symbol, price, timestamp)
                    except ValueError:
                        pass
                    except ValueError:
                        pass
            
            # Additional check for generic ticker updates (Delta sometimes wraps in a different struct or just sends updates)
            if data.get('type') == 'v2/ticker':
                 # Already handled by the dict check above if 'symbol' is present at top level logic? 
                 # Actually Delta v2/ticker sends: {"type": "v2/ticker", "symbol": "...", ...}
                 # So the previous blocks catch it.
                 pass

        except Exception as e:
            logger.error(f"Error processing Delta message: {e}")

    def _on_error(self, ws, error):
        logger.error(f"Delta WebSocket Error: {error}")

    def _on_close(self, ws, close_status_code, close_msg):
        logger.info("Delta WebSocket Closed")

