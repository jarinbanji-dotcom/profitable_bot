from curl_cffi import requests

# 1. REPLACE THESE WITH YOUR WEBSHARE DETAILS
PROXY_USER = "mgqvrbgh"
PROXY_PASS = "62lgg39b7a42"
PROXY_IP = "31.59.20.176"
PROXY_PORT = "6754"

# 2. Create the proxy dictionary
proxy_url = f"http://{PROXY_USER}:{PROXY_PASS}@{PROXY_IP}:{PROXY_PORT}"
print(proxy_url)

proxies = {
    "http": proxy_url,
    "https": proxy_url
}

# 3. The API URL you found in the Network tab
url = "https://api-manager.upbit.com/api/v1/announcements?os=web&page=1&per_page=1&category=all"

# 4. Use the headers you provided earlier
headers = {
    "authority": "api-manager.upbit.com",
    "accept": "application/json",
    "origin": "https://upbit.com",
    "referer": "https://upbit.com",
    "sec-ch-ua-platform": '"Windows"',
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
}


def fetch_data():
    try:
        # We use impersonate="chrome" + our proxies
        response = requests.get(
            url,
            headers=headers,
            proxies=proxies,
            impersonate="chrome",
        )

        if response.status_code == 200:
            print("Success! Data received:")
            print(response.json())
        else:
            print(f"Failed with status: {response.status_code}")
            # If still 403, Cloudflare is blocking the Webshare Data Center IP
            if response.status_code == 403:
                print("Cloudflare is still blocking this specific proxy IP.")

    except Exception as e:
        print(f"Connection Error: {e}")


if __name__ == "__main__":
    fetch_data()
