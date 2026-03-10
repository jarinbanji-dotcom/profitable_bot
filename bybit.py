from curl_cffi import requests
import json

# The exact URL from your network log
url = "https://api-manager.upbit.com/api/v1/announcements?os=web&page=1&per_page=20&category=all"

# Transcribed headers from your browser log
headers = {
    "authority": "api-manager.upbit.com",
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


def get_upbit_announcements():
    try:
        # impersonate="chrome" is crucial to bypass Cloudflare
        response = requests.get(url, headers=headers, impersonate="chrome")

        if response.status_code == 200:
            data = response.json()
            print(data)
            # Navigate to the list of announcements

        else:
            print(f"Error Code: {response.status_code}")
            print("Response:", response.text)

    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    get_upbit_announcements()
