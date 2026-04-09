#!/bin/bash
# MiniCPM-o-2.6 依赖安装脚本（使用现有 dl 环境）

set -e

echo "=========================================="
echo "MiniCPM-o-2.6 依赖安装"
echo "使用现有 conda 环境: dl"
echo "=========================================="

# 检查是否在 dl 环境中
if [[ "$CONDA_DEFAULT_ENV" != "dl" ]]; then
    echo "⚠️  请先激活 dl 环境:"
    echo "   conda activate dl"
    exit 1
fi

echo "✅ 当前环境: $CONDA_DEFAULT_ENV"
echo "✅ Python: $(python --version)"

# 安装缺失的依赖
echo ""
echo "🔄 安装缺失的依赖..."

# 核心依赖（用于量化）
pip install bitsandbytes accelerate

# MiniCPM-o 特有依赖
pip install vector-quantize-pytorch==1.18.5 vocos==0.1.0

# 视频处理
pip install decord moviepy

# 其他工具
pip install requests

echo ""
echo "=========================================="
echo "✅ 依赖安装完成！"
echo "=========================================="
echo ""
echo "现在可以运行: python deploy_minicpmo26.py"
