from huggingface_hub import try_to_load_from_cache
import os

repo_id = "mlx-community/whisper-large-v3"
# Common files for MLX/HF models. 
# Note: MLX models often use weights.npz, but newer ones or generic HF ones use model.safetensors.
# We will check for config.json and model.safetensors as requested.
files_to_check = ["config.json", "model.safetensors"]

print(f"Checking local Hugging Face cache for: {repo_id}")

found_files = []
missing_files = []

for filename in files_to_check:
    # try_to_load_from_cache returns the path if found, None otherwise
    filepath = try_to_load_from_cache(repo_id=repo_id, filename=filename)
    
    if filepath and os.path.exists(filepath):
        print(f"✅ Found {filename} at: {filepath}")
        found_files.append(filename)
    else:
        print(f"❌ Could not find {filename} in cache.")
        missing_files.append(filename)

print("-" * 40)
if len(missing_files) == 0:
    print("Success: The model appears to be fully available offline (based on checked files).")
else:
    print("Warning: Some files are missing from the cache.")
    print(f"Missing: {', '.join(missing_files)}")
    print("You may need to run the download script or use the model online first.")
