import time
import os
import threading
import bybit
from datetime import datetime, timezone

from curl_cffi import requests

# 1. Webshare details come from environment variables — never hardcode them
PROXY_USER = os.environ["PROXY_USER"]
PROXY_PASS = os.environ["PROXY_PASS"]
PROXY_IP = os.environ.get("PROXY_IP", "92.113.236.99")
PROXY_PORT = os.environ.get("PROXY_PORT", "6684")
#6540,6543,6837,6754,6114 , 6641,6014=6461=6462 , 6641
"""
PROXY_IP = "92.113.236.99"
PROXY_PORT = "6684"
"""
#6642 :0.4s , 5814

#6014 : 45.38.107.97 (0.2s)
# 6461 : 194.39.32.164 (0.2s)
# 6462 : 198.105.121.200 (0.3s)
#
# 2. Create the proxy dictionary
proxy_url = f"http://{PROXY_USER}:{PROXY_PASS}@{PROXY_IP}:{PROXY_PORT}"
print(f"proxy: {PROXY_IP}:{PROXY_PORT}")  # don't print the password

proxies = {
    "http": proxy_url,
    "https": proxy_url
}

# 3. The API URL you found in the Network tab
url = "https://api-manager.upbit.com/api/v1/announcements?os=web&page=1&per_page=1&category=all"
from curl_cffi import requests

# Create a session once at the start of your bot
session = requests.Session()
session.proxies = {"http": proxy_url, "https": proxy_url}

def fast_fetch():
    # Subsequent calls using the same session are MUCH faster
    # because the TLS handshake is already done.
    response = session.get(url, impersonate="chrome")
    return response.json()
    


last_seen=["KAT","ZAMA","SOON","CHIP","PIEVERSE","KAT","ETHFI","EDGE","ICP","SENT","CFG","ESP","SKR","AZTEC","TAO","BIRB"]

def connect_bybit(ticker):
    print("ticker is :", ticker)

    symbol = f"{ticker}USDT"
    print("symbol is :", symbol)

    qty = 6

    st = time.time()

    for i in range(7):
        try:
            bybit.place_aggressive_spot_buy(symbol, qty)
            break
        except Exception as e:
            print(f"Attempt {i + 1} failed. Error: {e}")
    en = time.time()
    print("total time taken : ", en - st)


# Keep the Bybit connection warm in the background, NOT inside the poll loop.
# Uses get_server_time (doesn't touch bybit.results, so it can't corrupt a buy in progress).
def keep_bybit_warm():
    while True:
        try:
            bybit.session.get_server_time()
        except Exception as e:
            print(f"[{datetime.now(timezone.utc)}] keep-alive error: {e}")
        time.sleep(10)

threading.Thread(target=keep_bybit_warm, daemon=True).start()

while(True):
    time.sleep(0.05)
    st=time.time()

    try:
        res=fast_fetch()
    except Exception as e:
        # one bad response must not kill the bot
        print(f"[{datetime.now(timezone.utc)}] fetch error: {e}")
        continue
    en=time.time()
    

    
    title=res["data"]["notices"][0]["title"]
    title_up = title.upper()
    is_listing = any(x in title_up for x in [
    "MARKET SUPPORT", 
    "디지털 자산 추가", 
    "신규 거래지원"])

    is_not_noise = all(x not in title_up for x in [
    "TERMINATION", "WARNING", "CAUTION", "LIFTED", "유의", "거래지원 종료"])

    
    if is_listing and is_not_noise and "KRW" in title_up:
        
        start = title.find("(")
        end = title.find(")")
        
        if start != -1 and end != -1:
            ticker = title[start + 1:end].strip()
            
            if(ticker not in last_seen):
                print(en-st)
                print(f"[{datetime.now(timezone.utc)}] new listing")
                print(f"inside upbit api page listing time : {res["data"]["notices"][0]["listed_at"]}")
                print("new listing announcement")
                print(ticker)
                print("heyya")
                last_seen.append(ticker)
                connect_bybit(ticker)
        
    
        
                
            
            



    


    en=time.time()
