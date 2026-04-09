#!/bin/bash
# 下载 MiniCPM-V-2_6 GGUF 模型

set -e

MODEL_DIR="/opt/image/MiniCPM-V-2_6-gguf"
mkdir -p $MODEL_DIR

echo "=========================================="
echo "下载 MiniCPM-V-2_6 GGUF 模型"
echo "=========================================="

cd $MODEL_DIR

# 下载 Q4_K_M 量化版本 (4.68GB，适合 RTX 3080 10GB)
echo "🔄 下载 LLM 模型 (Q4_K_M)..."
wget -c "https://huggingface.co/openbmb/MiniCPM-V-2_6-gguf/resolve/main/Model-7.6B-Q4_K_M.gguf" -O model-Q4_K_M.gguf

echo "🔄 下载视觉投影层..."
wget -c "https://huggingface.co/openbmb/MiniCPM-V-2_6-gguf/resolve/main/mmproj-model-f16.gguf" -O mmproj-model-f16.gguf

echo "=========================================="
echo "✅ 下载完成！"
echo "模型位置: $MODEL_DIR"
echo "=========================================="
