#!/usr/bin/env python

"""
Convert LeRobot dataset from v2.1 to v3.0 format.

Based on actual v3.0 format from thomas0829/bimanual-so100-handover-doll

Key changes:
- episodes.jsonl -> meta/episodes/chunk-000/file-000.parquet
- episodes_stats.jsonl -> meta/stats.json (global stats)
- tasks.jsonl -> meta/tasks.parquet
- file_000.parquet -> file-000.parquet (hyphen not underscore)
- Add quantile stats (q01, q10, q50, q90, q99)
"""

import argparse
import json
import logging
import shutil
from pathlib import Path

import jsonlines
import numpy as np
import pandas as pd
from huggingface_hub import HfApi, snapshot_download

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

V21 = "v2.1"
V30 = "v3.0"


def load_v21_episodes(root: Path) -> pd.DataFrame:
    """Load v2.1 episodes.jsonl as DataFrame."""
    episodes = []
    with jsonlines.open(root / "meta/episodes.jsonl") as reader:
        for item in reader:
            episodes.append(item)
    return pd.DataFrame(episodes)


def load_v21_episodes_stats(root: Path) -> dict:
    """Load v2.1 episodes_stats.jsonl."""
    stats = {}
    with jsonlines.open(root / "meta/episodes_stats.jsonl") as reader:
        for item in reader:
            ep_idx = item["episode_index"]
            stats[ep_idx] = item["stats"]
    return stats


def load_v21_tasks(root: Path) -> pd.DataFrame:
    """Load v2.1 tasks.jsonl as DataFrame."""
    tasks = []
    with jsonlines.open(root / "meta/tasks.jsonl") as reader:
        for item in reader:
            tasks.append({"task_index": item["task_index"], "task": item["task"]})
    df = pd.DataFrame(tasks)
    return df.set_index("task")  # task as index, task_index as column


def compute_quantiles(data: np.ndarray) -> dict:
    """Compute quantiles for v3.0 format."""
    return {
        "q01": np.quantile(data, 0.01, axis=0).tolist(),
        "q10": np.quantile(data, 0.10, axis=0).tolist(),
        "q50": np.quantile(data, 0.50, axis=0).tolist(),
        "q90": np.quantile(data, 0.90, axis=0).tolist(),
        "q99": np.quantile(data, 0.99, axis=0).tolist(),
    }


def compute_global_stats_from_episodes(episodes_stats: dict, features: dict) -> dict:
    """Aggregate per-episode stats into global stats for v3.0."""
    global_stats = {}
    
    # Get all feature names from first episode
    first_ep_stats = list(episodes_stats.values())[0]
    feature_names = list(first_ep_stats.keys())
    
    for feat_name in feature_names:
        # Collect all data for this feature across episodes
        all_mins = []
        all_maxs = []
        all_means = []
        all_stds = []
        all_counts = []
        
        for ep_stats in episodes_stats.values():
            if feat_name not in ep_stats:
                continue
            feat_stats = ep_stats[feat_name]
            all_mins.append(feat_stats["min"])
            all_maxs.append(feat_stats["max"])
            all_means.append(feat_stats["mean"])
            all_stds.append(feat_stats["std"])
            all_counts.append(feat_stats["count"])
        
        # Convert to arrays
        all_mins = np.array(all_mins)
        all_maxs = np.array(all_maxs)
        all_means = np.array(all_means)
        all_stds = np.array(all_stds)
        all_counts = np.array(all_counts)
        
        # Handle scalar counts (for features with single dimension)
        if all_counts.ndim == 1:
            # counts is 1D array of scalars
            weights = all_counts
        else:
            # counts is 2D array, use first column if all same
            weights = all_counts[:, 0] if all_counts.shape[1] > 0 else all_counts
        
        # Compute global stats
        global_stats[feat_name] = {
            "min": np.min(all_mins, axis=0).tolist(),
            "max": np.max(all_maxs, axis=0).tolist(),
            "mean": np.average(all_means, axis=0, weights=weights).tolist(),
            "std": np.sqrt(np.average(all_stds**2, axis=0, weights=weights)).tolist(),
            "count": np.sum(all_counts, axis=0).tolist() if all_counts.ndim > 1 else [int(np.sum(all_counts))],
        }
    
    return global_stats


