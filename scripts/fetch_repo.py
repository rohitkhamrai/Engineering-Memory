import os
import subprocess
from pathlib import Path

REPO_URL = "https://github.com/encode/httpx.git"
TARGET_DIR = Path("data") / "httpx"

def fetch_repo():
    if not TARGET_DIR.parent.exists():
        TARGET_DIR.parent.mkdir(parents=True)
    
    if TARGET_DIR.exists():
        print(f"Repository directory {TARGET_DIR} exists. Pulling latest changes...")
        subprocess.run(["git", "-C", str(TARGET_DIR), "pull"], check=True)
    else:
        print(f"Cloning {REPO_URL} into {TARGET_DIR}...")
        subprocess.run(["git", "clone", REPO_URL, str(TARGET_DIR)], check=True)
        
if __name__ == "__main__":
    fetch_repo()
