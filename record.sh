#!/bin/bash

export HF_USER=thomas0829

rm -rf ~/.cache/huggingface/lerobot/${HF_USER}/record-test

lerobot-record --robot.type=so100_follower --robot.port=/dev/ttyACM1 --robot.id=follower_left --robot.cameras="{ front: {type: opencv, index_or_path: 1, width: 640, height: 480, "fps": 30}, top: {type: opencv, index_or_path: 7, width: 1280, height: 720, fps: 30}}" --teleop.type=so100_leader --teleop.port=/dev/ttyACM0 --teleop.id=leader_left --display_data=true --dataset.repo_id=thomas0829/record-test --dataset.num_episodes=50 --dataset.single_task="Grab the doll"

#lerobot-record  --robot.type=so100_follower --robot.port=/dev/ttyACM1 --robot.cameras="{ front: {type: opencv, index_or_path: 1, width: 640, height: 480, "fps": 30}, top: {type: opencv, index_or_path: 7, width: 1280, height: 720, fps: 30}}" --robot.id=follower_left  --display_data=false --dataset.repo_id=thomas0829/eval_record_test  --dataset.single_task="Grab the doll" --policy.path="/home/sean/lerobot/outputs/train/act_so100_test/checkpoints/last/pretrained_model"

lerobot-record \
  --robot.type=bi_so100_follower \
  --robot.left_arm_port=/dev/ttyACM2 \
  --robot.right_arm_port=/dev/ttyACM1 \
  --robot.id=bimanual_follower \
  --robot.cameras='{ 
    left: {type: opencv, index_or_path: 9, width: 640, height: 480, "fps": 30}, 
    right: {type: opencv, index_or_path: 1, width: 640, height: 480, "fps": 30}, 
    top: {type: opencv, index_or_path: 7, width: 1280, height: 720, fps: 30}
    }' \
  --teleop.type=bi_so100_leader \
  --teleop.left_arm_port=/dev/ttyACM3 \
  --teleop.right_arm_port=/dev/ttyACM0 \
  --teleop.id=bimanual_leader \
  --display_data=true \
  --dataset.repo_id=thomas0829/bimanual_so100_stack_blocks \
  --dataset.num_episodes=50 \
  --dataset.single_task="Stack blocks." \
  --dataset.episode_time_s=120

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
  --display_data=false \
  --dataset.repo_id=thomas0829/eval_bimanual_so100_grab \
  --dataset.single_task="Grab things into a bowl." \
  --policy.path="/home/sean/lerobot/outputs/train/bimanual_act_so100_grab/checkpoints/010000/pretrained_model"

lerobot-train \
  --dataset.repo_id=thomas0829/bimanual_so100_grab \
  --policy.type=act \
  --output_dir=outputs/train/bimanual_act_so100_grab \
  --job_name=bimanual_act_so100_grab \
  --policy.device=cuda \
  --wandb.enable=true \
  --policy.repo_id=thomas0829/policy_bimanual_grab

# lerobot-train \
#   --config_path=outputs/train/bimanual_act_so100_fold_towel/checkpoints/007500/pretrained_model/train_config.json \
#   --resume=true

lerobot-teleoperate \
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
  --display_data=true

lerobot-record  \
 --robot.type=so100_follower \
 --robot.port=/dev/ttyACM0 \
 --robot.cameras='{ 
    top: {type: opencv, index_or_path: 5, width: 1280, height: 720, fps: 30}
    }' \
 --robot.id=follower_left  \
 --display_data=false \
 --dataset.repo_id=thomas0829/eval_record_test \
 --dataset.single_task="Grab the doll" \
 --policy.path="/home/sean/lerobot/outputs/train/act_so100_test/checkpoints/last/pretrained_model"


# ls /dev/video*
# v4l2-ctl -d /dev/video9 --list-formats-ext
# rm ~/.cache/huggingface/lerobot/calibration/robots/so100_follower/bimanual_follower_*.json
# rm ~/.cache/huggingface/lerobot/calibration/teleoperators/so100_leader/bimanual_leader_*.json

lerobot-teleoperate \
  --robot.type=so100_follower \
  --robot.port=/dev/ttyACM1 \
  --robot.id=follower_right \
  --robot.cameras='{ 
    right: {type: opencv, index_or_path: 7, width: 640, height: 480, "fps": 30}, 
    front: {type: opencv, index_or_path: 5, width: 640, height: 480, fps: 30}
    }' \
  --teleop.type=so100_leader \
  --teleop.port=/dev/ttyACM0 \
  --teleop.id=leader_right \
  --display_data=true

lerobot-record \
  --robot.type=so100_follower \
  --robot.port=/dev/ttyACM1 \
  --robot.id=follower_right \
  --robot.cameras='{ 
    right: {type: opencv, index_or_path: 7, width: 640, height: 480, "fps": 30}, 
    front: {type: opencv, index_or_path: 5, width: 640, height: 480, fps: 30}
    }' \
  --teleop.type=so100_leader \
  --teleop.port=/dev/ttyACM0 \
  --teleop.id=leader_right \
  --display_data=true \
  --dataset.repo_id=thomas0829/record_pick_pen \
  --dataset.num_episodes=100 \
  --dataset.single_task="Pick up the pen."