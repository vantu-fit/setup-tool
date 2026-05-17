import os
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"  # Vô hiệu hóa thanh tải xuống của HF để tránh spam log
import argparse
import json
import shutil
from huggingface_hub import snapshot_download
import subprocess
import re

def get_env_var(name):
    val = os.environ.get(name)
    if not val:
        print(f"\n[X] Error: Environment variable '{name}' is not set. Please run 'source setup.sh' first.")
        exit(1)
    return val

def download_from_hf(repo_id, repo_type, local_dir):
    # Create subdirectories for each repo to avoid file name conflicts
    safe_repo_name = repo_id.replace("/", "_")
    sub_dir = os.path.join(local_dir, f"{repo_type}s", safe_repo_name)
    os.makedirs(sub_dir, exist_ok=True)
    
    token = os.environ.get("HF_TOKEN")
    
    # Hugging Face snapshot_download has built-in progress bar (tqdm)
    snapshot_download(
        repo_id=repo_id,
        repo_type=repo_type,
        local_dir=sub_dir,
        token=token,
        ignore_patterns=["*.git*"]
    )
    return sub_dir

def upload_to_kaggle(local_dir, dataset_name):
    kaggle_user = get_env_var("KAGGLE_USERNAME")
    
    # Kaggle dataset slugs must be lowercase, alphanumeric, and hyphens only (6-50 characters)
    slug = dataset_name.lower().replace("_", "-")
    slug = re.sub(r'[^a-z0-9\-]', '', slug)
    
    # Pad with 'dataset' if slug is too short
    if len(slug) < 6:
        slug = f"{slug}-dataset"
        
    kaggle_dataset_id = f"{kaggle_user}/{slug}"
    
    print(f"\n[+] Preparing to sync to Kaggle Dataset: '{kaggle_dataset_id}'...")
    
    metadata_path = os.path.join(local_dir, "dataset-metadata.json")
    
    metadata = {
        "title": dataset_name,
        "id": kaggle_dataset_id,
        "licenses": [{"name": "unknown"}]
    }
    
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4)
        
    print("[+] Created dataset-metadata.json.")
    print(f"[+] Starting syncing to Kaggle (Please wait, this may take some time depending on the size)...")
    
    try:
        # Try to create new dataset
        process = subprocess.Popen(
            ["kaggle", "datasets", "create", "-p", local_dir, "-r", "tar"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
        
        output_log = ""
        for line in process.stdout:
            print(line, end="")
            output_log += line
            
        process.wait()
        
        if process.returncode != 0 or "error" in output_log.lower() or "already in use" in output_log.lower() or "already exists" in output_log.lower():
            print("\n[-] Dataset creation failed (Maybe the dataset already exists). Proceeding to sync/update new version...")
            update_process = subprocess.Popen(
                ["kaggle", "datasets", "version", "-p", local_dir, "-m", "Sync multiple models/datasets via script", "-r", "tar"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
            )
            for line in update_process.stdout:
                print(line, end="")
            update_process.wait()
            
            if update_process.returncode == 0:
                print("\n[V] Sync (update) successful!")
            else:
                print("\n[X] Error: Failed to sync to Kaggle.")
        else:
            print("\n[V] Sync (create) successful!")
            
    except FileNotFoundError:
        print("\n[X] Error: Kaggle CLI not found. Please install it: 'pip install kaggle'")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download multiple Models & Datasets from Hugging Face and upload them together into 1 Kaggle Dataset")
    parser.add_argument("--models", nargs="*", default=[], help="List of Hugging Face model repo IDs (separated by space)")
    parser.add_argument("--datasets", nargs="*", default=[], help="List of Hugging Face dataset repo IDs (separated by space)")
    parser.add_argument("--name", help="Name for the Kaggle dataset. If not provided, it will use the name of the first downloaded repo.")
    parser.add_argument("--dir", default="./temp_download", help="Temporary directory to store downloaded data")
    parser.add_argument("--no-cleanup", action="store_true", help="If set, do not delete the temporary downloaded files after uploading")
    
    args = parser.parse_args()
    
    if not args.models and not args.datasets:
        print("Error: Please specify at least 1 model (--models) or 1 dataset (--datasets).")
        exit(1)
        
    if not args.name:
        first_repo = (args.models + args.datasets)[0]
        args.name = first_repo.split('/')[-1]
        
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
                
        print("\n=== DOWNLOAD COMPLETE. STARTING SYNC TO KAGGLE ===")
        upload_to_kaggle(args.dir, args.name)
        
    except Exception as e:
        print(f"\n[X] An error occurred: {e}")
    finally:
        if not args.no_cleanup:
            print("\n=== CLEANING UP TEMPORARY DATA ===")
            shutil.rmtree(args.dir, ignore_errors=True)
            print("Cleanup complete. Script finished.")
        else:
            print(f"\n=== SKIPPING CLEANUP. DATA SAVED IN '{args.dir}' ===")
            print("Script finished.")
