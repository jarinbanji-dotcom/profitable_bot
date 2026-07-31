import websocket
import json
import requests
import threading
import time
from datetime import datetime, timezone

# 1. Fetch all current KRW pairs at startup
def get_all_krw_pairs():
    url = "https://api.upbit.com/v1/market/all?isDetails=false"
    res = requests.get(url, headers={"Accept": "application/json"})
    return [m['market'] for m in res.json() if m['market'].startswith('KRW-')]

known_pairs = set(get_all_krw_pairs())
print(f"[{datetime.now(timezone.utc)}] Watching {len(known_pairs)} pairs...")

ws_instance = None

# 2. When new listing found
def on_new_listing(ticker):
    print(f"[{datetime.now(timezone.utc)}] 🚀 NEW LISTING DETECTED: {ticker}")
    # connect_bybit(ticker)  ← uncomment when ready to go live

# 3. Periodically re-fetch market list and detect new pair
def watch_new_listings():
    while True:
        time.sleep(0.5)  # check every 500ms
        try:
            current = set(get_all_krw_pairs())
            new = current - known_pairs
            if new:
                for pair in new:
                    ticker = pair.replace('KRW-', '')
                    known_pairs.add(pair)
                    on_new_listing(ticker)

                    # Re-subscribe WebSocket with new pair included
                    if ws_instance:
                        try:
                            subscribe = [
                                {"ticket": "upbit-sniper"},
                                {"type": "ticker", "codes": list(known_pairs)}
                            ]
                            ws_instance.send(json.dumps(subscribe))
                        except Exception:
                            pass
        except Exception as e:
            print(f"[{datetime.now(timezone.utc)}] watch error: {e}")

# 4. WebSocket handlers
def on_message(ws, message):
    try:
        data = json.loads(message)
        code = data.get('code', '')  # e.g. KRW-CFX

        if code and code not in known_pairs:
            ticker = code.replace('KRW-', '')
            known_pairs.add(code)
            print(f"[{datetime.now(timezone.utc)}] 🚀 WS NEW LISTING DETECTED: {ticker}")
            on_new_listing(ticker)
    except Exception as e:
        print(f"on_message error: {e}")

def on_error(ws, error):
    print(f"[{datetime.now(timezone.utc)}] WS Error: {error}")

def on_close(ws, close_status_code, close_msg):
    print(f"[{datetime.now(timezone.utc)}] WS closed — reconnecting in 1s...")
    time.sleep(1)
    start_ws()

def on_open(ws):
    global ws_instance
    ws_instance = ws
    print(f"[{datetime.now(timezone.utc)}] WS connected — subscribed to {len(known_pairs)} pairs")
    subscribe = [
        {"ticket": "upbit-sniper"},
        {"type": "ticker", "codes": list(known_pairs)}
    ]
    ws.send(json.dumps(subscribe))

def start_ws():
    ws = websocket.WebSocketApp(
        "wss://api.upbit.com/websocket/v1",
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    ws.run_forever(ping_interval=30, ping_timeout=10)  # keeps connection alive

# Start both
threading.Thread(target=watch_new_listings, daemon=True).start()
threading.Thread(target=start_ws, daemon=True).start()

# Keep main alive
while True:
    time.sleep(1)