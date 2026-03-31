import requests
from datetime import datetime, timedelta

def test_delta():
    symbol = "BTCUSDT"
    resolution = "15m" # Standard for many APIs
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=1)
    
    url = "https://api.delta.exchange/v2/history/candles"
    params = {
        "symbol": symbol,
        "resolution": resolution,
        "start": int(start_time.timestamp()),
        "end": int(end_time.timestamp())
    }
    
    print(f"URL: {url}")
    print(f"Params: {params}")
    r = requests.get(url, params=params)
    print(f"Status: {r.status_code}")
    print(f"Response: {r.text[:500]}")

if __name__ == "__main__":
    test_delta()
