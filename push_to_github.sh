#!/bin/bash

# 推送到 GitHub 的快速脚本
# 使用方法: ./push_to_github.sh YOUR_GITHUB_USERNAME

# 检查是否提供了用户名
if [ -z "$1" ]; then
    echo "错误: 请提供您的 GitHub 用户名"
    echo "使用方法: ./push_to_github.sh YOUR_GITHUB_USERNAME"
    echo "例如: ./push_to_github.sh sean"
    exit 1
fi

GITHUB_USERNAME=$1
REPO_NAME="lerobot-async"  # 您可以修改这个仓库名称

echo "========================================="
echo "准备推送到 GitHub"
echo "========================================="
echo "GitHub 用户名: $GITHUB_USERNAME"
echo "仓库名称: $REPO_NAME"
echo "远程地址: https://github.com/$GITHUB_USERNAME/$REPO_NAME.git"
echo ""
echo "请确保您已经在 GitHub 上创建了这个仓库！"
echo "如果还没有创建，请访问: https://github.com/new"
echo ""
read -p "按 Enter 继续，或 Ctrl+C 取消..."

# 初始化 git 仓库（如果需要）
if [ ! -d ".git" ]; then
    echo "初始化 git 仓库..."
    git init
fi

# 添加所有文件
echo "添加文件到 git..."
git add .

# 创建提交
echo "创建提交..."
git commit -m "Initial commit: Add async episode saving and resume recording

- Implemented AsyncEpisodeSaver for non-blocking episode saving
- Added resume recording functionality with --dataset.resume parameter
- Updated documentation and examples
- Added bimanual SO100 configurations"

# 检查是否已经有 origin 远程仓库
if git remote | grep -q "^origin$"; then
    echo "远程仓库 'origin' 已存在，删除旧的..."
    git remote remove origin
fi

# 添加远程仓库
echo "添加远程仓库..."
git remote add origin https://github.com/$GITHUB_USERNAME/$REPO_NAME.git

# 设置主分支名称
echo "设置主分支为 main..."
git branch -M main

# 推送到 GitHub
echo "推送到 GitHub..."
git push -u origin main

echo ""
echo "========================================="
echo "完成！"
echo "========================================="
echo "您的仓库地址: https://github.com/$GITHUB_USERNAME/$REPO_NAME"
echo ""
echo "后续更新使用:"
echo "  git add ."
echo "  git commit -m \"Your message\""
echo "  git push"
