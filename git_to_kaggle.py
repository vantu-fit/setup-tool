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

def clone_repo(repo_name, local_dir):
    print(f"\n[+] Cloning repository '{repo_name}' from GitHub...")
    
    github_token = get_env_var("GITHUB_TOKEN")
    github_user = get_env_var("GITHUB_USER")
    
    # Construct clone URL with authentication
    repo_url = f"https://{github_user}:{github_token}@github.com/{github_user}/{repo_name}.git"
    
    if os.path.exists(local_dir):
        shutil.rmtree(local_dir, ignore_errors=True)
        
    try:
        process = subprocess.Popen(
            ["git", "clone", repo_url, local_dir],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
        
        for line in process.stdout:
            # Mask the token in output to prevent leaking
            safe_line = line.replace(github_token, "***")
            print(safe_line, end="")
            
        process.wait()
        
        if process.returncode == 0:
            print(f"\n[V] Cloned successfully to directory: {local_dir}")
            
            # Remove hidden .git directory to prevent Kaggle from uploading unnecessary commit history
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

def upload_to_kaggle(local_dir, repo_name):
    kaggle_user = get_env_var("KAGGLE_USERNAME")
    
    # Kaggle dataset slugs must be lowercase, alphanumeric, and hyphens only (6-50 characters)
    slug = repo_name.lower().replace("_", "-")
    slug = re.sub(r'[^a-z0-9\-]', '', slug)
    
    # Pad with 'dataset' if slug is too short
    if len(slug) < 6:
        slug = f"{slug}-dataset"
        
    kaggle_dataset_id = f"{kaggle_user}/{slug}"
    
    print(f"\n[+] Preparing to sync repo to Kaggle Dataset: '{kaggle_dataset_id}'...")
    
    metadata_path = os.path.join(local_dir, "dataset-metadata.json")
    
    metadata = {
        "title": repo_name,
        "id": kaggle_dataset_id,
        "licenses": [{"name": "unknown"}]
    }
    
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4)
        
    print("[+] Created dataset-metadata.json.")
    print(f"[+] Starting syncing to Kaggle...")
    
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
            # Update dataset
            update_process = subprocess.Popen(
                ["kaggle", "datasets", "version", "-p", local_dir, "-m", "Sync repository via script", "-r", "tar"],
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
    parser = argparse.ArgumentParser(description="Sync GitHub repository to Kaggle Dataset automatically")
    parser.add_argument("repo_name", help="Name of the repository to clone and sync (e.g., 'SiLoRA')")
    parser.add_argument("--dir", default="./temp_repo", help="Temporary directory to store downloaded repo code")
    
    args = parser.parse_args()
        
    try:
        print(f"=== STARTING SYNC FOR '{args.repo_name}' ===")
        clone_repo(args.repo_name, args.dir)
        upload_to_kaggle(args.dir, args.repo_name)
    except Exception as e:
        print(f"\n[X] An error occurred: {e}")
    finally:
        print("\n=== CLEANING UP TEMPORARY DATA ===")
        shutil.rmtree(args.dir, ignore_errors=True)
        print("Cleanup complete. Script finished.")
