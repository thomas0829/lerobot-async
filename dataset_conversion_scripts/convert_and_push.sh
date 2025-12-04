#!/bin/bash

# Dataset conversion and push script
# Usage: ./convert_and_push.sh [repo-id]
# Example: ./convert_and_push.sh thomas0829/put_the_cube_into_the_cup

set -e  # Exit on error

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Default values
REPO_ID="${1:-thomas0829/put_the_cube_into_the_cup}"
CACHE_DIR="$HOME/.cache/huggingface/lerobot"

echo "================================================"
echo "LeRobot Dataset v2.1 to v3.0 Conversion"
echo "================================================"
echo "Repository: $REPO_ID"
echo "Cache directory: $CACHE_DIR"
echo ""

# Check if dataset exists locally
DATASET_PATH="$CACHE_DIR/$REPO_ID"
if [ ! -d "$DATASET_PATH" ]; then
    echo "[!] Dataset not found at: $DATASET_PATH"
    echo "The script will download it from the hub."
fi

# Run conversion
echo "[*] Converting dataset from v2.1 to v3.0..."
python "$SCRIPT_DIR/convert_dataset_v21_to_v30.py" \
    --repo-id "$REPO_ID" \
    --push-to-hub

echo ""
echo "[+] Done!"
echo "View dataset at: https://huggingface.co/datasets/${REPO_ID}-v3.0"
