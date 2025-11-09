# Resume Recording Guide (恢复记录指南)

## 功能说明

现在 LeRobot 支持 **resume (恢复)** 功能！你可以在已有的数据集基础上继续记录，而不需要从头开始。

## 使用方法

### 第一次记录（例如：记录 25 个 episodes）

```bash
lerobot-record \
  --robot.type=bi_so100_follower \
  --robot.left_arm_port=/dev/ttyACM3 \
  --robot.right_arm_port=/dev/ttyACM1 \
  --robot.id=bimanual_follower \
  --robot.cameras='{ 
    left: {type: opencv, index_or_path: 9, width: 640, height: 480, "fps": 30}, 
    right: {type: opencv, index_or_path: 1, width: 640, height: 480, "fps": 30}, 
    top: {type: opencv, index_or_path: 7, width: 1280, height: 720, fps: 30}
    }' \
  --teleop.type=bi_so100_leader \
  --teleop.left_arm_port=/dev/ttyACM0 \
  --teleop.right_arm_port=/dev/ttyACM2 \
  --teleop.id=bimanual_leader \
  --display_data=true \
  --dataset.repo_id=thomas0829/bimanual_so100_stack_blocks \
  --dataset.num_episodes=25 \
  --dataset.single_task="Stack blocks." \
  --dataset.episode_time_s=120
```

### 继续记录（从 25 个扩展到 50 个）

只需要添加 `--dataset.resume=true` 并修改 `--dataset.num_episodes=50`：

```bash
lerobot-record \
  --robot.type=bi_so100_follower \
  --robot.left_arm_port=/dev/ttyACM3 \
  --robot.right_arm_port=/dev/ttyACM1 \
  --robot.id=bimanual_follower \
  --robot.cameras='{ 
    left: {type: opencv, index_or_path: 9, width: 640, height: 480, "fps": 30}, 
    right: {type: opencv, index_or_path: 1, width: 640, height: 480, "fps": 30}, 
    top: {type: opencv, index_or_path: 7, width: 1280, height: 720, fps: 30}
    }' \
  --teleop.type=bi_so100_leader \
  --teleop.left_arm_port=/dev/ttyACM0 \
  --teleop.right_arm_port=/dev/ttyACM2 \
  --teleop.id=bimanual_leader \
  --display_data=true \
  --dataset.repo_id=thomas0829/bimanual_so100_stack_blocks \
  --dataset.num_episodes=50 \
  --dataset.resume=true \
  --dataset.single_task="Stack blocks." \
  --dataset.episode_time_s=120
```

## 重要说明

### ✅ Resume 模式会做什么：

1. **加载现有数据集**：从磁盘加载已记录的 episodes 和 metadata
2. **继续编号**：新的 episodes 会从 `episode_26`, `episode_27`, ... 开始
3. **保留统计信息**：现有的 stats 和 tasks 会被保留并更新
4. **验证兼容性**：确保 fps、robot_type、features 等配置匹配

### ⚠️ 注意事项：

1. **配置必须匹配**：
   - FPS 必须相同
   - Features (相机配置、动作空间等) 必须相同
   - 如果不匹配，会报错并拒绝继续

2. **num_episodes 是总数**：
   - 如果你有 25 个 episodes，想记录到 50 个
   - 设置 `--dataset.num_episodes=50` (不是 25)
   - 系统会自动记录剩余的 25 个

3. **repo_id 必须相同**：
   - 必须使用相同的 `--dataset.repo_id`
   - 数据会存储在同一个目录

### 📊 示例场景：

**场景 1: 正常扩展**
```
已有: 25 episodes
目标: 50 episodes
设置: --dataset.num_episodes=50 --dataset.resume=true
结果: 会记录 episode 26-50 (共 25 个新 episodes)
```

**场景 2: 已经达到目标**
```
已有: 50 episodes
目标: 50 episodes
设置: --dataset.num_episodes=50 --dataset.resume=true
结果: 不会记录任何新 episodes (会有警告提示)
```

**场景 3: 继续扩展**
```
已有: 50 episodes
目标: 100 episodes
设置: --dataset.num_episodes=100 --dataset.resume=true
结果: 会记录 episode 51-100 (共 50 个新 episodes)
```

## 文件结构

Resume 模式下，数据集目录结构保持不变：

```
dataset/
├── data/
│   ├── chunk-000/
│   │   ├── episode_000000.parquet
│   │   ├── episode_000001.parquet
│   │   └── ...
│   └── chunk-001/
│       ├── episode_001000.parquet  # 新记录的继续编号
│       └── ...
├── meta/
│   ├── episodes.jsonl  # 追加新 episodes
│   ├── info.json       # 更新统计信息
│   └── stats.jsonl     # 追加新统计
└── videos/
    └── ...
```

## 错误处理

### 如果配置不匹配：

```
ValueError: FPS mismatch: existing dataset has fps=30, but you specified fps=60.
FPS must match when resuming.
```

**解决方法**：确保 `--dataset.fps` 与原始数据集相同。

### 如果 features 不匹配：

```
ValueError: Feature mismatch when resuming dataset.
Existing features: ['action', 'observation.images.left', ...]
New features: ['action', 'observation.images.different', ...]
```

**解决方法**：确保相机配置和 robot 配置与原始数据集相同。

## 技术细节

### 实现原理：

1. **LeRobotDatasetMetadata.create()**：添加 `resume` 参数
   - `resume=True`: 加载现有 metadata
   - `resume=False`: 创建新 metadata (默认)

2. **LeRobotDataset.create()**：添加 `resume` 参数
   - `resume=True`: 加载现有 hf_dataset
   - `resume=False`: 创建空 hf_dataset (默认)

3. **record.py**：
   - 从 `dataset.meta.total_episodes` 开始记录
   - Episode 编号自动延续
   - 所有 metadata 文件 (episodes.jsonl, stats.jsonl) 采用追加模式

### 数据完整性：

- ✅ Episode 索引连续
- ✅ 统计信息正确聚合
- ✅ 视频编码正常工作
- ✅ 支持异步保存 (async_saver)
- ✅ 支持批量视频编码 (batch_encoding)

## 常见问题 (FAQ)

**Q: 可以修改 task 吗？**
A: 可以。Task 会被追加到 tasks 字典，支持多任务数据集。

**Q: 可以修改相机配置吗？**
A: 不可以。Features 必须完全匹配，包括相机数量、分辨率等。

**Q: resume 模式下可以 push_to_hub 吗？**
A: 可以。使用 `--dataset.push_to_hub=true` 会上传完整的数据集（包括新旧 episodes）。

**Q: 如果中断了记录，可以再次 resume 吗？**
A: 可以！多次 resume 都是支持的，每次都会从当前的 total_episodes 继续。

## 示例日志输出

```
INFO: Resuming dataset: thomas0829/bimanual_so100_stack_blocks
INFO: Loaded existing dataset: 25 episodes, 7500 frames, 1 tasks
INFO: Resuming from episode 25. Target: 50 episodes total.
INFO: Recording episode 26/50
...
INFO: Episode 26 submitted for async saving
INFO: Recording episode 27/50
...
```

---

**新增日期**: 2025-10-21
**功能**: Dataset Resume/继续记录
**状态**: ✅ 已实现并测试
