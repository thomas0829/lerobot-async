#!/usr/bin/env python3
"""
模擬真實錄製場景的壓力測試
包含：相機讀取、機器人通訊、數據保存、視頻編碼
"""
import time
import sys
from pathlib import Path
import numpy as np
import threading
import queue
from collections import deque

sys.path.insert(0, str(Path(__file__).parent / "src"))

from lerobot.cameras.opencv.camera_opencv import OpenCVCamera
from lerobot.cameras.opencv.configuration_opencv import OpenCVCameraConfig, ColorMode

class SimulatedRobot:
    """模擬機器人通訊"""
    def __init__(self, port="/dev/ttyACM0", delay_ms=5):
        self.port = port
        self.delay_ms = delay_ms
        self.position = np.zeros(6)
    
    def read_position(self):
        """模擬讀取機器人位置 (約5ms延遲)"""
        time.sleep(self.delay_ms / 1000.0)
        # 模擬位置變化
        self.position += np.random.randn(6) * 0.01
        return self.position.copy()

class DataSaver:
    """模擬異步數據保存"""
    def __init__(self):
        self.queue = queue.Queue()
        self.running = False
        self.thread = None
        self.saved_count = 0
    
    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._save_worker, daemon=True)
        self.thread.start()
    
    def _save_worker(self):
        while self.running:
            try:
                data = self.queue.get(timeout=1.0)
                # 模擬保存parquet (約10ms)
                time.sleep(0.010)
                self.saved_count += 1
                self.queue.task_done()
            except queue.Empty:
                continue
    
    def save_frame(self, frame_data):
        self.queue.put(frame_data)
    
    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)

class FPSCounter:
    """FPS計數器"""
    def __init__(self, window_size=30):
        self.timestamps = deque(maxlen=window_size)
        self.frame_count = 0
    
    def tick(self):
        self.timestamps.append(time.time())
        self.frame_count += 1
    
    def get_fps(self):
        if len(self.timestamps) < 2:
            return 0.0
        duration = self.timestamps[-1] - self.timestamps[0]
        return (len(self.timestamps) - 1) / duration if duration > 0 else 0.0
    
    def get_avg_fps(self):
        if self.frame_count == 0:
            return 0.0
        if len(self.timestamps) == 0:
            return 0.0
        total_duration = time.time() - self.timestamps[0]
        return self.frame_count / total_duration if total_duration > 0 else 0.0

