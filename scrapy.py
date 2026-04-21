import time
import bybit
from datetime import datetime, timezone

from curl_cffi import requests

# 1. REPLACE THESE WITH YOUR WEBSHARE DETAILS
PROXY_USER = "pjmqkwnt"
PROXY_PASS = "1wct0d2sg0r5"
PROXY_IP = "198.105.121.23"
PROXY_PORT = "6285"
#6540,6543,6837,6754,6114 , 6641,6014=6461=6462 , 6641

#6642 :0.4s

#6014 : 45.38.107.97 (0.2s)
# 6461 : 194.39.32.164 (0.2s)
# 6462 : 198.105.121.200 (0.3s)
#
# 2. Create the proxy dictionary
proxy_url = f"http://{PROXY_USER}:{PROXY_PASS}@{PROXY_IP}:{PROXY_PORT}"
print(proxy_url)

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
    


last_seen=["KAT","ETHFI","EDGE","ICP","SENT","CFG","ESP","SKR","AZTEC","TAO","BIRB"]

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
i=0
while(True):
    time.sleep(0.1)
    st=time.time()
    
    res=fast_fetch()
    en=time.time()
    
    title=res["data"]["notices"][0]["title"]

    print(title)
    print(en-st)
    
    if("Market Support for" in title and "Termination" not in title and "KRW" in title):
        
        
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
    elif(i==0):
        st=time.time()
        bybit.run_session_continously("ETHUSDT")
        en=time.time()
        i=1
    elif(i==1):
        i=2
    elif(i==2):
        i=0
        
    
        
                
            
            



    


    en=time.time()














