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
    print(f"Columns: {columns}")
    
    # 按episode分組
    episodes = df.groupby('episode_index')
    
    print(f"\n分析每個episode的實際FPS:")
    print("="*80)
    print(f"{'Ep':>3} | {'幀數':>6} | {'開始時間':>10} | {'結束時間':>10} | {'時長(秒)':>9} | {'實際FPS':>8} | {'目標FPS':>8}")
    print("-"*80)
    
    results = []
    
    for ep_idx, group in episodes:
        frame_count = len(group)
        timestamps = group['timestamp'].values
        
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
            target_fps = 1 / avg_interval if avg_interval > 0 else 0
        else:
            avg_interval = 0
            std_interval = 0
            min_interval = 0
            max_interval = 0
            target_fps = 0
        
        results.append({
            'episode': ep_idx,
            'frames': frame_count,
            'duration': duration,
            'actual_fps': actual_fps,
            'target_fps': target_fps,
            'avg_interval': avg_interval,
            'std_interval': std_interval,
            'min_interval': min_interval,
            'max_interval': max_interval
        })
        
        print(f"{ep_idx:3d} | {frame_count:6d} | {start_time:10.3f} | {end_time:10.3f} | {duration:9.3f} | {actual_fps:8.2f} | {target_fps:8.2f}")
    
    print("="*80)
    
    # 整體統計
    results_df = pd.DataFrame(results)
    
    print(f"\n整體統計:")
    print(f"  實際FPS:")
    print(f"    - 平均: {results_df['actual_fps'].mean():.2f}")
    print(f"    - 標準差: {results_df['actual_fps'].std():.2f}")
    print(f"    - 最小: {results_df['actual_fps'].min():.2f} (Episode {results_df['actual_fps'].idxmin()})")
    print(f"    - 最大: {results_df['actual_fps'].max():.2f} (Episode {results_df['actual_fps'].idxmax()})")
    
    print(f"\n  幀間隔 (秒):")
    print(f"    - 平均: {results_df['avg_interval'].mean():.4f}")
    print(f"    - 標準差的平均: {results_df['std_interval'].mean():.4f}")
    
    # 檢查異常
    print(f"\n⚠️  異常檢測:")
    low_fps_episodes = results_df[results_df['actual_fps'] < 25]
    if len(low_fps_episodes) > 0:
        print(f"  有 {len(low_fps_episodes)} 個episode的FPS低於25:")
        for idx, row in low_fps_episodes.iterrows():
            print(f"    Episode {row['episode']}: {row['actual_fps']:.2f} fps")
    else:
        print(f"  ✅ 所有episode的FPS都正常 (>=25 fps)")
    
    high_std_episodes = results_df[results_df['std_interval'] > 0.01]
    if len(high_std_episodes) > 0:
        print(f"\n  有 {len(high_std_episodes)} 個episode的幀間隔不穩定 (標準差>0.01秒):")
        for idx, row in high_std_episodes.iterrows():
            print(f"    Episode {row['episode']}: std={row['std_interval']:.4f}秒 "
                  f"(最小間隔={row['min_interval']:.4f}, 最大間隔={row['max_interval']:.4f})")
    else:
        print(f"  ✅ 所有episode的幀間隔都很穩定")
    
    # 趨勢分析
    print(f"\n📉 FPS趨勢分析:")
    first_10_fps = results_df.iloc[:10]['actual_fps'].mean()
    last_10_fps = results_df.iloc[-10:]['actual_fps'].mean()
    fps_change = ((last_10_fps - first_10_fps) / first_10_fps) * 100
    
    print(f"  前10個episodes平均FPS: {first_10_fps:.2f}")
    print(f"  後10個episodes平均FPS: {last_10_fps:.2f}")
    print(f"  FPS變化: {fps_change:+.1f}%")
    
    if abs(fps_change) > 5:
        print(f"\n  ⚠️ FPS有明顯變化！")
    else:
        print(f"\n  ✅ FPS保持穩定")

if __name__ == "__main__":
    import sys
    
    default_path = Path.home() / ".cache/huggingface/lerobot/thomas0829/bimanual-so101-stacking-blocks-v2"
    
    if len(sys.argv) > 1:
        dataset_path = sys.argv[1]
    else:
        dataset_path = str(default_path)
        print(f"使用默認數據集路徑: {dataset_path}\n")
    
    analyze_timestamps(dataset_path)
