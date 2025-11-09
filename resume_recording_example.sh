#!/bin/bash

# Resume Recording Example for Bimanual SO100
# 双臂 SO100 Resume 记录示例脚本
#
# 用途: 展示如何使用 resume 功能继续记录数据集
# Usage: ./resume_recording_example.sh

set -e  # 遇到错误时退出

echo "=================================="
echo "Resume Recording Example"
echo "=================================="
echo ""

# 配置变量
REPO_ID="thomas0829/bimanual_so100_stack_blocks"
TASK="Stack blocks."
TARGET_EPISODES=50
EPISODE_TIME=120

# 相机配置 (需要根据你的实际设备调整)
CAMERA_CONFIG='{
  left: {type: opencv, index_or_path: 9, width: 640, height: 480, fps: 30},
  right: {type: opencv, index_or_path: 1, width: 640, height: 480, fps: 30},
  top: {type: opencv, index_or_path: 7, width: 1280, height: 720, fps: 30}
}'

# 机器人端口 (需要根据你的实际设备调整)
FOLLOWER_LEFT_PORT="/dev/ttyACM3"
FOLLOWER_RIGHT_PORT="/dev/ttyACM1"
LEADER_LEFT_PORT="/dev/ttyACM0"
LEADER_RIGHT_PORT="/dev/ttyACM2"

echo "Dataset: $REPO_ID"
echo "Task: $TASK"
echo "Target Episodes: $TARGET_EPISODES"
echo ""

# 检查数据集是否存在
DATASET_PATH="$HOME/.cache/huggingface/lerobot/$REPO_ID"

if [ -d "$DATASET_PATH" ]; then
    echo "✅ Found existing dataset at: $DATASET_PATH"
    
    # 尝试读取当前 episode 数量
    if [ -f "$DATASET_PATH/meta/info.json" ]; then
        CURRENT_EPISODES=$(python3 -c "import json; print(json.load(open('$DATASET_PATH/meta/info.json'))['total_episodes'])" 2>/dev/null || echo "unknown")
        echo "📊 Current episodes: $CURRENT_EPISODES"
        
        if [ "$CURRENT_EPISODES" != "unknown" ]; then
            REMAINING=$((TARGET_EPISODES - CURRENT_EPISODES))
            if [ $REMAINING -gt 0 ]; then
                echo "📹 Will record $REMAINING more episodes"
                RESUME_MODE="true"
            else
                echo "⚠️  Dataset already has $CURRENT_EPISODES episodes (target: $TARGET_EPISODES)"
                echo "   Consider increasing --dataset.num_episodes"
                exit 0
            fi
        else
            echo "⚠️  Could not read episode count"
            RESUME_MODE="true"
        fi
    else
        echo "⚠️  info.json not found, will try to resume anyway"
        RESUME_MODE="true"
    fi
    echo ""
else
    echo "ℹ️  Dataset not found, will create new one"
    RESUME_MODE="false"
    echo ""
fi

# 构建命令
CMD="lerobot-record \
  --robot.type=bi_so100_follower \
  --robot.left_arm_port=$FOLLOWER_LEFT_PORT \
  --robot.right_arm_port=$FOLLOWER_RIGHT_PORT \
  --robot.id=bimanual_follower \
  --robot.cameras='$CAMERA_CONFIG' \
  --teleop.type=bi_so100_leader \
  --teleop.left_arm_port=$LEADER_LEFT_PORT \
  --teleop.right_arm_port=$LEADER_RIGHT_PORT \
  --teleop.id=bimanual_leader \
  --display_data=true \
  --dataset.repo_id=$REPO_ID \
  --dataset.num_episodes=$TARGET_EPISODES \
  --dataset.single_task=\"$TASK\" \
  --dataset.episode_time_s=$EPISODE_TIME"

# 添加 resume 参数（如果需要）
if [ "$RESUME_MODE" = "true" ]; then
    CMD="$CMD \
  --dataset.resume=true"
    echo "🔄 Mode: RESUME (继续记录)"
else
    echo "🆕 Mode: CREATE (创建新数据集)"
fi

echo ""
echo "=================================="
echo "Command to execute:"
echo "=================================="
echo "$CMD"
echo ""

# 询问是否执行
read -p "Execute this command? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "=================================="
    echo "Starting recording..."
    echo "=================================="
    echo ""
    
    # 执行命令
    eval $CMD
    
    echo ""
    echo "=================================="
    echo "Recording completed!"
    echo "=================================="
else
    echo ""
    echo "Command not executed. You can copy and run it manually."
fi

echo ""
echo "💡 Tips:"
echo "  - To resume again later, just run this script again"
echo "  - To record more episodes, increase TARGET_EPISODES in this script"
echo "  - Check dataset at: $DATASET_PATH"
