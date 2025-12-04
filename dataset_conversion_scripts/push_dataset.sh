#!/bin/bash

# Simple dataset push script
# Usage: ./push_dataset.sh [local-dir] [repo-id]
# Example: ./push_dataset.sh ~/.cache/huggingface/lerobot/thomas0829/my_dataset thomas0829/my_dataset_v3.0

set -e  # Exit on error

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Arguments
LOCAL_DIR="${1:-$HOME/.cache/huggingface/lerobot/thomas0829/put_the_cube_into_the_cup}"
REPO_ID="${2:-thomas0829/put_the_cube_into_the_cup_backup}"

echo "================================================"
echo "LeRobot Dataset Push to Hub"
echo "================================================"
echo "Local directory: $LOCAL_DIR"
echo "Target repo: $REPO_ID"
echo ""

# Check if local directory exists
if [ ! -d "$LOCAL_DIR" ]; then
    echo "[!] Error: Local directory not found: $LOCAL_DIR"
    exit 1
fi

# Run push
echo "[*] Pushing dataset to hub..."
python "$SCRIPT_DIR/simple_push_dataset.py" \
    --local-dir "$LOCAL_DIR" \
    --repo-id "$REPO_ID"

echo ""
echo "[+] Done!"
echo "View dataset at: https://huggingface.co/datasets/$REPO_ID"
