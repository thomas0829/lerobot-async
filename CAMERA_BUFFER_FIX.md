# USB相機Buffer積壓問題修復

## 🔴 問題描述

在長時間錄製數據時（50個episodes），出現以下症狀：

1. **預覽畫面越來越卡** - 畫面延遲增加
2. **機器人抖動變大** - 控制響應變慢
3. **有效錄製時間縮短** - 後期episodes時長明顯減少（從37秒降到10秒）

## 🔍 問題根源

### OpenCV VideoCapture的Buffer機制

OpenCV的`VideoCapture`內部維護了一個幀buffer（通常5-10幀）：

```
相機硬體 → [Buffer: Frame1, Frame2, ..., Frame10] → read() 讀取
```

### 問題發生過程

1. **初期**：系統處理速度 = 相機速度，buffer清空
2. **中期**：系統稍微變慢，buffer開始積壓
3. **後期**：buffer滿了，`read()`讀到的是**幾百毫秒前的舊幀**

```
時間點:  0ms    100ms   200ms   300ms   400ms
相機:    Frame1  Frame4  Frame7  Frame10 Frame13
Buffer:  [1]→   [1,2,3,4]→ [2,3,4,5,6,7]→ buffer滿
read():  Frame1  Frame1  Frame2  Frame3  ← 延遲越來越大！
```

### 為什麼會越來越慢？

1. **多相機競爭** - 3個相機同時讀取，USB頻寬壓力大
2. **背景編碼** - 視頻編碼佔用CPU
3. **記憶體壓力** - 隨著episodes增加，記憶體使用增加
4. **Buffer積壓惡性循環** - 延遲導致控制變慢，錄製效率下降

## ✅ 解決方案

### 修改：清空Buffer機制

在`_read_loop()`中，每次讀取前先用`grab()`清空舊幀：

```python
def _read_loop(self):
    while not self.stop_event.is_set():
        try:
            # 清空buffer，確保讀到最新幀
            for _ in range(5):
                self.videocapture.grab()  # 只抓取不取回，速度快
            
            # 現在read()會得到最新的幀
            color_image = self.read()
            
            with self.frame_lock:
                self.latest_frame = color_image
            self.new_frame_event.set()
```

### 原理

- `grab()`: 只從buffer中移除幀，不取回數據（快）
- 連續grab 5次，清空積壓的舊幀
- 最後的`read()`讀到最新的幀

## 🧪 驗證方法

### 1. 使用測試腳本

```bash
# 測試單個相機，60秒
python test_camera_buffer.py 4 60

# 測試多個相機，30秒  
python test_camera_buffer.py 4 6 8 30
```

### 2. 觀察指標

測試時注意：
- **FPS穩定性** - 應保持在30fps附近
- **讀取時間** - 前50幀 vs 後50幀應該相近
- **性能趨勢** - 不應該越來越慢

預期結果：
```
前50幀平均讀取時間: 15.5ms
後50幀平均讀取時間: 16.2ms
變化: +4.5%  ← 應該在±10%以內
✅ 性能保持穩定
```

### 3. 實際錄製測試

```bash
# 錄製完整的50個episodes
lerobot-record \
  --robot.type=bi_so100_follower \
  ...
  --dataset.num_episodes=50
```

觀察：
- 預覽畫面是否保持流暢
- 機器人控制是否穩定
- 後期episodes時長是否正常

## 📊 預期改善

修復後應該看到：

### Before (有問題時)
- Episode 0: 81秒 ✅
- Episode 25: 15秒 ⚠️
- Episode 47: 8秒 ❌
- 預覽: 越來越卡 ❌
- 機器人: 抖動增加 ❌

### After (修復後)
- Episode 0: 20秒 ✅
- Episode 25: 21秒 ✅
- Episode 47: 19秒 ✅
- 預覽: 始終流暢 ✅
- 機器人: 穩定控制 ✅

## 🔧 其他優化建議

如果問題仍然存在，可以考慮：

### 1. 降低相機解析度
```python
# 從1920x1080降到1280x720
top: {type: opencv, index_or_path: 4, width: 1280, height: 720, fps: 30}
```

### 2. 減少相機數量（測試用）
先用2個相機測試，確認是否穩定

### 3. 調整編碼參數
```python
video_encoding_batch_size: 5  # 每5個episode才編碼一次
```

### 4. 增加USB帶寬
- 使用USB 3.0接口
- 不同相機接到不同的USB控制器
- 檢查`lsusb -t`看USB拓撲

### 5. 監控系統資源
```bash
python monitor_system.py 300  # 監控5分鐘
```

觀察CPU、記憶體、磁碟IO是否有瓶頸

## 📝 技術細節

### grab() vs read()

- `read()` = `grab()` + `retrieve()`
- `grab()`: 從driver buffer取出幀，但不decode
- `retrieve()`: 實際decode成numpy array

清空buffer時只需要`grab()`，省略decode步驟，更快。

### Buffer大小

不同系統的buffer大小不同：
- Linux V4L2: 通常4-5幀
- Windows DirectShow: 可能10+幀
- macOS AVFoundation: 取決於設置

我們flush 5幀是一個保守的值，在大多數系統上足夠。

## 🔗 相關文件

- 修改的檔案: `src/lerobot/cameras/opencv/camera_opencv.py`
- 測試腳本: `test_camera_buffer.py`
- 系統監控: `monitor_system.py`
- 數據分析: `analyze_dataset.py`, `check_actual_fps_v2.py`
