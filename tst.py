import requests

hostname = "pr-eu.proxies.fo"
port = "1337"
username = "dkzhep7vca"
password = "kxl6nggrde"

proxies = {
    'http': f'socks5h://{username}:{password}@{hostname}:{port}',
    'https': f'socks5h://{username}:{password}@{hostname}:{port}'
}

url = "https://api.ipify.org"  # Bisa ganti ke https://app.proxies.fo/ip juga

try:
    response = requests.get(url, proxies=proxies, timeout=10)
    print(f"Response Status Code: {response.status_code}")
    print(f"Your Proxy IP: {response.text}")
except requests.exceptions.RequestException as e:
    print(f"An error occurred: {e}")
