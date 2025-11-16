#!/usr/bin/env python3
"""
檢查實際錄製時的timestamp和真實fps
"""
import json
from pathlib import Path
import pyarrow.parquet as pq
import numpy as np
from collections import defaultdict

def analyze_timestamps(dataset_path):
    """分析parquet數據中的timestamps"""
    dataset_path = Path(dataset_path)
    
    # 讀取data
    data_dir = dataset_path / "data"
    parquet_files = list(data_dir.glob("*.parquet"))
    
    # 如果沒找到，嘗試在chunk目錄中找
    if not parquet_files:
        parquet_files = list(data_dir.glob("chunk-*/*.parquet"))
    
    if not parquet_files:
        print("找不到parquet文件")
        return
    
    print(f"找到 {len(parquet_files)} 個parquet文件")
    
    # 讀取所有數據
    all_episodes = defaultdict(list)
    total_rows = 0
    columns = None
    
    for pf in sorted(parquet_files):
        table = pq.read_table(pf)
        if columns is None:
            columns = table.column_names
        
        # 提取需要的列
        episode_indices = table['episode_index'].to_pylist()
        timestamps = table['timestamp'].to_pylist()
        
        for ep_idx, ts in zip(episode_indices, timestamps):
            all_episodes[ep_idx].append(ts)
            total_rows += 1
    
    print(f"\n總共有 {total_rows} 條數據")
    print(f"Columns: {columns[:5]}..." if len(columns) > 5 else f"Columns: {columns}")
    
    # 按episode分析
    print(f"\n分析每個episode的實際FPS:")
    print("="*90)
    print(f"{'Ep':>3} | {'幀數':>6} | {'開始':>10} | {'結束':>10} | {'時長':>9} | {'實際FPS':>8} | {'avg間隔':>9} | {'std間隔':>9}")
    print("-"*90)
    
    results = []
    
    for ep_idx in sorted(all_episodes.keys()):
        timestamps = np.array(all_episodes[ep_idx])
        frame_count = len(timestamps)
        
        start_time = timestamps[0]
        end_time = timestamps[-1]
        duration = end_time - start_time
        
        if duration > 0:
            actual_fps = (frame_count - 1) / duration
        else:
            actual_fps = 0
        
        # 計算幀間隔
        if len(timestamps) > 1:
            intervals = np.diff(timestamps)
            avg_interval = np.mean(intervals)
            std_interval = np.std(intervals)
            min_interval = np.min(intervals)
            max_interval = np.max(intervals)
        else:
            avg_interval = 0
            std_interval = 0
            min_interval = 0
            max_interval = 0
        
        results.append({
            'episode': ep_idx,
            'frames': frame_count,
            'duration': duration,
            'actual_fps': actual_fps,
            'avg_interval': avg_interval,
            'std_interval': std_interval,
            'min_interval': min_interval,
            'max_interval': max_interval
        })
        
        print(f"{ep_idx:3d} | {frame_count:6d} | {start_time:10.3f} | {end_time:10.3f} | "
              f"{duration:8.2f}s | {actual_fps:8.2f} | {avg_interval:8.4f}s | {std_interval:8.4f}s")
    
    print("="*90)
    
    # 整體統計
    all_fps = np.array([r['actual_fps'] for r in results])
    all_intervals = np.array([r['avg_interval'] for r in results])
    all_std_intervals = np.array([r['std_interval'] for r in results])
    
    print(f"\n整體統計:")
    print(f"  實際FPS:")
    print(f"    - 平均: {np.mean(all_fps):.2f}")
    print(f"    - 標準差: {np.std(all_fps):.2f}")
    print(f"    - 最小: {np.min(all_fps):.2f} (Episode {np.argmin(all_fps)})")
    print(f"    - 最大: {np.max(all_fps):.2f} (Episode {np.argmax(all_fps)})")
    
    print(f"\n  幀間隔 (秒):")
    print(f"    - 平均: {np.mean(all_intervals):.4f}")
    print(f"    - 標準差的平均: {np.mean(all_std_intervals):.4f}")
    
    # 檢查異常
    print(f"\n⚠️  異常檢測:")
    low_fps_count = np.sum(all_fps < 25)
    if low_fps_count > 0:
        print(f"  有 {low_fps_count} 個episode的FPS低於25:")
        for r in results:
            if r['actual_fps'] < 25:
                print(f"    Episode {r['episode']}: {r['actual_fps']:.2f} fps")
    else:
        print(f"  ✅ 所有episode的FPS都正常 (>=25 fps)")
    
    high_std_count = np.sum(all_std_intervals > 0.01)
    if high_std_count > 0:
        print(f"\n  有 {high_std_count} 個episode的幀間隔不穩定 (標準差>0.01秒):")
        for r in results:
            if r['std_interval'] > 0.01:
                print(f"    Episode {r['episode']}: std={r['std_interval']:.4f}秒 "
                      f"(最小間隔={r['min_interval']:.4f}, 最大間隔={r['max_interval']:.4f})")
    else:
        print(f"  ✅ 所有episode的幀間隔都很穩定")
    
    # 趨勢分析
    print(f"\n📉 FPS趨勢分析:")
    first_10_fps = np.mean(all_fps[:10])
    last_10_fps = np.mean(all_fps[-10:])
    fps_change = ((last_10_fps - first_10_fps) / first_10_fps) * 100
    
    print(f"  前10個episodes平均FPS: {first_10_fps:.2f}")
    print(f"  後10個episodes平均FPS: {last_10_fps:.2f}")
    print(f"  FPS變化: {fps_change:+.1f}%")
    
    if abs(fps_change) > 5:
        print(f"\n  ⚠️ FPS有明顯變化！")
    else:
        print(f"\n  ✅ FPS保持穩定")
    
    # 檢查間隔異常
    print(f"\n📊 幀間隔異常檢測:")
    for r in results:
        if r['max_interval'] > 0.1:  # 超過100ms的間隔
            print(f"  Episode {r['episode']}: 最大間隔 {r['max_interval']:.4f}秒 (可能有幀丟失)")

if __name__ == "__main__":
    import sys
    
    default_path = Path.home() / ".cache/huggingface/lerobot/thomas0829/bimanual-so101-stacking-blocks-v2"
    
    if len(sys.argv) > 1:
        dataset_path = sys.argv[1]
    else:
        dataset_path = str(default_path)
        print(f"使用默認數據集路徑: {dataset_path}\n")
    
    analyze_timestamps(dataset_path)
