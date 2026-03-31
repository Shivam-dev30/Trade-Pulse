# Supertrend Alert System (NSE)

A production-grade Python-based real-time alert system for NSE stocks using the Angel One SmartAPI and Telegram notifications.

## Features
- **Real-time Monitoring**: Uses Angel One WebSocket for live tick data.
- **15-Minute Candles**: Aggregates ticks into 15m OHLC candles.
- **Supertrend Indicator**: Implements Supertrend (31, 2) logic.
- **Instant Alerts**: Sends Telegram notifications on trend reversal (Bullish <-> Bearish) at candle close.
- **Robustness**: Handles reconnects (via library), logging, and token lookup.

## Prerequisites
- Python 3.10+
- Angel One SmartAPI Account (API Key, Client ID, Password, TOTP Key)
- Telegram Bot (Token and Chat ID)

## Installation

1.  **Clone/Download the repository** to your local machine.
2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

1.  **Environment Variables**:
    Copy `.env.example` to `.env` and fill in your credentials.
    ```bash
    cp .env.example .env
    ```
    Edit `.env`:
    ```ini
    ANGEL_API_KEY=your_api_key
    ANGEL_CLIENT_ID=your_client_id
    ANGEL_PASSWORD=your_password
    ANGEL_TOTP_KEY=your_totp_key
    TELEGRAM_BOT_TOKEN=your_bot_token
    TELEGRAM_CHAT_ID=your_chat_id
    ```
    *Note: `ANGEL_TOTP_KEY` is the secret key used to generate TOTP (Time-based One-Time Password).*

2.  **Watchlist**:
    Open `main.py` and modify the `WATCHLIST_SYMBOLS` list with the NSE symbols you want to track (e.g., `["TCS", "INFY"]`).

## Usage

Run the main script:
```bash
python main.py
```

## How It Works

1.  **Authenticator**: Logs in specifically using TOTP generation.
2.  **Token Lookup**: Automatically fetches the latest `OpenAPIScripMaster.json` to map symbols (e.g., "TCS") to Angel One tokens.
3.  **WebSocket**:Connects to `SmartWebSocketV2` and subscribes to LTP (Last Traded Price) updates.
4.  **Candle Builder**: Aggregates live ticks into 15-minute candles (00, 15, 30, 45).
5.  **Supertrend Logic**: 
    - Calculates ATR (31).
    - Determines Basic and Final Bands.
    - Checks for trend flips upon candle completion.
6.  **Alerts**: If a flip is detected, a formatted message is sent to Telegram.

## Directory Structure

```
/config         # Configuration settings
/broker         # WebSocket connection logic
/data           # Candle aggregation and token lookup
/indicators     # Supertrend algorithm
/alerts         # Telegram notification
/logger         # Logging setup
main.py         # Entry point
```

## Logs
Logs are saved to `bot.log` and printed to the console.
