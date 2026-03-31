<div align="center">
  <h1>📈 Trade Pulse</h1>
  <p><strong>A Professional, Multi-Market Algorithmic Trading & Alert Architecture</strong></p>

  <p>
    <img src="https://img.shields.io/badge/Python-3.10+-blue.svg" alt="Python" />
    <img src="https://img.shields.io/badge/Markets-NSE%20%7C%20MCX%20%7C%20Crypto-success.svg" alt="Markets" />
    <img src="https://img.shields.io/badge/License-MIT-gray.svg" alt="License" />
  </p>
</div>

---

**Trade Pulse** (formerly Supertrend Alert System) is a high-performance, real-time algorithmic trading foundation that bridges the gap between Indian traditional markets and global cryptocurrency exchanges. Driven by a customizable confluence engine, it connects live WebSocket market feeds directly to a personal command center dashboard and your email alerts.

## ✨ Core Features

* **🌍 Dual-Market Connectivity**
  * **Indian Markets:** Low-latency WebSocket feeds for NSE & MCX powered by the *Angel One SmartAPI*.
  * **Crypto Markets:** Direct integration with *Delta Exchange* for live digital asset monitoring.
* **🧠 Advanced Confluence Engine**
  * Dozens of indicators (Supertrend, VWAP, ATR, Bollinger Bands, EMA, EMA Cross).
  * Build complex event triggers that wait for multi-indicator confirmation before firing alerts to filter out false signals.
* **🖥️ Web Command Center Dashboard**
  * Built-in Flask localized server providing a sleek, responsive UI (`http://localhost:5000`).
  * Live dynamic charting, realtime prices, subscription tiering (via Razorpay integration), and immediate state control.
* **📬 Real-time Notifications**
  * Get formatted HTML email alerts within milliseconds of a confirmed algorithmic setup.
* **🧪 Deep Backtesting & Optimization**
  * Optimize settings against historical tick data using the built-in `backtester` module to find the highest-probability setups.

## 🛠️ Tech Stack
* **Language:** Python
* **Data Processing:** Pandas, NumPy
* **Communication:** WebSockets, Flask CORS, SMTP, REST APIs
* **Brokers:** Angel One, Delta Exchange
* **Payments:** Razorpay API (for subscription models)

---

## 🚀 Getting Started

### 1. Prerequisites
Ensure you have the following installed and configured:
*   Python 3.10 or newer
*   Angel One SmartAPI Account *(API Key, Client ID, Password, TOTP Key)*
*   Delta Exchange API Keys *(Optional: Only if tracking crypto)*
*   Email Account with App Password enabled for SMTP alerts

### 2. Installation
Clone the repository and install the required dependencies:

```bash
git clone https://github.com/Shivam-dev30/Trade-Pulse.git
cd Trade-Pulse
pip install -r requirements.txt
pip install flask flask-cors flask-login flask-sqlalchemy razorpay  # Additional UI requirements
```

### 3. Environment Configuration
Create an environment file to store your sensitive keys safely.

```bash
# Windows
copy .env.example .env

# Linux/Mac
cp .env.example .env
```

Open `.env` in your editor and provide your keys:
```ini
# Angel One (Indian Markets)
API_KEY=your_angel_api_key
CLIENT_ID=your_client_id
PASSWORD=your_password
TOTP_KEY=your_totp_secret

# Delta Exchange (Crypto Markets)
DELTA_API_KEY=your_delta_api_key
DELTA_API_SECRET=your_delta_secret

# Email Alerts Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=your_sending_email@gmail.com
SENDER_PASSWORD=your_app_password
RECEIVER_EMAIL=your_receiving_email@gmail.com
```

### 4. Running the Platform

To initialize the algorithmic listener and the UI Dashboard simultaneously:

```bash
python main.py
```
* **Trading Engine:** Background threads will spin up, map broker tokens, catch up on the last 5 days of history (for immediate indicator accuracy), and connect to websocket feeds.
* **Dashboard:** Open your browser and navigate to `http://localhost:5000` to interact with your live Trade Pulse panel.

---

## 📁 Repository Structure

```text
Trade-Pulse/
 ├── main.py                # Core Entrypoint (Initializes broker threads & UI)
 ├── config_server.py       # Flask Backend & Razorpay Integration
 ├── frontend/              # HTML/CSS/JS for the Command Center UI
 ├── backtester/            # Historical optimization engine and historical scripts
 ├── broker/                # Angel One & Delta Exchange API Wrappers
 ├── data/                  # Token mapping and candle building (Tick -> OHLCV)
 ├── indicators/            # Evaluator logic (Signal Confluence)
 ├── alerts/                # Email dispatchers and HTML formatting
 ├── logger/                # Extensible rotating file/console loggers
 └── OpenAPIScripMaster.json# Cached Indian Market Symbology
```

## 🔒 Security
* **Never commit your `.env` file.**
* **Never expose your Broker API keys or TOTP Secrets.** 
* A `.gitignore` has been provided to protect configuration environments and local databases by default.

## 📄 License
This platform is open-sourced software licensed under the [MIT license](LICENSE).
