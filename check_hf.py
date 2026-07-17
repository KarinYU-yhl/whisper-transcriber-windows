import requests
import truststore
truststore.inject_into_ssl()

url = "https://huggingface.co/mlx-community/whisper-large-v3-turbo/resolve/main/config.json"
print(f"Attempting to GET {url}...")

try:
    resp = requests.get(url)
    print(f"Status Code: {resp.status_code}")
    print(f"Headers: {resp.headers}")
except Exception as e:
    print(f"Request failed: {e}")
