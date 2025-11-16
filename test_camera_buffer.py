#!/usr/bin/env python3
"""
測試相機buffer flush - 檢查是否還有延遲問題
"""
import time
import cv2
import numpy as np
from pathlib import Path
import sys

# 添加src到路徑
sys.path.insert(0, str(Path(__file__).parent / "src"))

from lerobot.cameras.opencv.camera_opencv import OpenCVCamera
from lerobot.cameras.opencv.configuration_opencv import OpenCVCameraConfig, ColorMode

def test_camera_latency(camera_index, duration_seconds=60):
    """
    測試相機延遲
    
    在畫面中顯示當前時間戳，通過對比系統時間和畫面中的時間來檢測延遲
    """
    print(f"正在測試相機 {camera_index} 的延遲情況...")
    print(f"測試時長: {duration_seconds}秒")
    print("=" * 60)
    
    # 創建相機配置
    config = OpenCVCameraConfig(
        index_or_path=camera_index,
        fps=30,
        width=640,
        height=480,
        color_mode=ColorMode.RGB
    )
    
    # 創建相機
    camera = OpenCVCamera(config)
    
    camera.connect()
    print(f"相機已連接: {camera}")
    
    # 測試參數
    frame_count = 0
    start_time = time.time()
    last_print_time = start_time
    
    capture_times = []
    processing_times = []
    
    try:
        while (time.time() - start_time) < duration_seconds:
            # 記錄讀取時間
            read_start = time.perf_counter()
            frame = camera.async_read(timeout_ms=500)
            read_end = time.perf_counter()
            
            read_time_ms = (read_end - read_start) * 1000
            processing_times.append(read_time_ms)
            
            frame_count += 1
            current_time = time.time()
            
            # 每秒統計一次
            if current_time - last_print_time >= 1.0:
                elapsed = current_time - start_time
                fps = frame_count / elapsed
                avg_read_time = np.mean(processing_times[-30:]) if len(processing_times) >= 30 else np.mean(processing_times)
                
                print(f"[{elapsed:6.1f}s] 幀數: {frame_count:5d} | "
                      f"FPS: {fps:5.2f} | "
                      f"讀取時間: {avg_read_time:5.1f}ms")
                
                last_print_time = current_time
            
            # 小延遲避免CPU 100%
            time.sleep(0.001)
    
    except KeyboardInterrupt:
        print("\n測試被中斷")
    
    finally:
        camera.disconnect()
        print("\n相機已斷開")
    
    # 統計
    print("\n" + "=" * 60)
    print("測試統計:")
    print(f"  總幀數: {frame_count}")
    print(f"  總時長: {time.time() - start_time:.2f}秒")
    print(f"  平均FPS: {frame_count / (time.time() - start_time):.2f}")
    
    if processing_times:
        print(f"\n  讀取時間統計:")
        print(f"    平均: {np.mean(processing_times):.2f}ms")
        print(f"    最小: {np.min(processing_times):.2f}ms")
        print(f"    最大: {np.max(processing_times):.2f}ms")
        print(f"    標準差: {np.std(processing_times):.2f}ms")
        
        # 檢查是否有趨勢
        if len(processing_times) > 100:
            first_50 = np.mean(processing_times[:50])
            last_50 = np.mean(processing_times[-50:])
            change_percent = ((last_50 - first_50) / first_50) * 100
            
            print(f"\n  性能趨勢:")
            print(f"    前50幀平均讀取時間: {first_50:.2f}ms")
            print(f"    後50幀平均讀取時間: {last_50:.2f}ms")
            print(f"    變化: {change_percent:+.1f}%")
            
            if change_percent > 20:
                print(f"    ⚠️  警告: 後期讀取時間明顯增加，可能仍有buffer問題")
            elif change_percent < -20:
                print(f"    ✅ 性能改善了！")
            else:
                print(f"    ✅ 性能保持穩定")

def test_multiple_cameras(camera_indices, duration_seconds=30):
    """測試多個相機同時讀取"""
    print(f"正在測試 {len(camera_indices)} 個相機...")
    print("=" * 60)
    
    cameras = []
    for idx in camera_indices:
        try:
            config = OpenCVCameraConfig(
                index_or_path=idx,
                fps=30,
                width=640,
                height=480,
                color_mode=ColorMode.RGB
            )
            camera = OpenCVCamera(config)
            camera.connect()
            cameras.append(camera)
            print(f"✅ 相機 {idx} 已連接")
        except Exception as e:
            print(f"❌ 相機 {idx} 連接失敗: {e}")
    
    if not cameras:
        print("沒有可用的相機")
        return
    
    print(f"\n開始同時讀取 {len(cameras)} 個相機...")
    
    frame_counts = [0] * len(cameras)
    start_time = time.time()
    last_print_time = start_time
    
    try:
        while (time.time() - start_time) < duration_seconds:
            # 同時讀取所有相機
            for i, camera in enumerate(cameras):
                try:
                    frame = camera.async_read(timeout_ms=500)
                    frame_counts[i] += 1
                except Exception as e:
                    print(f"相機 {camera.index_or_path} 讀取失敗: {e}")
            
            # 每秒統計
            current_time = time.time()
            if current_time - last_print_time >= 1.0:
                elapsed = current_time - start_time
                fps_list = [count / elapsed for count in frame_counts]
                
                fps_str = " | ".join([f"Cam{cameras[i].index_or_path}: {fps:.1f}fps" 
                                      for i, fps in enumerate(fps_list)])
                print(f"[{elapsed:5.1f}s] {fps_str}")
                
                last_print_time = current_time
            
            time.sleep(0.001)
    
    except KeyboardInterrupt:
        print("\n測試被中斷")
    
    finally:
        for camera in cameras:
            camera.disconnect()
        print("\n所有相機已斷開")
    
    # 統計
    print("\n" + "=" * 60)
    print("測試統計:")
    elapsed = time.time() - start_time
    for i, (camera, count) in enumerate(zip(cameras, frame_counts)):
        fps = count / elapsed
        print(f"  相機 {camera.index_or_path}: {count} 幀, 平均 {fps:.2f} fps")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法:")
        print("  單相機測試: python test_camera_buffer.py <camera_index> [duration]")
        print("  多相機測試: python test_camera_buffer.py <cam1> <cam2> <cam3> ... [duration]")
        print("\n例如:")
        print("  python test_camera_buffer.py 4 60          # 測試相機4，60秒")
        print("  python test_camera_buffer.py 4 6 8 30      # 測試相機4,6,8，30秒")
        sys.exit(1)
    
    # 解析參數
    try:
        # 最後一個參數可能是duration
        if sys.argv[-1].isdigit() and int(sys.argv[-1]) > 10:
            duration = int(sys.argv[-1])
            camera_indices = [int(x) for x in sys.argv[1:-1]]
        else:
            duration = 30
            camera_indices = [int(x) for x in sys.argv[1:]]
    except ValueError:
        print("❌ 參數錯誤：相機索引必須是整數")
        sys.exit(1)
    
    if len(camera_indices) == 1:
        test_camera_latency(camera_indices[0], duration)
    else:
        test_multiple_cameras(camera_indices, duration)