def add_quantiles_to_episode_stats(ep_stats: dict, df_episode: pd.DataFrame, features: dict) -> dict:
    """Add quantile statistics to episode stats for v3.0 format."""
    for feat_name, feat_info in features.items():
        # Skip features not in episode stats
        if feat_name not in ep_stats:
            continue
            
        # For video features, we can't compute quantiles from data (not in parquet)
        # But we can still add quantiles to their stats if they exist
        if feat_info.get("dtype") == "video":
            # Video stats come from v2.1 episodes_stats, just add empty quantiles to maintain structure
            if feat_name in ep_stats and feat_name in features:
                # Get the shape from existing stats
                if "min" in ep_stats[feat_name]:
                    min_val = ep_stats[feat_name]["min"]
                    shape = np.array(min_val).shape
                    # Add quantiles as copies of min/max for video stats
                    ep_stats[feat_name]["q01"] = ep_stats[feat_name]["min"]
                    ep_stats[feat_name]["q10"] = ep_stats[feat_name]["min"]
                    ep_stats[feat_name]["q50"] = ep_stats[feat_name]["mean"]
                    ep_stats[feat_name]["q90"] = ep_stats[feat_name]["max"]
                    ep_stats[feat_name]["q99"] = ep_stats[feat_name]["max"]
            continue
        
        # For non-video features in data parquet, compute real quantiles
        if feat_name in df_episode.columns:
            # Get data for this feature from episode
            data = np.array([row for row in df_episode[feat_name]])
            
            # Add quantiles
            quantiles = compute_quantiles(data)
            ep_stats[feat_name].update(quantiles)
    
    return ep_stats


def convert_to_v30(root: Path, new_root: Path):
    """Convert v2.1 dataset to v3.0 format."""
    logging.info(f"Converting {root} to v3.0 format at {new_root}")
    
    # Create new directory structure
    new_root.mkdir(parents=True, exist_ok=True)
    (new_root / "meta").mkdir(exist_ok=True)
    (new_root / "meta/episodes/chunk-000").mkdir(parents=True, exist_ok=True)
    (new_root / "data/chunk-000").mkdir(parents=True, exist_ok=True)
    
    # 1. Load v2.1 metadata
    logging.info("Loading v2.1 metadata...")
    info = json.load(open(root / "meta/info.json"))
    v21_episodes = load_v21_episodes(root)
    v21_episodes_stats = load_v21_episodes_stats(root)
    v21_tasks = load_v21_tasks(root)
    
    # 2. Convert info.json
    logging.info("Converting info.json...")
    info["codebase_version"] = V30
    # Update path templates
    info["data_path"] = "data/chunk-{chunk_index:03d}/file-{file_index:03d}.parquet"
    info["video_path"] = "videos/{video_key}/chunk-{chunk_index:03d}/file-{file_index:03d}.mp4"
    # Remove v2.1 specific fields
    info.pop("total_chunks", None)
    info.pop("chunks_size", None)
    # Add v3.0 fields
    info["chunks_size"] = 1000
    info["data_files_size_in_mb"] = 200
    info["video_files_size_in_mb"] = 200
    
    with open(new_root / "meta/info.json", "w") as f:
        json.dump(info, f, indent=4)
    
    # 3. Convert tasks.jsonl to tasks.parquet
    logging.info("Converting tasks...")
    v21_tasks.to_parquet(new_root / "meta/tasks.parquet")
    
    # 4. Merge and convert data files (v2.1 has one file per episode, v3.0 has one combined file)
    logging.info("Converting and merging data files...")
    all_episodes_data = []
    for ep_file in sorted((root / "data/chunk-000").glob("episode_*.parquet")):
        df = pd.read_parquet(ep_file)
        all_episodes_data.append(df)
    
    df_combined = pd.concat(all_episodes_data, ignore_index=True)
    df_combined.to_parquet(new_root / "data/chunk-000/file-000.parquet", index=False)
    
    # 5. Merge and convert video files (requires ffmpeg)
    logging.info("Converting video files...")
    video_keys = [k for k, v in info["features"].items() if v.get("dtype") == "video"]
    for video_key in video_keys:
        old_video_dir = root / f"videos/chunk-000/{video_key}"
        new_video_dir = new_root / f"videos/{video_key}/chunk-000"
        new_video_dir.mkdir(parents=True, exist_ok=True)
        
        # Find all episode video files for this camera
        old_videos = sorted(old_video_dir.glob("episode_*.mp4"))
        if old_videos:
            # Create concat file for ffmpeg
            concat_file = new_root / f"concat_{video_key}.txt"
            with open(concat_file, "w") as f:
                for video in old_videos:
                    f.write(f"file '{video.absolute()}'\n")
            
            # Merge videos with ffmpeg
            new_video_file = new_video_dir / "file-000.mp4"
            import subprocess
            try:
                subprocess.run([
                    "ffmpeg", "-f", "concat", "-safe", "0", 
                    "-i", str(concat_file), 
                    "-c", "copy", str(new_video_file)
                ], check=True, capture_output=True)
                concat_file.unlink()  # Clean up
                logging.info(f"✓ Merged {len(old_videos)} videos for {video_key}")
            except Exception as e:
                logging.warning(f"⚠ Video merge failed for {video_key}: {e}")
                logging.warning("Copying first video only as fallback")
                shutil.copy(old_videos[0], new_video_file)
    
    # 6. Create episodes parquet with quantiles
    logging.info("Creating episodes parquet with quantiles...")
    episodes_data = []
    cumulative_index = 0  # Track dataset indices
    
    # Get video keys
    video_keys = [k for k, v in info["features"].items() if v.get("dtype") == "video"]
    
    for idx, row in v21_episodes.iterrows():
        ep_idx = row["episode_index"]
        ep_dict = row.to_dict()
        
        # Get episode stats
        ep_stats = v21_episodes_stats.get(ep_idx, {})
        
        # Load episode data for quantile computation (v2.1 has one file per episode)
        ep_file = root / "data/chunk-000" / f"episode_{ep_idx:06d}.parquet"
        if ep_file.exists():
            df_episode = pd.read_parquet(ep_file)
            
            # Add quantiles to stats
            ep_stats_with_q = add_quantiles_to_episode_stats(ep_stats, df_episode, info["features"])
            
            # Add data file indices
            ep_dict["data/chunk_index"] = 0
            ep_dict["data/file_index"] = 0
            
            # Add dataset range indices
            ep_length = len(df_episode)
            ep_dict["dataset_from_index"] = cumulative_index
            ep_dict["dataset_to_index"] = cumulative_index + ep_length
            cumulative_index += ep_length
            
            # Add video metadata for each camera
            for video_key in video_keys:
                ep_dict[f"videos/{video_key}/chunk_index"] = 0
                ep_dict[f"videos/{video_key}/file_index"] = 0
                # Calculate timestamps from frame data
                timestamps = df_episode["timestamp"].values
                ep_dict[f"videos/{video_key}/from_timestamp"] = float(timestamps[0])
                ep_dict[f"videos/{video_key}/to_timestamp"] = float(timestamps[-1])
        else:
            ep_stats_with_q = ep_stats
        
        # Flatten stats into episode dict
        for feat_name, feat_stats in ep_stats_with_q.items():
            for stat_name, stat_value in feat_stats.items():
                ep_dict[f"stats/{feat_name}/{stat_name}"] = stat_value
        
        # Add metadata fields
        ep_dict["meta/episodes/chunk_index"] = 0
        ep_dict["meta/episodes/file_index"] = 0
        
        episodes_data.append(ep_dict)
    
    df_episodes = pd.DataFrame(episodes_data)
    df_episodes.to_parquet(new_root / "meta/episodes/chunk-000/file-000.parquet", index=False)
    
    # 8. Create global stats.json
    logging.info("Creating global stats...")
    global_stats = compute_global_stats_from_episodes(v21_episodes_stats, info["features"])
    with open(new_root / "meta/stats.json", "w") as f:
        json.dump(global_stats, f, indent=4)
    
    # 9. Copy README if exists
    if (root / "README.md").exists():
        shutil.copy(root / "README.md", new_root / "README.md")
        # Update codebase version in README
        with open(new_root / "README.md") as f:
            content = f.read()
        content = content.replace('"codebase_version": "v2.1"', '"codebase_version": "v3.0"')
        with open(new_root / "README.md", "w") as f:
            f.write(content)
    
    logging.info(f"✓ Conversion complete! v3.0 dataset at: {new_root}")


