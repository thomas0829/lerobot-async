#!/usr/bin/env python3
"""
分析LeRobot數據集中每個episode的時長、幀數和實際fps
"""
import json
import os
from pathlib import Path
import cv2
import numpy as np

def analyze_dataset(dataset_path):
    """分析數據集中所有episode的統計信息"""
    dataset_path = Path(dataset_path)
    
    # 讀取meta_data中的info
    meta_path = dataset_path / "meta" / "info.json"
    if not meta_path.exists():
        print(f"❌ 找不到 {meta_path}")
        return
    
    with open(meta_path, 'r') as f:
        info = json.load(f)
    
    fps = info.get('fps', 30)
    print(f"📊 數據集信息:")
    print(f"  - 數據集路徑: {dataset_path}")
    print(f"  - 設定的FPS: {fps}")
    print(f"  - 總幀數: {info.get('total_frames', 'N/A')}")
    print(f"  - 總episodes: {info.get('total_episodes', 'N/A')}")
    print()
    
    # 分析每個episode
    episodes_data = []
    
    # 讀取data目錄下的parquet文件
    data_dir = dataset_path / "data"
    if not data_dir.exists():
        print(f"❌ 找不到data目錄: {data_dir}")
        return
    
    # 找出所有episode
    video_dir = dataset_path / "videos"
    if video_dir.exists():
        print("📹 分析視頻文件...")
        
        # 處理chunk結構
        for chunk_dir in sorted(video_dir.glob("chunk-*")):
            if not chunk_dir.is_dir():
                continue
            
            for cam_dir in sorted(chunk_dir.iterdir()):
                if cam_dir.is_dir():
                    camera_name = cam_dir.name
                    print(f"\n  相機: {camera_name}")
                    
                    video_files = sorted(cam_dir.glob("*.mp4"))
                    for video_file in video_files:
                        # 從文件名提取episode_index (例如: episode_000000.mp4)
                        ep_name = video_file.stem
                        if ep_name.startswith("episode_"):
                            ep_index = int(ep_name.split("_")[1])
                        else:
                            continue
                        
                        # 打開視頻文件獲取信息
                        cap = cv2.VideoCapture(str(video_file))
                        if not cap.isOpened():
                            print(f"    ⚠️  無法打開視頻: {video_file}")
                            continue
                        
                        # 獲取視頻屬性
                        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                        video_fps = cap.get(cv2.CAP_PROP_FPS)
                        video_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                        video_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        duration = frame_count / video_fps if video_fps > 0 else 0
                        
                        cap.release()
                        
                        # 記錄episode數據
                        episode_info = {
                            'episode': ep_index,
                            'camera': camera_name,
                            'frames': frame_count,
                            'video_fps': video_fps,
                            'duration_sec': duration,
                            'resolution': f"{video_width}x{video_height}",
                            'file_size_mb': video_file.stat().st_size / (1024 * 1024)
                        }
                        episodes_data.append(episode_info)
                        
                        # 即時顯示
                        print(f"    Episode {ep_index:03d}: {frame_count:4d} 幀, "
                              f"{video_fps:.2f} fps, {duration:.2f}秒, "
                              f"{video_width}x{video_height}, "
                              f"{episode_info['file_size_mb']:.2f}MB")
    
    if not episodes_data:
        print("\n❌ 沒有找到任何視頻文件")
        return
    
    # 按episode和camera分組統計
    print("\n" + "="*80)
    print("📈 統計分析:")
    print("="*80)
    
    # 按episode分組
    from collections import defaultdict
    episodes_by_num = defaultdict(list)
    for ep_data in episodes_data:
        episodes_by_num[ep_data['episode']].append(ep_data)
    
    # 打印每個episode的匯總信息
    print("\n各Episode詳細信息:")
    print("-" * 80)
    print(f"{'Ep':>3} | {'相機數':>6} | {'平均幀數':>8} | {'平均FPS':>8} | {'平均時長':>8} | {'總大小(MB)':>11}")
    print("-" * 80)
    
    all_durations = []
    all_frame_counts = []
    all_fps = []
    
    for ep_num in sorted(episodes_by_num.keys()):
        ep_list = episodes_by_num[ep_num]
        avg_frames = np.mean([ep['frames'] for ep in ep_list])
        avg_fps = np.mean([ep['video_fps'] for ep in ep_list])
        avg_duration = np.mean([ep['duration_sec'] for ep in ep_list])
        total_size = sum([ep['file_size_mb'] for ep in ep_list])
        
        all_durations.append(avg_duration)
        all_frame_counts.append(avg_frames)
        all_fps.append(avg_fps)
        
        print(f"{ep_num:3d} | {len(ep_list):6d} | {avg_frames:8.1f} | {avg_fps:8.2f} | {avg_duration:8.2f}s | {total_size:11.2f}")
    
    # 整體統計
    print("-" * 80)
    print(f"\n🔍 整體統計 (共{len(episodes_by_num)}個episodes):")
    print(f"  時長:")
    print(f"    - 最短: {min(all_durations):.2f}秒 (Episode {all_durations.index(min(all_durations))})")
    print(f"    - 最長: {max(all_durations):.2f}秒 (Episode {all_durations.index(max(all_durations))})")
    print(f"    - 平均: {np.mean(all_durations):.2f}秒")
    print(f"    - 標準差: {np.std(all_durations):.2f}秒")
    
    print(f"\n  幀數:")
    print(f"    - 最少: {min(all_frame_counts):.0f}幀 (Episode {all_frame_counts.index(min(all_frame_counts))})")
    print(f"    - 最多: {max(all_frame_counts):.0f}幀 (Episode {all_frame_counts.index(max(all_frame_counts))})")
    print(f"    - 平均: {np.mean(all_frame_counts):.0f}幀")
    print(f"    - 標準差: {np.std(all_frame_counts):.2f}幀")
    
    print(f"\n  實際FPS:")
    print(f"    - 最低: {min(all_fps):.2f} (Episode {all_fps.index(min(all_fps))})")
    print(f"    - 最高: {max(all_fps):.2f} (Episode {all_fps.index(max(all_fps))})")
    print(f"    - 平均: {np.mean(all_fps):.2f}")
    print(f"    - 標準差: {np.std(all_fps):.2f}")
    
    # 檢測趨勢
    print(f"\n📉 趨勢分析:")
    first_10_duration = np.mean(all_durations[:10]) if len(all_durations) >= 10 else np.mean(all_durations[:len(all_durations)//2])
    last_10_duration = np.mean(all_durations[-10:]) if len(all_durations) >= 10 else np.mean(all_durations[len(all_durations)//2:])
    duration_change = ((last_10_duration - first_10_duration) / first_10_duration) * 100
    
    first_10_frames = np.mean(all_frame_counts[:10]) if len(all_frame_counts) >= 10 else np.mean(all_frame_counts[:len(all_frame_counts)//2])
    last_10_frames = np.mean(all_frame_counts[-10:]) if len(all_frame_counts) >= 10 else np.mean(all_frame_counts[len(all_frame_counts)//2:])
    frames_change = ((last_10_frames - first_10_frames) / first_10_frames) * 100
    
    first_10_fps = np.mean(all_fps[:10]) if len(all_fps) >= 10 else np.mean(all_fps[:len(all_fps)//2])
    last_10_fps = np.mean(all_fps[-10:]) if len(all_fps) >= 10 else np.mean(all_fps[len(all_fps)//2:])
    fps_change = ((last_10_fps - first_10_fps) / first_10_fps) * 100
    
    print(f"  前10個episodes平均時長: {first_10_duration:.2f}秒")
    print(f"  後10個episodes平均時長: {last_10_duration:.2f}秒")
    print(f"  時長變化: {duration_change:+.1f}%")
    
    print(f"\n  前10個episodes平均幀數: {first_10_frames:.0f}幀")
    print(f"  後10個episodes平均幀數: {last_10_frames:.0f}幀")
    print(f"  幀數變化: {frames_change:+.1f}%")
    
    print(f"\n  前10個episodes平均FPS: {first_10_fps:.2f}")
    print(f"  後10個episodes平均FPS: {last_10_fps:.2f}")
    print(f"  FPS變化: {fps_change:+.1f}%")
    
    if duration_change < -20:
        print(f"\n⚠️  警告: 後期episodes的時長明顯縮短了 {abs(duration_change):.1f}%!")
        print(f"   這可能是由於:")
        print(f"   1. USB頻寬不足 (多相機同時錄製)")
        print(f"   2. 系統資源不足 (CPU/記憶體)")
        print(f"   3. 相機驅動問題 (幀丟失)")
    
    if fps_change < -20:
        print(f"\n⚠️  警告: 後期episodes的FPS明顯下降了 {abs(fps_change):.1f}%!")
        print(f"   建議檢查系統資源使用情況")

if __name__ == "__main__":
    import sys
    
    # 默認路徑
    default_path = Path.home() / ".cache/huggingface/lerobot/thomas0829/bimanual-so101-stacking-blocks-v2"
    
    if len(sys.argv) > 1:
        dataset_path = sys.argv[1]
    else:
        dataset_path = str(default_path)
        print(f"使用默認數據集路徑: {dataset_path}")
        print()
    
    analyze_dataset(dataset_path)
