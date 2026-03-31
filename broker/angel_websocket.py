from SmartApi.smartWebSocketV2 import SmartWebSocketV2
from logger.logger import logger
import json

class AngelWebSocket:
    def __init__(self, auth_token, api_key, client_code, feed_token, correlation_id="stream_1"):
        self.sws = SmartWebSocketV2(
            auth_token=auth_token,
            api_key=api_key,
            client_code=client_code,
            feed_token=feed_token
        )
        self.correlation_id = correlation_id
        self.callbacks = [] # List of functions to call on filtered tick data

    def add_callback(self, callback):
        self.callbacks.append(callback)

    def _on_data(self, wsapp, message):
        # Message is usually a list of dicts or a dict
        # logger.debug(f"Tick: {message}")
        if self.callbacks:
            for cb in self.callbacks:
                try:
                    cb(message)
                except Exception as e:
                    logger.error(f"Error in callback: {e}")

    def _on_open(self, wsapp):
        logger.info("WebSocket Connection Opened")

    def _on_close(self, wsapp):
        logger.info("WebSocket Connection Closed")

    def _on_error(self, wsapp, error):
        logger.error(f"WebSocket Error: {error}")

    def connect(self, subscribe_tokens=None, mode=1):
        """
        Connects to the WebSocket.
        subscribe_tokens: Optional list of tokens to subscribe to on open.
        mode: Subscription mode (default 1 for LTP).
        """
        # Define internal wrappers that call external callbacks if needed or handle logic
        
        def internal_on_open(wsapp):
            logger.info("WebSocket Connection Opened (Internal)")
            if subscribe_tokens:
                self.subscribe(mode, subscribe_tokens)
                
        def internal_on_data(wsapp, message):
            self._on_data(wsapp, message)

        self.sws.on_data = internal_on_data
        self.sws.on_open = internal_on_open
        self.sws.on_close = self._on_close
        self.sws.on_error = self._on_error
        
        try:
            self.sws.connect()
        except Exception as e:
            logger.error(f"Connection failed: {e}")

    def subscribe(self, mode, token_list):
        """
        mode: 1 (LTP), 2 (Quote), 3 (SnapQuote)
        token_list: list of {"exchangeType": int, "tokens": ["token1", ...]}
        """
        try:
            # Example format required by V2:
            # exchangeType: 1 (NSE), 2 (NFO)...
            # tokens: list of strings
            
            # The library expects specific correlationID and action
            # The wrapper method `subscribe` in SmartWebSocketV2 handles simple subscription?
            # Checking docs metaphorically: V2 uses `subscribe(self, correlation_id, mode, token_list)`
            self.sws.subscribe(self.correlation_id, mode, token_list)
            logger.info(f"Subscribed to {token_list} with mode {mode}")
        except Exception as e:
            logger.error(f"Subscription failed: {e}")
