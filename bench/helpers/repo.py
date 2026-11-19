#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys

# Mapping of CLI keys to their respective repository details
REPO_CONFIGS = {
    "bench": {
        "url": "https://github.com/azizios011/bench-Compatible_windows.git",
        "branch": "bench-6.1.0",
        "dir_name": "bench-Compatible_windows"
    },
    "frappe": {
        "url": "https://github.com/azizios011/frappe-Compatible_windows.git",
        "branch": "axeane_kompta",
        "dir_name": "frappe-Compatible_windows"
    },
    "erpnext": {
        "url": "https://github.com/azizios011/erpnext-Compatible_windows.git",
        "branch": "axeane_kompta",
        "dir_name": "erpnext-Compatible_windows"
    },
    "print_designer": {
        "url": "https://github.com/azizios011/Print-Designer_Compatible_windows.git",
        "branch": "axeane_kompta",
        "dir_name": "Print-Designer_Compatible_windows"
    },
    "hrms": {
        "url": "https://github.com/azizios011/hrms_Compatible_windows.git",
        "branch": "axeane_kompta",
        "dir_name": "hrms_Compatible_windows"
    },
    "webshop": {
        "url": "https://github.com/azizios011/webshop-Compatible_windows.git",
        "branch": "axeane_kompta",
        "dir_name": "webshop-Compatible_windows"
    },
    "payments": {
        "url": "https://github.com/azizios011/payments-Compatible_windows.git",
        "branch": "axeane_kompta",
        "dir_name": "payments-Compatible_windows"
    },
    "builder": {
        "url": "https://github.com/azizios011/builder-Compatible_windows.git",
        "branch": "axeane_kompta",
        "dir_name": "builder-Compatible_windows"
    },
    "crm": {
        "url": "https://github.com/azizios011/crm-Compatible_windows.git",
        "branch": "axeane_kompta",
        "dir_name": "crm-Compatible_windows"
    },
    "drive": {
        "url": "https://github.com/azizios011/drive-Compatible_windows.git",
        "branch": "axeane_kompta",
        "dir_name": "drive-Compatible_windows"
    },
    "books": {
        "url": "https://github.com/azizios011/books-Compatible_windows.git",
        "branch": "axeane_kompta",
        "dir_name": "books-Compatible_windows"
    },
    "pilot": {
        "url": "https://github.com/azizios011/pilot-Compatible_windows.git",
        "branch": "axeane_kompta",
        "dir_name": "pilot-Compatible_windows"
    }
}

def run_command(command, cwd=None):
    """Helper to run shell commands and stream output."""
    print(f"Executing: {' '.join(command)}")
    try:
        subprocess.run(command, cwd=cwd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error executing command: {e}", file=sys.stderr)
        sys.exit(1)

def setup_repo(repo_key):
    config = REPO_CONFIGS[repo_key]
    url = config["url"]
    branch = config["branch"]
    target_dir = config["dir_name"]

    print(f"\n🚀 Setting up {repo_key.upper()}...")

    # 1. Clone the repo with --depth=1 if it doesn't already exist in the current root
    if not os.path.exists(target_dir):
        print(f"Cloning {url} with depth=1...")
        run_command(["git", "clone", "--depth=1", url])
    else:
        print(f"Directory '{target_dir}' already exists. Skipping clone.")

    # 2. Update git config (Navigates into the cloned directory)
    print("Updating git fetch refspecs...")
    run_command(
        ["git", "config", "remote.origin.fetch", "+refs/heads/*:refs/remotes/origin/*"],
        cwd=target_dir
    )

    # 3. Fetch from origin (Navigates into the cloned directory)
    print("Fetching from origin...")
    run_command(["git", "fetch", "origin"], cwd=target_dir)

    # 4. Checkout the target branch (Navigates into the cloned directory)
    print(f"Checking out branch: {branch}...")
    run_command(["git", "checkout", branch], cwd=target_dir)

    print(f"✨ Successfully set up {repo_key} on branch '{branch}'!\n")

def main():
    # Allow "all" as a choice alongside the standard repo keys
    choices = list(REPO_CONFIGS.keys()) + ["all"]
    
    parser = argparse.ArgumentParser(
        description="Helper script to clone and configure specific ERPNext/Frappe Windows compatible repositories."
    )
    parser.add_argument(
        "repo",
        choices=choices,
        help="The repository setup to trigger, or 'all' to set up all repositories."
    )
    
    args = parser.parse_args()
    
    if args.repo == "all":
        repo_list = ", ".join(REPO_CONFIGS.keys())
        print(f"🌟 Setting up all repositories ({repo_list})...")
        for key in REPO_CONFIGS.keys():
            setup_repo(key)
        print("🎉 Finished setting up all repositories successfully!")
    else:
        setup_repo(args.repo)

if __name__ == "__main__":
    main()
