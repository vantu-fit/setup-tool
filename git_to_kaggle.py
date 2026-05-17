import os
import argparse
import json
import shutil
import subprocess

def clone_repo(repo_url, local_dir):
    print(f"\n[+] Cloning repository from GitHub...")
    # If the directory already exists, remove it to clone fresh
    if os.path.exists(local_dir):
        shutil.rmtree(local_dir, ignore_errors=True)
        
    try:
        # Run git clone command
        process = subprocess.Popen(
            ["git", "clone", repo_url, local_dir],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
        
        for line in process.stdout:
            print(line, end="")
            
        process.wait()
        
        if process.returncode == 0:
            print(f"\n[V] Cloned successfully to directory: {local_dir}")
            
            # Remove hidden .git directory to prevent Kaggle from uploading unnecessary commit history (optional)
            git_folder = os.path.join(local_dir, ".git")
            if os.path.exists(git_folder):
                shutil.rmtree(git_folder, ignore_errors=True)
                print("[+] Removed hidden .git folder to optimize Dataset size.")
        else:
            print("\n[X] Error: Clone repository failed.")
            exit(1)
            
    except FileNotFoundError:
        print("\n[X] Error: 'git' command not found. Please install Git.")
        exit(1)

def upload_to_kaggle(local_dir, kaggle_dataset_id, title):
    print(f"\n[+] Preparing to upload repo to Kaggle Dataset: '{kaggle_dataset_id}'...")
    
    metadata_path = os.path.join(local_dir, "dataset-metadata.json")
    
    metadata = {
        "title": title,
        "id": kaggle_dataset_id,
        "licenses": [{"name": "unknown"}]
    }
    
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4)
        
    print("[+] Created dataset-metadata.json.")
    print(f"[+] Starting zipping and uploading to Kaggle...")
    
    try:
        # Create new dataset
        process = subprocess.Popen(
            ["kaggle", "datasets", "create", "-p", local_dir, "-r", "tar"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
        
        for line in process.stdout:
            print(line, end="")
            
        process.wait()
        
        if process.returncode != 0:
            print("\n[-] Dataset creation failed (Maybe the dataset already exists). Proceeding to update new version...")
            # Update dataset
            update_process = subprocess.Popen(
                ["kaggle", "datasets", "version", "-p", local_dir, "-m", "Updated repo via script", "-r", "tar"],
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
    parser = argparse.ArgumentParser(description="Clone GitHub repository and upload to Kaggle Dataset")
    parser.add_argument("--repo-url", required=True, help="URL of the GitHub repository (including token if it is a private repo)")
    parser.add_argument("--kaggle-id", required=True, help="Kaggle dataset ID (e.g., 'username/dataset-name')")
    parser.add_argument("--title", help="Title for the Kaggle dataset")
    parser.add_argument("--dir", default="./temp_repo", help="Temporary directory to store downloaded repo code")
    
    args = parser.parse_args()
        
    if not args.title:
        args.title = args.kaggle_id.split('/')[-1]
        
    try:
        print("=== STARTING PROCESS TO DOWNLOAD SOURCE CODE FROM GITHUB AND PUSH TO KAGGLE ===")
        clone_repo(args.repo_url, args.dir)
        upload_to_kaggle(args.dir, args.kaggle_id, args.title)
    except Exception as e:
        print(f"\n[X] An error occurred: {e}")
    finally:
        print("\n=== CLEANING UP TEMPORARY DATA ===")
        shutil.rmtree(args.dir, ignore_errors=True)
        print("Cleanup complete. Script finished.")
