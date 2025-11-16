#!/usr/bin/env python3
"""
監控系統資源使用情況 - 檢測記憶體洩漏和性能下降
"""
import psutil
import time
import os
from pathlib import Path

def monitor_system_resources(duration_seconds=300, interval_seconds=5):
    """
    監控系統資源使用情況
    
    Args:
        duration_seconds: 監控總時長（秒）
        interval_seconds: 採樣間隔（秒）
    """
    print(f"開始監控系統資源，總時長 {duration_seconds}秒，每 {interval_seconds}秒採樣一次")
    print("=" * 100)
    print(f"{'時間(s)':>8} | {'CPU%':>6} | {'記憶體%':>7} | {'記憶體MB':>9} | {'可用MB':>8} | "
          f"{'Swap%':>6} | {'磁碟讀MB/s':>11} | {'磁碟寫MB/s':>11}")
    print("-" * 100)
    
    process = psutil.Process(os.getpid())
    parent_process = psutil.Process(os.getppid())
    
    # 記錄初始磁碟IO
    disk_io_start = psutil.disk_io_counters()
    
    data_points = []
    start_time = time.time()
    
    try:
        for i in range(int(duration_seconds / interval_seconds)):
            current_time = time.time() - start_time
            
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 記憶體使用率
            mem = psutil.virtual_memory()
            mem_percent = mem.percent
            mem_used_mb = mem.used / 1024 / 1024
            mem_available_mb = mem.available / 1024 / 1024
            
            # Swap使用率
            swap = psutil.swap_memory()
            swap_percent = swap.percent
            
            # 磁碟IO
            disk_io_end = psutil.disk_io_counters()
            disk_read_mb = (disk_io_end.read_bytes - disk_io_start.read_bytes) / 1024 / 1024 / interval_seconds
            disk_write_mb = (disk_io_end.write_bytes - disk_io_start.write_bytes) / 1024 / 1024 / interval_seconds
            disk_io_start = disk_io_end
            
            # 記錄數據
            data_point = {
                'time': current_time,
                'cpu': cpu_percent,
                'mem_percent': mem_percent,
                'mem_mb': mem_used_mb,
                'available_mb': mem_available_mb,
                'swap': swap_percent,
                'disk_read': disk_read_mb,
                'disk_write': disk_write_mb
            }
            data_points.append(data_point)
            
            # 打印
            print(f"{current_time:8.1f} | {cpu_percent:6.1f} | {mem_percent:7.1f} | "
                  f"{mem_used_mb:9.1f} | {mem_available_mb:8.1f} | {swap_percent:6.1f} | "
                  f"{disk_read_mb:11.2f} | {disk_write_mb:11.2f}")
            
            time.sleep(interval_seconds)
    
    except KeyboardInterrupt:
        print("\n監控被中斷")
    
    print("=" * 100)
    
    # 統計分析
    if len(data_points) > 1:
        print("\n📊 統計分析:")
        
        import numpy as np
        
        cpu_values = [d['cpu'] for d in data_points]
        mem_values = [d['mem_mb'] for d in data_points]
        
        print(f"\nCPU使用率:")
        print(f"  平均: {np.mean(cpu_values):.1f}%")
        print(f"  最大: {np.max(cpu_values):.1f}%")
        print(f"  最小: {np.min(cpu_values):.1f}%")
        
        print(f"\n記憶體使用:")
        print(f"  開始: {mem_values[0]:.1f} MB")
        print(f"  結束: {mem_values[-1]:.1f} MB")
        print(f"  增長: {mem_values[-1] - mem_values[0]:.1f} MB")
        print(f"  最大: {np.max(mem_values):.1f} MB")
        
        # 檢測記憶體洩漏
        if len(mem_values) >= 3:
            # 簡單線性回歸檢測趨勢
            x = np.array(range(len(mem_values)))
            y = np.array(mem_values)
            slope = np.polyfit(x, y, 1)[0]
            
            if slope > 1:  # 每次採樣增長超過1MB
                print(f"\n⚠️  警告: 檢測到記憶體持續增長，速率: {slope:.2f} MB/採樣")
                print(f"   預估每分鐘增長: {slope * 60 / interval_seconds:.2f} MB")
            else:
                print(f"\n✅ 記憶體使用穩定")

def check_lerobot_processes():
    """檢查LeRobot相關進程的資源使用"""
    print("\n🔍 檢查LeRobot相關進程:")
    print("=" * 100)
    
    found_processes = []
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_percent']):
        try:
            cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
            if 'lerobot' in cmdline.lower() or 'python' in proc.info['name'].lower():
                if any(keyword in cmdline for keyword in ['record', 'lerobot-record', 'opencv', 'camera']):
                    found_processes.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'cmdline': cmdline[:80] + '...' if len(cmdline) > 80 else cmdline,
                        'cpu': proc.info['cpu_percent'],
                        'mem': proc.info['memory_percent']
                    })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    if found_processes:
        print(f"{'PID':>7} | {'名稱':>15} | {'CPU%':>6} | {'記憶體%':>7} | 命令")
        print("-" * 100)
        for p in found_processes:
            print(f"{p['pid']:7d} | {p['name']:>15} | {p['cpu']:6.1f} | {p['mem']:7.2f} | {p['cmdline']}")
    else:
        print("未找到正在運行的LeRobot進程")

def check_camera_threads():
    """檢查當前進程的線程數"""
    print("\n🧵 線程檢查:")
    print("=" * 50)
    
    process = psutil.Process()
    num_threads = process.num_threads()
    print(f"當前進程線程數: {num_threads}")
    
    try:
        threads = process.threads()
        print(f"線程詳情: {len(threads)} 個線程")
        for i, thread in enumerate(threads[:10]):  # 只顯示前10個
            print(f"  線程 {i}: id={thread.id}, user_time={thread.user_time:.2f}s, system_time={thread.system_time:.2f}s")
    except AttributeError:
        print("無法獲取線程詳情（需要更高權限）")

if __name__ == "__main__":
    import sys
    
    print("🔧 LeRobot 系統資源監控工具\n")
    
    # 檢查進程
    check_lerobot_processes()
    
    # 檢查線程
    check_camera_threads()
    
    # 如果提供參數，則進行持續監控
    if len(sys.argv) > 1:
        try:
            duration = int(sys.argv[1])
        except ValueError:
            duration = 300
    else:
        print("\n提示: 運行 'python monitor_system.py <秒數>' 進行持續監控")
        print("例如: python monitor_system.py 300  (監控5分鐘)")
        sys.exit(0)
    
    interval = 5 if len(sys.argv) <= 2 else int(sys.argv[2])
    
    print(f"\n開始持續監控 {duration} 秒...")
    monitor_system_resources(duration, interval)
