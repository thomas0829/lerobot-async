#!/usr/bin/env python3
"""
Test script for resume recording functionality.
测试 resume 记录功能的脚本。

This script demonstrates:
1. Creating a new dataset
2. Resuming the dataset to add more episodes
3. Verifying the episode count

Usage:
    python test_resume_functionality.py
"""

import tempfile
import shutil
from pathlib import Path
from lerobot.datasets.lerobot_dataset import LeRobotDataset

def test_resume_functionality():
    """Test dataset resume functionality."""
    
    # Create a temporary directory for testing
    test_dir = Path(tempfile.mkdtemp(prefix="lerobot_resume_test_"))
    print(f"📁 Test directory: {test_dir}")
    
    try:
        # Define dataset parameters
        repo_id = "test/resume_test"
        fps = 30
        features = {
            "observation.state": {
                "dtype": "float32",
                "shape": (6,),
                "names": ["x", "y", "z", "roll", "pitch", "yaw"]
            },
            "action": {
                "dtype": "float32", 
                "shape": (6,),
                "names": ["x", "y", "z", "roll", "pitch", "yaw"]
            }
        }
        
        print("\n" + "="*60)
        print("Step 1: Create new dataset")
        print("="*60)
        
        # Create new dataset
        dataset1 = LeRobotDataset.create(
            repo_id=repo_id,
            fps=fps,
            features=features,
            root=test_dir,
            use_videos=False,
            resume=False,
        )
        
        print(f"✅ Created dataset: {dataset1.repo_id}")
        print(f"   Episodes: {dataset1.meta.total_episodes}")
        print(f"   Frames: {dataset1.meta.total_frames}")
        
        # Simulate recording some episodes (simplified version)
        print("\n📹 Simulating recording 3 episodes...")
        for ep_idx in range(3):
            # Create a simple episode buffer
            episode_buffer = dataset1.create_episode_buffer()
            
            # Add 5 frames to each episode
            for frame_idx in range(5):
                episode_buffer["frame_index"].append(frame_idx)
                episode_buffer["timestamp"].append(frame_idx / fps)
                episode_buffer["task"].append("test_task")
                episode_buffer["observation.state"].append([1.0] * 6)
                episode_buffer["action"].append([0.5] * 6)
                episode_buffer["size"] += 1
            
            # Save episode (this will increment total_episodes)
            dataset1.save_episode()
            print(f"   Episode {ep_idx}: saved")
        
        print(f"\n✅ After first recording:")
        print(f"   Total episodes: {dataset1.meta.total_episodes}")
        print(f"   Total frames: {dataset1.meta.total_frames}")
        
        # Clean up first dataset
        if hasattr(dataset1, 'stop_async_saver'):
            dataset1.stop_async_saver()
        
        print("\n" + "="*60)
        print("Step 2: Resume dataset to add more episodes")
        print("="*60)
        
        # Resume the dataset
        dataset2 = LeRobotDataset.create(
            repo_id=repo_id,
            fps=fps,
            features=features,
            root=test_dir,
            use_videos=False,
            resume=True,  # ← Resume mode!
        )
        
        print(f"✅ Resumed dataset: {dataset2.repo_id}")
        print(f"   Existing episodes: {dataset2.meta.total_episodes}")
        print(f"   Existing frames: {dataset2.meta.total_frames}")
        
        # Record more episodes
        print("\n📹 Recording 2 more episodes...")
        for ep_idx in range(2):
            episode_buffer = dataset2.create_episode_buffer()
            
            # Add 5 frames
            for frame_idx in range(5):
                episode_buffer["frame_index"].append(frame_idx)
                episode_buffer["timestamp"].append(frame_idx / fps)
                episode_buffer["task"].append("test_task")
                episode_buffer["observation.state"].append([2.0] * 6)
                episode_buffer["action"].append([1.0] * 6)
                episode_buffer["size"] += 1
            
            dataset2.save_episode()
            actual_ep_idx = dataset2.meta.total_episodes - 1
            print(f"   Episode {actual_ep_idx}: saved")
        
        print(f"\n✅ After resume recording:")
        print(f"   Total episodes: {dataset2.meta.total_episodes}")
        print(f"   Total frames: {dataset2.meta.total_frames}")
        
        # Verify counts
        print("\n" + "="*60)
        print("Step 3: Verify results")
        print("="*60)
        
        expected_episodes = 5  # 3 from first + 2 from resume
        expected_frames = 25   # 5 episodes * 5 frames each
        
        if dataset2.meta.total_episodes == expected_episodes:
            print(f"✅ Episode count correct: {dataset2.meta.total_episodes}")
        else:
            print(f"❌ Episode count wrong: {dataset2.meta.total_episodes} (expected {expected_episodes})")
            
        if dataset2.meta.total_frames == expected_frames:
            print(f"✅ Frame count correct: {dataset2.meta.total_frames}")
        else:
            print(f"❌ Frame count wrong: {dataset2.meta.total_frames} (expected {expected_frames})")
        
        # Check that parquet files exist
        parquet_files = list((test_dir / "data").rglob("*.parquet"))
        if len(parquet_files) == expected_episodes:
            print(f"✅ Parquet files correct: {len(parquet_files)}")
        else:
            print(f"❌ Parquet files wrong: {len(parquet_files)} (expected {expected_episodes})")
        
        print("\n" + "="*60)
        print("✅ Resume functionality test PASSED!")
        print("="*60)
        
        # Clean up
        if hasattr(dataset2, 'stop_async_saver'):
            dataset2.stop_async_saver()
            
    except Exception as e:
        print(f"\n❌ Test FAILED with error:")
        print(f"   {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Clean up test directory
        if test_dir.exists():
            shutil.rmtree(test_dir)
            print(f"\n🧹 Cleaned up test directory: {test_dir}")

if __name__ == "__main__":
    print("="*60)
    print("Testing LeRobot Dataset Resume Functionality")
    print("="*60)
    test_resume_functionality()
