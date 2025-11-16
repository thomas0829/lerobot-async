#!/bin/bash

# SmolVLA Training Script - Resume from Checkpoint 7000
# Dataset: thomas0829/bimanual-so101-stacking-blocks-v2

source /home/duanj1/anaconda3/bin/activate lerobot
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export TOKENIZERS_PARALLELISM=false

# Resume training from checkpoint 7000 using saved config
python src/lerobot/scripts/train.py \
    --config_path=outputs/train/bimanual-smolvla-stacking/checkpoints/010000/pretrained_model/train_config.json \
    --resume=true \
    --steps=12000 \
    --save_freq=1000 \
    --eval_freq=1000 \
    --wandb.enable=true \
    --wandb.project=bimanual-smolvla-stacking
