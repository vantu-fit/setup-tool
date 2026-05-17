import os
import argparse
import json
import shutil
import subprocess
import re

def get_env_var(name):
    val = os.environ.get(name)
    if not val:
        print(f"\n[X] Error: Environment variable '{name}' is not set. Please run 'source setup.sh' first.")
        exit(1)
    return val

def download_lib(lib_name, local_dir):
    print(f"\n[+] Downloading python package '{lib_name}' and its dependencies...")
    os.makedirs(local_dir, exist_ok=True)
    
    try:
        # Run pip download
        # pip download sẽ tải file cài đặt (.whl hoặc .tar.gz) của thư viện này
        # và TẤT CẢ các thư viện phụ thuộc (dependencies) của nó.
        process = subprocess.Popen(
            ["pip", "download", lib_name, "-d", local_dir],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
        for line in process.stdout:
            # Lọc bớt log nếu muốn (hiện tại in ra để tiện theo dõi)
            print(line, end="")
        process.wait()
        
        if process.returncode == 0:
            print(f"\n[V] Downloaded '{lib_name}' successfully to: {local_dir}")
        else:
            print(f"\n[X] Error: Failed to download '{lib_name}'.")
            exit(1)
            
    except FileNotFoundError:
        print("\n[X] Error: 'pip' command not found.")
        exit(1)

def upload_to_kaggle(local_dir, lib_name):
    kaggle_user = get_env_var("KAGGLE_USERNAME")
    
    slug = f"lib-{lib_name}".lower().replace("_", "-")
    slug = re.sub(r'[^a-z0-9\-]', '', slug)
    
    if len(slug) < 6:
        slug = f"{slug}-pkg"
        
    kaggle_dataset_id = f"{kaggle_user}/{slug}"
    
    print(f"\n[+] Preparing to sync to Kaggle Dataset: '{kaggle_dataset_id}'...")
    
    metadata_path = os.path.join(local_dir, "dataset-metadata.json")
    metadata = {
        "title": f"Python Lib: {lib_name}",
        "id": kaggle_dataset_id,
        "licenses": [{"name": "unknown"}]
    }
    
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4)
        
    try:
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
            print("\n[-] Proceeding to sync/update new version...")
            update_process = subprocess.Popen(
                ["kaggle", "datasets", "version", "-p", local_dir, "-m", "Sync library via script", "-r", "tar"],
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
        print("\n[X] Error: Kaggle CLI not found.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download Python library for offline use and upload to Kaggle")
    parser.add_argument("lib_name", help="Name of the library to download (e.g., 'evaluate')")
    parser.add_argument("--dir", default="./temp_lib_download", help="Temporary directory")
    
    args = parser.parse_args()
        
    try:
        download_lib(args.lib_name, args.dir)
        upload_to_kaggle(args.dir, args.lib_name)
    finally:
        print("\n=== CLEANING UP TEMPORARY DATA ===")
        shutil.rmtree(args.dir, ignore_errors=True)
        print("Script finished.")
