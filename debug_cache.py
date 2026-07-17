import truststore
from huggingface_hub import scan_cache_dir, try_to_load_from_cache
import sys

# Inject system trust store
truststore.inject_into_ssl()

print("--- Cache Scan ---")
try:
    hf_cache_info = scan_cache_dir()
    for repo in hf_cache_info.repos:
        print(f"Repo: {repo.repo_id}")
        for revision in repo.revisions:
            print(f"  Revision: {revision.commit_hash[:8]} (Refs: {revision.refs})")
            for file in revision.files:
                print(f"    - {file.file_name}")
except Exception as e:
    print(f"Error scanning cache: {e}")

print("\n--- Check Specific Models ---")
models = [
    "mlx-community/whisper-large-v3",
    "mlx-community/whisper-large-v3-turbo",
    "mlx-community/whisper-tiny",
    "mlx-community/whisper-base",
    "mlx-community/whisper-small",
    "mlx-community/whisper-medium"
]

for model in models:
    cached_config = try_to_load_from_cache(repo_id=model, filename="config.json")
    print(f"{model}: {'[FOUND]' if cached_config else '[MISSING]'} config.json")
