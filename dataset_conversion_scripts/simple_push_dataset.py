#!/usr/bin/env python

"""
Simple script to push a local LeRobot dataset to the hub with a new repo_id.
This is much simpler than converting between versions when the dataset is already in the correct format.

Usage:
python simple_push_dataset.py \
    --local-dir ~/.cache/huggingface/lerobot/thomas0829/put_the_cube_into_the_cup \
    --repo-id thomas0829/put_the_cube_into_the_cup_v3.0
"""

import argparse
import logging
from pathlib import Path

from lerobot.datasets.lerobot_dataset import LeRobotDataset

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Push local dataset to hub with new name")
    parser.add_argument(
        "--local-dir",
        type=str,
        required=True,
        help="Path to local dataset directory",
    )
    parser.add_argument(
        "--repo-id",
        type=str,
        required=True,
        help="New repository ID on the hub (e.g., 'username/dataset_v3.0')",
    )
    args = parser.parse_args()

    local_dir = Path(args.local_dir).expanduser()
    
    if not local_dir.exists():
        raise ValueError(f"Local directory does not exist: {local_dir}")
    
    logger.info(f"Loading dataset from {local_dir}")
    logger.info(f"Will push to hub as: {args.repo_id}")
    
    # Load the dataset
    dataset = LeRobotDataset(str(local_dir))
    
    logger.info(f"Dataset info:")
    logger.info(f"  - Number of episodes: {dataset.num_episodes}")
    logger.info(f"  - Total frames: {dataset.num_frames}")
    logger.info(f"  - FPS: {dataset.fps}")
    
    # Push to hub with new repo_id
    logger.info(f"Pushing to hub as {args.repo_id}...")
    dataset.push_to_hub(args.repo_id)
    
    logger.info("✓ Done! Dataset pushed successfully")
    logger.info(f"View at: https://huggingface.co/datasets/{args.repo_id}")


if __name__ == "__main__":
    main()
