#!/bin/bash
# Friday AI 助手 - 完整启动脚本
# 集成: MiniCPM-V-2_6 (视觉+文本) + CosyVoice (TTS) + SenseVoice (ASR)

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}==========================================${NC}"
echo -e "${GREEN}  Friday AI 助手启动器${NC}"
echo -e "${GREEN}==========================================${NC}"
echo ""

# 配置
MODEL_DIR="/opt/image/OpenBMB/MiniCPM-V-2_6-gguf"
LLAMA_SERVER="$HOME/llama.cpp/build/bin/llama-server"
COSYVOICE_DIR="/opt/image/CosyVoice-300M-SFT"
SENSEVOICE_DIR="$HOME/SenseVoice.cpp"

# 检查模型文件
check_models() {
    echo -e "${BLUE}📦 检查模型文件...${NC}"
    
    if [ ! -f "$MODEL_DIR/ggml-model-Q4_K_M.gguf" ]; then
        echo -e "${RED}❌ 错误: MiniCPM-V 模型不存在${NC}"
        echo "   路径: $MODEL_DIR/ggml-model-Q4_K_M.gguf"
        return 1
    fi
    echo -e "${GREEN}✅ MiniCPM-V-2_6 Q4_K_M 模型已就绪${NC}"
    
    if [ ! -f "$MODEL_DIR/mmproj-model-f16.gguf" ]; then
        echo -e "${RED}❌ 错误: 视觉投影文件不存在${NC}"
        return 1
    fi
    echo -e "${GREEN}✅ 视觉投影组件已就绪${NC}"
    
    if [ ! -d "$COSYVOICE_DIR" ]; then
        echo -e "${YELLOW}⚠️  警告: CosyVoice 模型不存在，语音功能将不可用${NC}"
    else
        echo -e "${GREEN}✅ CosyVoice 语音模型已就绪${NC}"
    fi
    
    echo ""
}

# 启动 MiniCPM-V API 服务
start_vision_api() {
    echo -e "${BLUE}🚀 启动 MiniCPM-V API 服务...${NC}"
    echo -e "   地址: ${GREEN}http://0.0.0.0:11434${NC}"
    echo -e "   显存: ~6GB"
    echo ""
    
    $LLAMA_SERVER \
        -m "$MODEL_DIR/ggml-model-Q4_K_M.gguf" \
        --mmproj "$MODEL_DIR/mmproj-model-f16.gguf" \
        --host 0.0.0.0 \
        --port 11434 \
        -ngl 99 \
        -c 8192 \
        --batch-size 256 \
        --flash-attn on \
        --threads 12 \
        --parallel 1 \
        --n-predict 4096 \
        --jinja \
        --temp 0.7 &
    
    LLAMA_PID=$!
    echo $LLAMA_PID > /tmp/friday_llama.pid
    
    # 等待服务启动
    echo -e "${YELLOW}⏳ 等待服务启动...${NC}"
    for i in {1..30}; do
        if curl -s http://localhost:11434/health > /dev/null 2>&1; then
            echo -e "${GREEN}✅ MiniCPM-V API 服务已启动${NC}"
            echo ""
            return 0
        fi
        sleep 1
        echo -n "."
    done
    
    echo ""
    echo -e "${RED}❌ 服务启动超时${NC}"
    return 1
}

# 显示使用说明
show_usage() {
    echo -e "${GREEN}==========================================${NC}"
    echo -e "${GREEN}  Friday AI 助手已就绪${NC}"
    echo -e "${GREEN}==========================================${NC}"
    echo ""
    echo -e "${BLUE}API 端点:${NC}"
    echo "  - 视觉+文本: http://localhost:11434"
    echo ""
    echo -e "${BLUE}使用方式:${NC}"
    echo "  1. 直接调用 API"
    echo "  2. 使用 webui: python webui.py"
    echo "  3. 使用 gateway.py"
    echo ""
    echo -e "${BLUE}停止服务:${NC}"
    echo "  ./stop_friday.sh"
    echo ""
}

# 主函数
main() {
    # 检查模型
    check_models || exit 1
    
    # 启动服务
    start_vision_api || exit 1
    
    # 显示使用说明
    show_usage
    
    # 保持脚本运行
    echo -e "${YELLOW}按 Ctrl+C 停止服务${NC}"
    wait
}

# 捕获中断信号
trap 'echo ""; echo -e "${YELLOW}🛑 正在停止服务...${NC}"; kill $(cat /tmp/friday_llama.pid 2>/dev/null) 2>/dev/null; exit 0' INT

# 运行主函数
main
