# pip install curl_cffi
from curl_cffi import requests 

url = "https://api-manager.upbit.com/api/v1/announcements?os=web&page=1&per_page=20&category=all"

headers = {
    "accept": "application/json",
    "accept-language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "origin": "https://upbit.com",
    "referer": "https://upbit.com/",
    "sec-ch-ua": '"Not:A-Brand";v="99", "Google Chrome";v="145", "Chromium";v="145"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
}

try:
    # 'impersonate' makes the TLS fingerprint look like a real Chrome browser
    response = requests.get(url, headers=headers, impersonate="chrome120")
    
    if response.status_code == 200:
        data = response.json()
        latest_title = data['data']['list'][0]['title']
        print(f"Success! Latest: {latest_title}")
    else:
        print(f"Blocked! Status Code: {response.status_code}")
        print(f"Response: {response.text[:200]}")

except Exception as e:
    print(f"Error: {e}")
