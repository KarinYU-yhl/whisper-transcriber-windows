import requests
import truststore
truststore.inject_into_ssl()

url = "https://huggingface.co/api/models/mlx-community/whisper-large-v3"
print(f"Fetching {url}...")

try:
    resp = requests.get(url)
    print(f"Status: {resp.status_code}")
    with open("block_page.html", "w", encoding="utf-8") as f:
        f.write(resp.text)
    print("Saved response to block_page.html")
except Exception as e:
    print(f"Failed: {e}")
