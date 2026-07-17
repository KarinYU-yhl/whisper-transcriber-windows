import os
import shutil
from pathlib import Path
import truststore
import huggingface_hub

# Inject truststore to handle corporate SSL
truststore.inject_into_ssl()

def clear_cache(repo_id):
    cache_dir = Path(os.path.expanduser("~/.cache/huggingface/hub"))
    repo_dir = cache_dir / f"models--{repo_id.replace('/', '--')}"
    if repo_dir.exists():
        print(f"Removing corrupted cache at: {repo_dir}")
        shutil.rmtree(repo_dir)
    else:
        print(f"No cache found at: {repo_dir}")

def download_model(repo_id):
    print(f"Downloading {repo_id}...")
    try:
        # snapshot_download will download all files in the repo
        path = huggingface_hub.snapshot_download(repo_id=repo_id)
        print(f"Successfully downloaded to: {path}")
    except Exception as e:
        print(f"Download failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    model_id = "mlx-community/whisper-large-v3"
    
    # 1. Clear potential corrupted cache
    clear_cache(model_id)
    
    # 2. Try to download
    # download_model(model_id)

    # Debug API call
    import requests
    url = f"https://huggingface.co/api/models/{model_id}"
    print(f"Debugging GET {url}...")
    try:
        resp = requests.get(url)
        print(f"Status: {resp.status_code}")
        print(f"Content-Type: {resp.headers.get('Content-Type')}")
        print(f"Content preview: {resp.text[:500]}")
        resp.json() # Try to parse JSON
        print("JSON parse successful")
    except Exception as e:
        print(f"JSON parse failed: {e}")
