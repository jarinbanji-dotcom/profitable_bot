import time
import bybit

from curl_cffi import requests

# 1. REPLACE THESE WITH YOUR WEBSHARE DETAILS
PROXY_USER = "mgqvrbgh"
PROXY_PASS = "62lgg39b7a42"
PROXY_IP = "198.105.121.200"
PROXY_PORT = "6462"
#6540,6543,6837,6754,6114 , 6641,6014=6461=6462 ,

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
url = "https://api-manager.upbit.com/api/v1/announcements?os=web&page=1&per_page=1&category=trade"
from curl_cffi import requests

# Create a session once at the start of your bot
session = requests.Session()
session.proxies = {"http": proxy_url, "https": proxy_url}

def fast_fetch():
    # Subsequent calls using the same session are MUCH faster
    # because the TLS handshake is already done.
    response = session.get(url, impersonate="chrome")
    return response.json()


last_seen=["EDGE","ICP","SENT","CFG","ESP","SKR","AZTEC","TAO","BIRB"]

def connect_bybit(ticker):
    print("ticker is :", ticker)

    symbol = f"{ticker}USDT"
    print("symbol is :", symbol)

    qty = 7

    st = time.time()

    for i in range(3):
        try:
            bybit.place_aggressive_spot_buy(symbol, qty)
            break
        except Exception as e:
            print(f"Attempt {i + 1} failed. Error: {e}")
    en = time.time()
    print("total time taken : ", en - st)

while(True):
    time.sleep(0.1)
    st=time.time()
    res=fast_fetch()
    title=res["data"]["notices"][0]["title"]
    if("Market Support for" in title and "Termination" not in title):
        
        start = title.find("(")
        end = title.find(")")

        if start != -1 and end != -1:
            ticker = title[start + 1:end].strip()
            
            if(ticker not in last_seen):
                print("new listing announcement")
                print(ticker)
                last_seen.append(ticker)
                
                connect_bybit(ticker)
                
                
            
            #it will connect to bybit
            



    


    en=time.time()