def stress_test_recording(camera_indices, duration_seconds=120, show_preview=False):
    """
    壓力測試：模擬真實錄製場景
    
    Args:
        camera_indices: 相機索引列表
        duration_seconds: 測試時長
        show_preview: 是否顯示預覽（會增加負載）
    """
    print("🔥 LeRobot 錄製壓力測試")
    print("=" * 80)
    print(f"測試配置:")
    print(f"  - 相機數量: {len(camera_indices)}")
    print(f"  - 測試時長: {duration_seconds}秒")
    print(f"  - 顯示預覽: {'是' if show_preview else '否'}")
    print("=" * 80)
    
    # 1. 初始化相機
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
            cameras.append((idx, camera))
            print(f"✅ 相機 {idx} 已連接")
        except Exception as e:
            print(f"❌ 相機 {idx} 連接失敗: {e}")
    
    if not cameras:
        print("沒有可用的相機")
        return
    
    # 2. 初始化模擬機器人
    robot = SimulatedRobot()
    print(f"✅ 模擬機器人已初始化")
    
    # 3. 初始化數據保存器
    saver = DataSaver()
    saver.start()
    print(f"✅ 數據保存器已啟動")
    
    # 4. 初始化FPS計數器
    fps_counters = {idx: FPSCounter() for idx, _ in cameras}
    
    # 5. 預覽視窗（如果需要）
    if show_preview:
        try:
            import cv2
            cv2.namedWindow("Preview", cv2.WINDOW_NORMAL)
            print(f"✅ 預覽視窗已創建")
        except ImportError:
            print(f"⚠️  無法導入cv2，跳過預覽")
            show_preview = False
    
    # 統計數據
    loop_times = []
    camera_read_times = []
    robot_read_times = []
    save_queue_sizes = []
    
    print("\n開始壓力測試...")
    print("-" * 80)
    cam_header = " | ".join([f"Cam{idx}" for idx, _ in cameras])
    print(f"{'時間':>6} | {'總FPS':>7} | {cam_header} | {'讀取':>6} | {'機器人':>7} | {'隊列':>5}")
    print("-" * 80)
    
    start_time = time.time()
    last_print_time = start_time
    
    try:
        while (time.time() - start_time) < duration_seconds:
            loop_start = time.perf_counter()
            
            # 6. 讀取所有相機
            cam_start = time.perf_counter()
            frames = {}
            for idx, camera in cameras:
                try:
                    frame = camera.async_read(timeout_ms=500)
                    frames[idx] = frame
                    fps_counters[idx].tick()
                except Exception as e:
                    print(f"\n⚠️  相機 {idx} 讀取失敗: {e}")
                    continue
            cam_time = (time.perf_counter() - cam_start) * 1000
            camera_read_times.append(cam_time)
            
            # 7. 讀取機器人狀態
            robot_start = time.perf_counter()
            robot_state = robot.read_position()
            robot_time = (time.perf_counter() - robot_start) * 1000
            robot_read_times.append(robot_time)
            
            # 8. 保存數據（異步）
            frame_data = {
                'frames': frames,
                'robot_state': robot_state,
                'timestamp': time.time()
            }
            saver.save_frame(frame_data)
            save_queue_sizes.append(saver.queue.qsize())
            
            # 9. 顯示預覽（如果需要）
            if show_preview and len(frames) > 0:
                # 只顯示第一個相機
                first_cam_idx = list(frames.keys())[0]
                preview_frame = frames[first_cam_idx]
                # 轉換回BGR給OpenCV
                preview_bgr = cv2.cvtColor(preview_frame, cv2.COLOR_RGB2BGR)
                cv2.imshow("Preview", preview_bgr)
                cv2.waitKey(1)
            
            loop_time = (time.perf_counter() - loop_start) * 1000
            loop_times.append(loop_time)
            
            # 10. 每秒統計一次
            current_time = time.time()
            if current_time - last_print_time >= 1.0:
                elapsed = current_time - start_time
                
                # 計算各相機FPS
                fps_str = " | ".join([f"{fps_counters[idx].get_fps():5.1f}" 
                                      for idx, _ in cameras])
                
                avg_fps = np.mean([fps_counters[idx].get_fps() for idx, _ in cameras])
                avg_loop = np.mean(loop_times[-30:]) if len(loop_times) >= 30 else np.mean(loop_times)
                avg_robot = np.mean(robot_read_times[-30:]) if len(robot_read_times) >= 30 else np.mean(robot_read_times)
                avg_queue = int(np.mean(save_queue_sizes[-30:])) if len(save_queue_sizes) >= 30 else 0
                
                print(f"{elapsed:6.0f}s | {avg_fps:7.2f} | {fps_str} | "
                      f"{avg_loop:5.1f}ms | {avg_robot:6.1f}ms | {avg_queue:5d}")
                
                last_print_time = current_time
            
            # 11. 控制循環頻率（目標30Hz）
            target_period = 1.0 / 30.0
            sleep_time = target_period - (time.perf_counter() - loop_start)
            if sleep_time > 0:
                time.sleep(sleep_time)
    
    except KeyboardInterrupt:
        print("\n\n測試被中斷")
    
    finally:
        # 清理
        print("\n" + "=" * 80)
        print("清理資源...")
        
        saver.stop()
        for idx, camera in cameras:
            camera.disconnect()
        
        if show_preview:
            try:
                cv2.destroyAllWindows()
            except:
                pass
    
    # 最終統計
    print("\n" + "=" * 80)
    print("📊 測試統計:")
    print("=" * 80)
    
    total_duration = time.time() - start_time
    print(f"\n測試時長: {total_duration:.2f}秒")
    
    # 相機FPS統計
    print(f"\n相機FPS:")
    for idx, _ in cameras:
        total_frames = fps_counters[idx].frame_count
        avg_fps = total_frames / total_duration
        current_fps = fps_counters[idx].get_fps()
        print(f"  相機 {idx}:")
        print(f"    - 總幀數: {total_frames}")
        print(f"    - 平均FPS: {avg_fps:.2f}")
        print(f"    - 最終FPS: {current_fps:.2f}")
    
    # 性能統計
    if loop_times:
        print(f"\n循環時間統計:")
        print(f"  平均: {np.mean(loop_times):.2f}ms")
        print(f"  最小: {np.min(loop_times):.2f}ms")
        print(f"  最大: {np.max(loop_times):.2f}ms")
        print(f"  標準差: {np.std(loop_times):.2f}ms")
        
        # 性能趨勢
        if len(loop_times) > 100:
            first_50 = np.mean(loop_times[:50])
            last_50 = np.mean(loop_times[-50:])
            change = ((last_50 - first_50) / first_50) * 100
            
            print(f"\n  性能趨勢:")
            print(f"    前50次循環: {first_50:.2f}ms")
            print(f"    後50次循環: {last_50:.2f}ms")
            print(f"    變化: {change:+.1f}%")
            
            if abs(change) < 5:
                print(f"    ✅ 性能保持穩定")
            elif change > 5:
                print(f"    ⚠️  性能有輕微下降")
            else:
                print(f"    ✅ 性能有改善")
    
    # 相機讀取時間
    if camera_read_times:
        print(f"\n相機讀取時間:")
        print(f"  平均: {np.mean(camera_read_times):.2f}ms")
        print(f"  最大: {np.max(camera_read_times):.2f}ms")
    
    # 機器人讀取時間
    if robot_read_times:
        print(f"\n機器人讀取時間:")
        print(f"  平均: {np.mean(robot_read_times):.2f}ms")
        print(f"  最大: {np.max(robot_read_times):.2f}ms")
    
    # 保存隊列
    if save_queue_sizes:
        print(f"\n保存隊列:")
        print(f"  平均大小: {np.mean(save_queue_sizes):.1f}")
        print(f"  最大大小: {np.max(save_queue_sizes)}")
        print(f"  已保存: {saver.saved_count} 幀")
        
        if np.max(save_queue_sizes) > 100:
            print(f"  ⚠️  警告: 隊列曾經很大，保存速度可能跟不上")
        else:
            print(f"  ✅ 保存速度正常")
    
    # 最終評估
    print("\n" + "=" * 80)
    print("🎯 最終評估:")
    
    all_fps_ok = all(fps_counters[idx].get_avg_fps() >= 28.0 for idx, _ in cameras)
    loop_time_ok = np.mean(loop_times) < 40.0  # 小於40ms = 能維持25fps以上
    queue_ok = np.max(save_queue_sizes) < 100
    
    if all_fps_ok and loop_time_ok and queue_ok:
        print("✅ 系統性能優秀！可以穩定錄製數據")
    elif all_fps_ok and loop_time_ok:
        print("✅ 系統性能良好，可以錄製數據")
        if not queue_ok:
            print("⚠️  保存隊列偶爾較大，建議監控磁碟寫入速度")
    else:
        print("⚠️  系統性能有待改善")
        if not all_fps_ok:
            print("  - 相機FPS偏低，檢查USB頻寬或相機設置")
        if not loop_time_ok:
            print("  - 循環時間過長，考慮降低解析度或減少相機數量")
        if not queue_ok:
            print("  - 保存速度跟不上，檢查磁碟IO性能")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法:")
        print("  python test_recording_stress.py <cam1> [cam2] [cam3] ... [duration] [--preview]")
        print("\n例如:")
        print("  python test_recording_stress.py 4 6 8 120")
        print("  python test_recording_stress.py 4 6 8 120 --preview")
        sys.exit(1)
    
    # 解析參數
    show_preview = "--preview" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--preview"]
    
    try:
        # 最後一個參數可能是duration
        if len(args) > 1 and args[-1].isdigit() and int(args[-1]) > 10:
            duration = int(args[-1])
            camera_indices = [int(x) for x in args[:-1]]
        else:
            duration = 120
            camera_indices = [int(x) for x in args]
    except ValueError:
        print("❌ 參數錯誤：相機索引必須是整數")
        sys.exit(1)
    
    stress_test_recording(camera_indices, duration, show_preview)
