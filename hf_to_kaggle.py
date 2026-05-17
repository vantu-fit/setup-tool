import os
import argparse
import json
import shutil
from huggingface_hub import snapshot_download
import subprocess
from tqdm import tqdm

def download_from_hf(repo_id, repo_type, local_dir):
    # Create subdirectories for each repo to avoid file name conflicts
    # Example: gpt2 -> models/gpt2, meta-llama/Llama-2 -> models/meta-llama_Llama-2
    safe_repo_name = repo_id.replace("/", "_")
    sub_dir = os.path.join(local_dir, f"{repo_type}s", safe_repo_name)
    os.makedirs(sub_dir, exist_ok=True)
    
    token = os.environ.get("HF_TOKEN")
    
    # Hugging Face snapshot_download has built-in progress bar (tqdm)
    # for each downloaded file.
    snapshot_download(
        repo_id=repo_id,
        repo_type=repo_type,
        local_dir=sub_dir,
        token=token,
        ignore_patterns=["*.git*"]
    )
    return sub_dir

def upload_to_kaggle(local_dir, kaggle_dataset_id, title):
    print(f"\n[+] Preparing to upload to Kaggle Dataset: '{kaggle_dataset_id}'...")
    
    metadata_path = os.path.join(local_dir, "dataset-metadata.json")
    
    metadata = {
        "title": title,
        "id": kaggle_dataset_id,
        "licenses": [{"name": "unknown"}]
    }
    
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4)
        
    print("[+] Created dataset-metadata.json.")
    
    print(f"[+] Starting zipping and uploading to Kaggle (Please wait, this may take some time depending on the size)...")
    try:
        # Use Popen to see real-time output of Kaggle CLI (Kaggle CLI also has its own upload progress bar)
        process = subprocess.Popen(
            ["kaggle", "datasets", "create", "-p", local_dir, "-r", "tar"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
        
        for line in process.stdout:
            print(line, end="")
            
        process.wait()
        
        if process.returncode != 0:
            print("\n[-] Dataset creation failed (Maybe the dataset already exists). Proceeding to update new version...")
            update_process = subprocess.Popen(
                ["kaggle", "datasets", "version", "-p", local_dir, "-m", "Updated multiple models/datasets via script", "-r", "tar"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
            )
            for line in update_process.stdout:
                print(line, end="")
            update_process.wait()
            
            if update_process.returncode == 0:
                print("\n[V] Upload (update) successful!")
            else:
                print("\n[X] Error: Failed to upload to Kaggle.")
        else:
            print("\n[V] Upload (create) successful!")
            
    except FileNotFoundError:
        print("\n[X] Error: Kaggle CLI not found. Please install it: 'pip install kaggle'")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download multiple Models & Datasets from Hugging Face and upload them together into 1 Kaggle Dataset")
    parser.add_argument("--models", nargs="*", default=[], help="List of Hugging Face model repo IDs (separated by space)")
    parser.add_argument("--datasets", nargs="*", default=[], help="List of Hugging Face dataset repo IDs (separated by space)")
    parser.add_argument("--kaggle-id", required=True, help="Kaggle dataset ID (e.g., 'username/dataset-name')")
    parser.add_argument("--title", help="Title for the Kaggle dataset")
    parser.add_argument("--dir", default="./temp_download", help="Temporary directory to store downloaded data")
    
    args = parser.parse_args()
    
    if not args.models and not args.datasets:
        print("Error: Please specify at least 1 model (--models) or 1 dataset (--datasets).")
        exit(1)
        
    if not args.title:
        args.title = args.kaggle_id.split('/')[-1]
        
    os.makedirs(args.dir, exist_ok=True)
    
    total_items = len(args.models) + len(args.datasets)
    
    try:
        # Download models process
        if args.models:
            print(f"\n=== START DOWNLOADING {len(args.models)} MODEL(S) FROM HUGGING FACE ===")
            for i, model_id in enumerate(args.models):
                print(f"\n[{i+1}/{total_items}] Downloading Model: {model_id}")
                download_from_hf(model_id, "model", args.dir)
                
        # Download datasets process
        if args.datasets:
            print(f"\n=== START DOWNLOADING {len(args.datasets)} DATASET(S) FROM HUGGING FACE ===")
            base_index = len(args.models)
            for i, dataset_id in enumerate(args.datasets):
                print(f"\n[{base_index+i+1}/{total_items}] Downloading Dataset: {dataset_id}")
                download_from_hf(dataset_id, "dataset", args.dir)
                
        print("\n=== DOWNLOAD COMPLETE. STARTING UPLOAD TO KAGGLE ===")
        upload_to_kaggle(args.dir, args.kaggle_id, args.title)
        
    except Exception as e:
        print(f"\n[X] An error occurred: {e}")
    finally:
        print("\n=== CLEANING UP TEMPORARY DATA ===")
        shutil.rmtree(args.dir, ignore_errors=True)
        print("Cleanup complete. Script finished.")
