#!/bin/bash
# Friday AI 助手启动脚本
# 使用 MiniCPM-V-2_6 (llama.cpp) + CosyVoice

set -e

echo "=========================================="
echo "Friday AI 助手启动"
echo "=========================================="

# 模型路径
LLAMA_CPP="/home/dministrator/llama.cpp/build/bin/llama-mtmd-cli"
MODEL="/opt/image/OpenBMB/MiniCPM-V-2_6-gguf/ggml-model-Q4_K_M.gguf"
MMPROJ="/opt/image/OpenBMB/MiniCPM-V-2_6-gguf/mmproj-model-f16.gguf"

# 检查模型文件
if [ ! -f "$MODEL" ]; then
    echo "❌ 错误: 模型文件不存在: $MODEL"
    exit 1
fi

if [ ! -f "$MMPROJ" ]; then
    echo "❌ 错误: 视觉投影文件不存在: $MMPROJ"
    exit 1
fi

echo "✅ 模型文件检查通过"
echo ""
echo "启动参数:"
echo "  模型: MiniCPM-V-2_6 Q4_K_M"
echo "  显存占用: ~6GB"
echo "  功能: 文本对话 + 图片理解"
echo ""
echo "使用说明:"
echo "  - 直接输入: 文本对话"
echo "  - /image <路径>: 加载图片"
echo "  - /clear: 清空历史"
echo "  - /quit: 退出"
echo "=========================================="

# 启动 llama-mtmd-cli
$LLAMA_CPP \
    -m "$MODEL" \
    --mmproj "$MMPROJ" \
    -c 4096 \
    --temp 0.7 \
    --top-p 0.8 \
    --top-k 100 \
    --repeat-penalty 1.05 \
    -i
