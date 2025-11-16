#!/usr/bin/env python3
"""
壓力測試：模擬真實雙臂錄製場景
- 4 個機器人 (2 follower + 2 leader)
- 3 個相機
- async 數據保存
- 模擬編碼負載
"""

import argparse
import queue
import sys
import threading
import time
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from lerobot.cameras.opencv.camera_opencv import OpenCVCamera, OpenCVCameraConfig


class SimulatedRobot:
    """模擬單個機器人手臂的 serial 讀取"""
    
    def __init__(self, name: str, read_delay_ms: float = 5.0):
        self.name = name
        self.read_delay_ms = read_delay_ms
        self.position = np.random.rand(6)  # 6 個關節
    
    def get_observation(self) -> dict:
        """模擬 sync_read Present_Position"""
        time.sleep(self.read_delay_ms / 1000.0)
        # 模擬輕微變化
        self.position += np.random.randn(6) * 0.01
        return {f"{self.name}_{i}.pos": self.position[i] for i in range(6)}


class DataSaver:
    """模擬 async episode saving"""
    
    def __init__(self, save_delay_ms: float = 10.0):
        self.queue = queue.Queue()
        self.save_delay_ms = save_delay_ms
        self.running = False
        self.thread = None
        self.saved_count = 0
    
    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._save_loop, daemon=True)
        self.thread.start()
    
    def _save_loop(self):
        while self.running:
            try:
                data = self.queue.get(timeout=0.1)
                # 模擬保存操作
                time.sleep(self.save_delay_ms / 1000.0)
                self.saved_count += 1
                self.queue.task_done()
            except queue.Empty:
                continue
    
    def queue_frame(self, frame_data: dict):
        self.queue.put(frame_data)
    
    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
    
    def get_queue_size(self) -> int:
        return self.queue.qsize()


class FPSCounter:
    """FPS 計數器"""
    
    def __init__(self, window_size: int = 30):
        self.window_size = window_size
        self.timestamps = []
    
    def tick(self):
        now = time.perf_counter()
        self.timestamps.append(now)
        if len(self.timestamps) > self.window_size:
            self.timestamps.pop(0)
    
    def get_fps(self) -> float:
        if len(self.timestamps) < 2:
            return 0.0
        elapsed = self.timestamps[-1] - self.timestamps[0]
        return (len(self.timestamps) - 1) / elapsed if elapsed > 0 else 0.0


