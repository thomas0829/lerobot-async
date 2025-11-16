#!/bin/bash

# Diffusion Policy Training Script
# Dataset: thomas0829/bimanual-so101-stacking-blocks

source /home/duanj1/anaconda3/bin/activate lerobot
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

# Train Diffusion Policy
python -m lerobot.scripts.train \
    --dataset.repo_id=thomas0829/bimanual-so101-stacking-blocks-v2 \
    --policy.type=diffusion \
    --output_dir=outputs/train/bimanual-diffusion-stacking-blocks \
    --policy.repo_id=thomas0829/policy-bimanual-diffusion-stacking \
    --wandb.enable=true \
    --wandb.project=diffusion-bimanual-stacking \
    --num_workers=4 \
    --batch_size=16 \
    --steps=10000 \
    --eval_freq=1000 \
    --save_freq=1000 \
    --log_freq=100