def main():
    parser = argparse.ArgumentParser(description="Convert LeRobot dataset from v2.1 to v3.0")
    parser.add_argument("--repo-id", required=True, help="Dataset repo ID (e.g., thomas0829/put_the_cube_into_the_cup)")
    parser.add_argument("--root", default=None, help="Local root directory (default: ~/.cache/huggingface/lerobot)")
    parser.add_argument("--push-to-hub", action="store_true", help="Push to hub after conversion")
    
    args = parser.parse_args()
    
    # Determine paths
    if args.root:
        root = Path(args.root) / args.repo_id
    else:
        from pathlib import Path
        import os
        cache_dir = Path(os.path.expanduser("~/.cache/huggingface/lerobot"))
        root = cache_dir / args.repo_id
    
    # Download if not exists
    if not root.exists():
        logging.info(f"Downloading {args.repo_id}...")
        snapshot_download(repo_id=args.repo_id, repo_type="dataset", local_dir=root)
    
    # Convert
    new_root = root.parent / f"{root.name}_v30"
    if new_root.exists():
        shutil.rmtree(new_root)
    
    convert_to_v30(root, new_root)
    
    # Push to hub
    if args.push_to_hub:
        logging.info("Pushing to hub...")
        api = HfApi()
        new_repo_id = f"{args.repo_id}-v3.0"  # Use hyphen not underscore
        api.create_repo(repo_id=new_repo_id, repo_type="dataset", exist_ok=True)
        api.upload_folder(
            folder_path=new_root,
            repo_id=new_repo_id,
            repo_type="dataset",
            commit_message="Convert from v2.1 to v3.0"
        )
        logging.info(f"✓ Pushed to https://huggingface.co/datasets/{new_repo_id}")


if __name__ == "__main__":
    main()