def stress_test(
    camera_indices: list[int],
    duration_seconds: int = 60,
    show_preview: bool = False,
    robot_read_delay_ms: float = 5.0,  # 每個機器人 5ms
):
    """
    壓力測試主函數
    
    模擬真實錄製場景:
    - 4 個機器人 (follower_left, follower_right, leader_left, leader_right)
    - N 個相機
    - async 數據保存
    - 30Hz 控制迴圈
    """
    print("🔥 LeRobot 雙臂錄製壓力測試 (4 個機器人)")
    print("=" * 80)
    print(f"測試配置:")
    print(f"  - 機器人數量: 4 (2 follower + 2 leader)")
    print(f"  - 相機數量: {len(camera_indices)}")
    print(f"  - 測試時長: {duration_seconds}秒")
    print(f"  - 顯示預覽: {'是' if show_preview else '否'}")
    print(f"  - 每個機器人讀取延遲: {robot_read_delay_ms:.1f}ms")
    print("=" * 80)
    
    # 初始化相機
    cameras = {}
    fps_counters = {}
    
    for idx in camera_indices:
        config = OpenCVCameraConfig(
            index_or_path=idx,
            width=640,
            height=480,
            fps=30,
        )
        cam = OpenCVCamera(config)
        cam.connect()
        cameras[idx] = cam
        fps_counters[idx] = FPSCounter()
        print(f"✅ 相機 {idx} 已連接")
    
    # 初始化 4 個機器人
    robots = {
        "follower_left": SimulatedRobot("follower_left", robot_read_delay_ms),
        "follower_right": SimulatedRobot("follower_right", robot_read_delay_ms),
        "leader_left": SimulatedRobot("leader_left", robot_read_delay_ms),
        "leader_right": SimulatedRobot("leader_right", robot_read_delay_ms),
    }
    print(f"✅ 4 個模擬機器人已初始化")
    
    # 初始化數據保存器
    saver = DataSaver(save_delay_ms=10.0)
    saver.start()
    print("✅ 數據保存器已啟動")
    
    # Warm-up 相機
    print("\n🔥 相機 Warm-up (5秒)...")
    warmup_start = time.perf_counter()
    warmup_frames = 0
    while time.perf_counter() - warmup_start < 5.0:
        for cam in cameras.values():
            _ = cam.async_read(timeout_ms=1000)
        warmup_frames += 1
        time.sleep(1.0 / 30.0)  # 30Hz
    print(f"✅ Warm-up 完成！讀取了 {warmup_frames} 幀")
    
    # 測試統計
    loop_times = []
    camera_read_times = []
    robot_read_times = []
    queue_sizes = []
    
    # 用於計算每秒的平均值
    last_print_idx = 0
    
    print("\n開始壓力測試...")
    print("-" * 80)
    print(f"{'時間':>8} | {'總FPS':>8} | {'Cam4':>5} | {'Cam6':>5} | {'Cam8':>5} | "
          f"{'相機讀取':>10} | {'機器人讀取':>12} | {'隊列':>8}")
    print("-" * 80)
    
    start_time = time.perf_counter()
    iteration = 0
    
    try:
        while time.perf_counter() - start_time < duration_seconds:
            loop_start = time.perf_counter()
            
            # 1. 讀取所有相機 (async)
            cam_read_start = time.perf_counter()
            frames = {}
            for idx, cam in cameras.items():
                frames[idx] = cam.async_read(timeout_ms=1000)
                fps_counters[idx].tick()
            cam_read_time = (time.perf_counter() - cam_read_start) * 1000
            camera_read_times.append(cam_read_time)
            
            # 2. 讀取所有機器人狀態 (serial, 依序執行)
            robot_read_start = time.perf_counter()
            robot_obs = {}
            for robot_name, robot in robots.items():
                robot_obs.update(robot.get_observation())
            robot_read_time = (time.perf_counter() - robot_read_start) * 1000
            robot_read_times.append(robot_read_time)
            
            # 3. 組合數據並加入保存隊列
            frame_data = {
                "frames": frames,
                "robot_state": robot_obs,
                "timestamp": time.perf_counter(),
            }
            saver.queue_frame(frame_data)
            
            # 4. 顯示預覽 (可選)
            if show_preview and 4 in frames:
                cv2.imshow("Preview", frames[4])
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            
            # 記錄循環時間和隊列大小
            loop_time = (time.perf_counter() - loop_start) * 1000
            loop_times.append(loop_time)
            queue_sizes.append(saver.get_queue_size())
            
            # 每秒打印一次統計
            iteration += 1
            if iteration % 30 == 0:
                elapsed = time.perf_counter() - start_time
                avg_fps = sum(c.get_fps() for c in fps_counters.values()) / len(fps_counters)
                cam_fps = {idx: c.get_fps() for idx, c in fps_counters.items()}
                
                # 計算這一秒的平均讀取時間
                avg_cam_read = np.mean(camera_read_times[last_print_idx:])
                avg_robot_read = np.mean(robot_read_times[last_print_idx:])
                last_print_idx = len(camera_read_times)
                
                print(f"{elapsed:>7.0f}s | {avg_fps:>7.2f} | "
                      f"{cam_fps.get(4, 0):>5.1f} | {cam_fps.get(6, 0):>5.1f} | {cam_fps.get(8, 0):>5.1f} | "
                      f"{avg_cam_read:>8.1f}ms | {avg_robot_read:>10.1f}ms | "
                      f"{saver.get_queue_size():>6}")
            
            # 維持 30Hz
            target_loop_time = 1.0 / 30.0
            sleep_time = target_loop_time - (time.perf_counter() - loop_start)
            if sleep_time > 0:
                time.sleep(sleep_time)
    
    except KeyboardInterrupt:
        print("\n\n⚠️ 測試被中斷")
    
    # 清理
    print("\n" + "=" * 80)
    print("清理資源...")
    
    saver.stop()
    for cam in cameras.values():
        cam.disconnect()
    if show_preview:
        cv2.destroyAllWindows()
    
    # 統計報告
    print("\n" + "=" * 80)
    print("📊 測試統計:")
    print("=" * 80)
    
    total_time = time.perf_counter() - start_time
    print(f"\n測試時長: {total_time:.2f}秒")
    
    print("\n相機FPS:")
    for idx, counter in fps_counters.items():
        total_frames = len([t for t in counter.timestamps])
        avg_fps = total_frames / total_time if total_time > 0 else 0
        final_fps = counter.get_fps()
        print(f"  相機 {idx}:")
        print(f"    - 總幀數: {total_frames}")
        print(f"    - 平均FPS: {avg_fps:.2f}")
        print(f"    - 最終FPS: {final_fps:.2f}")
    
    print("\n循環時間統計:")
    print(f"  平均: {np.mean(loop_times):.2f}ms")
    print(f"  最小: {np.min(loop_times):.2f}ms")
    print(f"  最大: {np.max(loop_times):.2f}ms")
    print(f"  標準差: {np.std(loop_times):.2f}ms")
    
    # 性能趨勢分析
    if len(loop_times) > 100:
        first_50 = np.mean(loop_times[:50])
        last_50 = np.mean(loop_times[-50:])
        change_pct = ((last_50 - first_50) / first_50) * 100
        print(f"\n  性能趨勢:")
        print(f"    前50次循環: {first_50:.2f}ms")
        print(f"    後50次循環: {last_50:.2f}ms")
        print(f"    變化: {change_pct:+.1f}%")
        if change_pct > 10:
            print(f"    ⚠️ 性能有衰退")
        else:
            print(f"    ✅ 性能穩定")
    
    print("\n相機讀取時間:")
    print(f"  平均: {np.mean(camera_read_times):.2f}ms")
    print(f"  最大: {np.max(camera_read_times):.2f}ms")
    
    print("\n機器人讀取時間 (4 個機器人總和):")
    print(f"  平均: {np.mean(robot_read_times):.2f}ms")
    print(f"  最大: {np.max(robot_read_times):.2f}ms")
    print(f"  理論最小值: {robot_read_delay_ms * 4:.1f}ms (4個機器人 × {robot_read_delay_ms}ms)")
    
    print("\n保存隊列:")
    print(f"  平均大小: {np.mean(queue_sizes):.1f}")
    print(f"  最大大小: {np.max(queue_sizes)}")
    print(f"  已保存: {saver.saved_count} 幀")
    max_queue = np.max(queue_sizes)
    if max_queue > 100:
        print(f"  ⚠️ 隊列累積過多，保存速度跟不上")
    else:
        print(f"  ✅ 保存速度正常")
    
    # 最終評估
    print("\n" + "=" * 80)
    print("🎯 最終評估:")
    
    avg_total_fps = sum(len(c.timestamps) for c in fps_counters.values()) / len(fps_counters) / total_time
    avg_loop_time = np.mean(loop_times)
    max_queue = np.max(queue_sizes)
    
    issues = []
    if avg_total_fps < 28:
        issues.append(f"❌ 平均 FPS 過低 ({avg_total_fps:.1f} < 28)")
    if avg_loop_time > 40:
        issues.append(f"❌ 循環時間過長 ({avg_loop_time:.1f}ms > 40ms)")
    if max_queue > 100:
        issues.append(f"❌ 隊列累積過多 (max={max_queue})")
    
    if not issues:
        print("✅ 系統性能優秀！可以穩定錄製數據")
    else:
        print("⚠️ 發現以下問題:")
        for issue in issues:
            print(f"   {issue}")
        
        print("\n建議:")
        if avg_total_fps < 28:
            print("   - 降低相機解析度 (1920x1080 → 1280x720)")
            print("   - 減少相機數量")
        if avg_loop_time > 40:
            print("   - 檢查 USB 拓撲 (每個 USB 控制器不超過 2 個相機)")
            print("   - 優化機器人通信速度")
        if max_queue > 100:
            print("   - 增加 encoding batch size")
            print("   - 檢查磁碟 I/O 速度")


def main():
    parser = argparse.ArgumentParser(description="LeRobot 雙臂錄製壓力測試")
    parser.add_argument("camera_indices", nargs="+", type=int, help="相機索引 (例如: 4 6 8)")
    parser.add_argument("duration", type=int, default=60, help="測試時長(秒), 預設60")
    parser.add_argument("--preview", action="store_true", help="顯示預覽視窗")
    parser.add_argument("--robot-delay", type=float, default=5.0, 
                       help="每個機器人讀取延遲(ms), 預設5.0ms")
    
    args = parser.parse_args()
    
    stress_test(
        camera_indices=args.camera_indices,
        duration_seconds=args.duration,
        show_preview=args.preview,
        robot_read_delay_ms=args.robot_delay,
    )


if __name__ == "__main__":
    main()
