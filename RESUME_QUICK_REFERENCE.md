# Resume Recording Quick Reference
# Resume 记录快速参考

## 🎯 一句话总结

添加 `--dataset.resume=true` 参数即可在现有数据集上继续记录！

## ⚡ 快速开始

### 你的原命令（记录 25 个）：
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

### 继续到 50 个（只改 2 行）：
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
  --dataset.num_episodes=50 \            # ← 改这里: 25 → 50
  --dataset.resume=true \                # ← 加这行！
  --dataset.single_task="Stack blocks." \
  --dataset.episode_time_s=120
```

## ✨ 核心要点

1. **添加**: `--dataset.resume=true`
2. **修改**: `--dataset.num_episodes=50` (目标总数，不是增量)
3. **保持**: 其他所有参数必须与原来相同

## 📊 工作原理

```
已有 25 episodes → resume=true + num_episodes=50 → 记录 25 个新的 → 总共 50 episodes
  ⬇️                                                    ⬇️
episode_000000.parquet                       episode_000025.parquet
episode_000001.parquet                       episode_000026.parquet
...                                          ...
episode_000024.parquet                       episode_000049.parquet
```

## ⚠️ 注意事项

| 配置项 | 要求 | 说明 |
|--------|------|------|
| `--dataset.repo_id` | 必须相同 | 使用相同的数据集名称 |
| `--dataset.fps` | 必须相同 | 帧率必须匹配 |
| `--robot.cameras` | 必须相同 | 相机配置必须完全一致 |
| `--dataset.num_episodes` | 必须 ≥ 已有数量 | 这是目标总数，不是增量 |

## 🔍 常见错误

### ❌ 错误 1: FPS 不匹配
```
ValueError: FPS mismatch: existing dataset has fps=30, but you specified fps=60.
```
**解决**: 保持 `--dataset.fps=30`

### ❌ 错误 2: 相机配置不同
```
ValueError: Feature mismatch when resuming dataset.
```
**解决**: 使用完全相同的 `--robot.cameras` 配置

### ❌ 错误 3: num_episodes 太小
```
WARNING: Dataset already has 25 episodes, which is >= target of 20.
```
**解决**: 设置 `--dataset.num_episodes` ≥ 25（例如 50, 100）

## ✅ 检查清单

在运行 resume 之前检查：

- [ ] 原数据集路径存在
- [ ] `--dataset.resume=true` 已添加
- [ ] `--dataset.num_episodes` 是目标总数（≥ 已有数量）
- [ ] `--dataset.repo_id` 与原来相同
- [ ] `--robot.type` 与原来相同
- [ ] `--robot.cameras` 配置与原来相同
- [ ] `--dataset.fps` 与原来相同

## 📚 更多信息

- 详细指南: `RESUME_RECORDING_GUIDE.md`
- 技术总结: `RESUME_IMPLEMENTATION_SUMMARY.md`
- 测试脚本: `test_resume_functionality.py`

## 💡 实用技巧

### 查看现有 episode 数量
```bash
# 方法 1: 查看 info.json
cat ~/.cache/huggingface/lerobot/thomas0829/bimanual_so100_stack_blocks/meta/info.json | grep total_episodes

# 方法 2: 数 parquet 文件
ls ~/.cache/huggingface/lerobot/thomas0829/bimanual_so100_stack_blocks/data/*/*.parquet | wc -l
```

### 多次 resume
```bash
# 第一次: 0 → 25
lerobot-record --dataset.num_episodes=25 ...

# 第二次: 25 → 50
lerobot-record --dataset.num_episodes=50 --dataset.resume=true ...

# 第三次: 50 → 100
lerobot-record --dataset.num_episodes=100 --dataset.resume=true ...
```

---

**快速上手**: 复制你的原命令 → 改 `num_episodes` → 加 `--dataset.resume=true` → 运行！
