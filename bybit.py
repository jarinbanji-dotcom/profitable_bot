import time

from curl_cffi import requests

# 1. REPLACE THESE WITH YOUR WEBSHARE DETAILS
PROXY_USER = "mgqvrbgh"
PROXY_PASS = "62lgg39b7a42"
PROXY_IP = "45.38.107.97"
PROXY_PORT = "6014"
#6540,6543,6837,6754,6114 , 6641,6014=6461=6462 ,

#6014 : 45.38.107.97 (0.25s)
# 6461 : 194.39.32.164 (0.35s)
# 6462 : 198.105.121.200 (0.45s)
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


for i in range(20):
    
    st=time.time()
    time.sleep(0.1)
    print(fast_fetch())
    en=time.time()
    print(en-st)



