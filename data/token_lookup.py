import requests
import json
import os
from logger.logger import logger

SCRIP_MASTER_URL = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
CACHE_FILE = "OpenAPIScripMaster.json"

def get_token_info(symbol_list):
    """
    Returns a dictionary {symbol: {"token": token, "exchange": exchange}} 
    for the given list of symbols. Support NSE and MCX.
    """
    data = []
    
    # Check cache
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                data = json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load cached scrip master: {e}")
    
    if not data:
        logger.info("Downloading Scrip Master...")
        try:
            r = requests.get(SCRIP_MASTER_URL)
            data = r.json()
            with open(CACHE_FILE, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            logger.error(f"Failed to download Scrip Master: {e}")
            return {}

    mapping = {}
    target_symbols = set(s.upper() for s in symbol_list)
    
    # We'll group MCX candidates to find the near-month expiry
    mcx_candidates = {} # {base_name: [item1, item2, ...]}

    for item in data:
        name = item.get('name', '').upper()
        symbol_full = item.get('symbol', '').upper()
        exch = item.get('exch_seg')

        # Logic for NSE
        if exch == "NSE" and name in target_symbols:
            if symbol_full.endswith('-EQ'): 
                mapping[name] = {"token": item['token'], "exchange": "NSE"}
        
        # Logic for MCX
        if exch == "MCX":
            # Prioritize Futures (usually end with 'FUT')
            is_target = (name in target_symbols or symbol_full in target_symbols)
            is_future = symbol_full.endswith('FUT')
            
            if is_target and is_future:
                if name not in mcx_candidates:
                    mcx_candidates[name] = []
                mcx_candidates[name].append(item)

    # Process MCX candidates to find the nearest expiry
    from datetime import datetime
    today = datetime.now().date()

    for name, items in mcx_candidates.items():
        # Sort items by expiry date
        valid_items = []
        for it in items:
            expiry_str = it.get('expiry')
            if not expiry_str:
                continue
            try:
                # Format is usually 'DDMMMYYYY' (e.g., 31JAN2026)
                expiry_dt = datetime.strptime(expiry_str, '%d%b%Y').date()
                if expiry_dt >= today:
                    valid_items.append((expiry_dt, it))
            except Exception:
                continue
        
        if valid_items:
            # Sort by date (nearest first)
            valid_items.sort(key=lambda x: x[0])
            nearest_item = valid_items[0][1]
            mapping[name] = {
                "token": nearest_item['token'], 
                "exchange": "MCX",
                "full_symbol": nearest_item['symbol'],
                "expiry": nearest_item['expiry']
            }
            logger.info(f"Selected MCX contract for {name}: {nearest_item['symbol']} (Expiry: {nearest_item['expiry']})")

    return mapping
