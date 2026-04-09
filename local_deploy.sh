#!/bin/bash
# =============================================================================
# Friday - 本地部署脚本 (RTX 3080 10GB 适配版)
# =============================================================================
#
# 【项目概述】
# Friday 是一个基于 WebRTC 的实时语音/视频对话系统，让用户可以通过摄像头和麦克风
# 与大模型进行自然的语音和视频交互。
#
# 【系统架构】
#
#   ┌─────────────────────────────────────────────────────────────────────┐
#   │                        用户浏览器 (Browser)                          │
#   │   ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
#   │   │  音视频采集   │  │  WebRTC     │  │   Vue.js 前端        │   │
#   │   │  (摄像头/麦克风)│ │  媒体通道   │  │   (Vite Dev Server) │   │
#   │   └──────────────┘  └──────────────┘  └──────────────────────┘   │
#   └─────────────────────────────────────────────────────────────────────┘
#                                    │
#                                    │ WebSocket (wss://)
#                                    ▼
#   ┌─────────────────────────────────────────────────────────────────────┐
#   │                      LiveKit Server (SFU服务器)                       │
#   │                                                                       │
#   │   功能:                                                               │
#   │   - WebRTC 信令交换 (Signaling)                                       │
#   │   - 媒体流路由和转发 (SFU - Selective Forwarding Unit)                │
#   │   - TURN 服务器 (NAT穿透)                                            │
#   │   - 房间管理 (Room Management)                                       │
#   │                                                                       │
#   │   端口: 7880 (WebSocket), 7881 (TCP), 7882 (UDP TURN)               │
#   │   配置: livekit.yaml                                                  │
#   └─────────────────────────────────────────────────────────────────────┘
#                                    │
#                                    │ HTTP REST / WebSocket
#                                    ▼
#   ┌─────────────────────────────────────────────────────────────────────┐
#   │                      Python 后端 (FastAPI)                            │
#   │   路径: MiniCPM-V-CookBook/demo/web_demo/WebRTC_Demo/               │
#   │   模块:                                                                │
#   │   ├── voice_chat/           - 语音对话核心                            │
#   │   │   ├── livekit_room.py   - LiveKit房间管理，接收音频流              │
#   │   │   ├── robot_service.py  - 机器人服务，协调各组件                   │
#   │   │   ├── omni_stream.py    - 全双工流处理                            │
#   │   │   ├── model_call.py     - 调用C++推理服务                        │
#   │   │   └── vad/             - 语音活动检测 (VAD - Voice Activity Detection) │
#   │   │       └── silero_vad.onnx - Silero VAD 模型                      │
#   │   │                                                                   │
#   │   ├── services/              - 服务管理                               │
#   │   │   ├── inference_service_manager.py - 推理服务注册与调度            │
#   │   │   └── heartbeat_monitor.py - 心跳检测                             │
#   │   │                                                                   │
#   │   └── api/                   - HTTP API 路由                          │
#   │       └── inference_service_routes.py - 推理服务注册接口               │
#   │                                                                       │
#   │   依赖库:                                                             │
#   │   - livekit (livekit-api)     - LiveKit Python SDK                    │
#   │   - fastapi                   - Web 框架                             │
#   │   - uvicorn                   - ASGI 服务器                          │
#   │   - websockets                - WebSocket 支持                        │
#   │   - soundfile, librosa        - 音频处理                              │
#   │   - aiohttp                   - 异步 HTTP 客户端                     │
#   │                                                                       │
#   │   端口: 8021 (HTTP)                                                  │
#   └─────────────────────────────────────────────────────────────────────┘
#                                    │
#                                    │ HTTP (REST)
#                                    ▼
#   ┌─────────────────────────────────────────────────────────────────────┐
#   │                    C++ 推理服务 (Python HTTP Server)                  │
#   │   路径: cpp_server/minicpmo_cpp_http_server.py                        │
#   │                                                                       │
#   │   功能:                                                               │
#   │   - 封装 llama.cpp-omni 的 HTTP API                                   │
#   │   - 模型加载和推理调度                                                │
#   │   - 音频编解码                                                        │
#   │                                                                       │
#   │   调用链:                                                             │
#   │   Python HTTP → llama-server (C++) → GGUF 模型                       │
#   │                                                                       │
#   │   依赖库:                                                             │
#   │   - uvicorn                  - HTTP 服务器                            │
#   │   - curl-cffi               - HTTP 客户端 (C绑)                     │
#   │                                                                       │
#   │   端口: 9060 (HTTP), 9061 (健康检查)                                 │
#   └─────────────────────────────────────────────────────────────────────┘
#                                    │
#                                    │ CUDA/GPU
#                                    ▼
#   ┌─────────────────────────────────────────────────────────────────────┐
#   │                    llama.cpp-omni (C++ 推理引擎)                      │
#   │   路径: /opt/llama.cpp-omni                                         │
#   │                                                                       │
#   │   功能:                                                               │
#   │   - MiniCPM-o 多模态模型推理                                         │
#   │   - 音频编码 (Whisper 编码器)                                        │
#   │   - LLM 推理 (Transformer)                                           │
#   │   - TTS 合成 (Flow Matching)                                         │
#   │   - Token2Wav 声码器                                                 │
#   │                                                                       │
#   │   编译选项:                                                           │
#   │   - GGML_CUDA=ON        - 启用 CUDA GPU 加速                        │
#   │   - GGML_CUDA_VMM=ON    - 启用 CUDA 虚拟内存                        │
#   │   - LLAMA_CURL=OFF       - 禁用 curl (可选)                         │
#   │                                                                       │
#   │   模型文件 (~8.3GB):                                                  │
#   │   ├── MiniCPM-o-4_5-Q4_K_M.gguf     - LLM 主模型 (~5GB)            │
#   │   ├── audio/MiniCPM-o-4_5-audio-F16.gguf   - 音频编码器 (~660MB)   │
#   │   ├── vision/MiniCPM-o-4_5-vision-F16.gguf - 视觉编码器 (~1GB)     │
#   │   ├── tts/MiniCPM-o-4_5-tts-F16.gguf       - TTS 模型              │
#   │   └── token2wav-gguf/                      - Token2Wav 模型         │
#   │                                                                       │
#   │   端口: 19060 (HTTP)                                                │
#   └─────────────────────────────────────────────────────────────────────┘
#
# 【技术栈】
#
#   前端:
#   ├── Vue.js 3              - 渐进式 JavaScript 框架
#   ├── Vite                  - 新一代前端构建工具
#   ├── livekit-client         - LiveKit WebRTC 客户端
#   ├── @vueuse/core           - Vue 组合式工具库
#   └── Pinia                 - 状态管理
#
#   后端:
#   ├── Python 3.10+          - 运行时
#   ├── FastAPI                - Web 框架
#   ├── Uvicorn                 - ASGI 服务器
#   ├── LiveKit Python SDK      - LiveKit 服务端 SDK
#   ├── Silero VAD              - 语音活动检测模型
#   └── Numba                  - JIT 编译器 (加速音频处理)
#
#   推理:
#   ├── llama.cpp              - C++ LLM 推理库
#   ├── CUDA Toolkit            - NVIDIA GPU 计算平台
#   └── GGML                   - GPT 模型的张量运算库
#
#   基础设施:
#   ├── LiveKit Server          - WebRTC SFU 服务器
#   ├── Redis                  - 缓存 (可选)
#   └── Docker                 - 容器化 (可选)
#
# 【工作流程 - 语音对话】
#
#   1. 用户在浏览器点击"开始对话"
#   2. 浏览器采集麦克风音频流
#   3. 音频通过 WebRTC 发送到 LiveKit
#   4. Python 后端订阅 LiveKit 房间，获取音频流
#   5. 后端进行 VAD 检测（判断是否在说话）
#   6. 检测到语音结束后，将音频发送到 C++ 推理服务
#   7. C++ 服务调用 Whisper 编码器进行 ASR（语音识别）
#   8. 识别结果发送给 LLM 生成回复
#   9. LLM 输出通过 TTS 转换为音频
#   10. 音频流通过 LiveKit 发送回浏览器
#   11. 浏览器播放音频
#
# 【工作流程 - 视频对话】
#
#   1. 用户开启摄像头
#   2. 视频帧通过 WebRTC 传输
#   3. 后端定期采样视频帧
#   4. 视频帧发送到 C++ 服务的视觉编码器
#   5. 视觉特征与文本/语音融合
#   6. 多模态 LLM 生成回复
#   7. 回复内容通过语音输出
#
# 【环境要求】
#
#   最低配置 (单工模式):
#   - GPU: RTX 3060 12GB / RTX 3080 10GB
#   - CPU: 4 核+
#   - 内存: 16GB+
#   - 显存: 10GB+ (INT4 量化)
#
#   推荐配置 (全双工模式):
#   - GPU: RTX 4090 24GB / RTX 3090 24GB
#   - CPU: 8 核+
#   - 内存: 32GB+
#   - 显存: 16GB+ (INT4 量化)
#
# 【端口说明】
#
#   7880  - LiveKit WebSocket (信令)
#   7881  - LiveKit TCP (媒体)
#   7882  - LiveKit UDP TURN (NAT穿透)
#   8021  - Python 后端 HTTP API
#   9060  - C++ 推理服务 HTTP
#   3000  - Vite 前端开发服务器
#   50000-50100 - WebRTC 媒体端口范围
#
# =============================================================================

set -e

# ========== 配置 ==========
CUDA_HOME="${CUDA_HOME:-/usr/local/cuda}"
MODEL_DIR="/opt/models"
OPT_DIR="/opt/friday"

# 端口
LIVEKIT_PORT=7880
BACKEND_PORT=8021
FRONTEND_PORT=3000
CPP_PORT=9060

# ========== 颜色 ==========
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'
info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
err()   { echo -e "${RED}[ERROR]${NC} $*"; }

# ========== 前置检查 ==========
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   Friday 本地部署${NC}"
echo -e "${BLUE}========================================${NC}"

info "检查 CUDA..."
if ! command -v nvcc &> /dev/null; then
    err "CUDA 未安装"
    exit 1
fi
ok "CUDA: $(nvcc --version | grep release | awk '{print $5}' | tr -d ',')"

info "检查 Python..."
if ! command -v python3 &> /dev/null; then
    err "Python3 未安装"
    exit 1
fi
ok "Python: $(python3 --version)"

# ========== 创建目录 ==========
mkdir -p "$MODEL_DIR" "$OPT_DIR" "$OPT_DIR/.pids" "$OPT_DIR/.logs"

# ========== 安装系统依赖 ==========
info "安装系统依赖..."
apt-get update -qq
apt-get install -y -qq cmake libcurl4-openssl-dev wget git > /dev/null 2>&1
ok "系统依赖安装完成"

# ========== 安装 Miniconda ==========
info "安装 Miniconda..."
if [[ ! -f "/root/miniconda3/bin/conda" ]]; then
    wget -q https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /tmp/miniconda.sh
    bash /tmp/miniconda.sh -b -p /root/miniconda3 > /dev/null 2>&1
fi
export PATH="/root/miniconda3/bin:$PATH"
ok "Miniconda 已安装"

# ========== 创建 conda 环境 ==========
info "创建 Python 环境..."
/root/miniconda3/bin/conda create -n friday python=3.10 -y -q > /dev/null 2>&1
ok "conda 环境创建完成"

# ========== 安装 Python 包 ==========
info "安装 Python 包..."
source /root/miniconda3/etc/profile.d/conda.sh
conda activate friday

# PyTorch (CUDA 支持)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118 -q

# Web 服务
pip install fastapi uvicorn websockets -q

# LiveKit SDK (WebRTC 服务端)
pip install livekit-api -q

# 音频处理
pip install soundfile librosa numpy -q

# HTTP 客户端 (高性能)
pip install curl-cffi -q

# 语音活动检测 (VAD)
pip install silero-vad -q

# 快速 Whisper 推理
pip install "faster-whisper>=0.10" -q

ok "Python 包安装完成"

# ========== 克隆项目 ==========
info "克隆项目..."

cd "$OPT_DIR"

# Friday 主项目
if [[ ! -d "Friday" ]]; then
    git clone https://github.com/quqiufeng/Friday.git
fi
ok "Friday 已克隆"

# llama.cpp-omni (C++ 推理引擎)
if [[ ! -d "llama.cpp-omni" ]]; then
    git clone https://github.com/tc-mb/llama.cpp-omni.git
fi
ok "llama.cpp-omni 已克隆"

# MiniCPM-V-CookBook (WebRTC Demo)
if [[ ! -d "MiniCPM-V-CookBook" ]]; then
    git clone https://github.com/OpenSQZ/MiniCPM-V-CookBook.git
fi
ok "MiniCPM-V-CookBook 已克隆"

# ========== 编译 llama.cpp ==========
info "编译 llama.cpp-omni (CUDA 加速)..."

cd "$OPT_DIR/llama.cpp-omni"

cmake -B build \
    -DCMAKE_BUILD_TYPE=Release \
    -DGGML_CUDA=ON \
    -DLLAMA_CURL=OFF \
    -DCMAKE_CUDA_COMPILER=$CUDA_HOME/bin/nvcc > /dev/null 2>&1

cmake --build build --target llama-server -j$(nproc) > /dev/null 2>&1

ok "llama.cpp 编译完成 (二进制: build/bin/llama-server)"

# ========== 下载模型 ==========
info "下载模型 (约 5GB)..."

cd "$MODEL_DIR"

# MiniCPM-V-2.6 Q4 量化 (视觉模型, ~4GB)
# 7B 参数, INT4 量化, 适合 10GB 显存
if [[ ! -f "MiniCPM-V-2.6-q4_k_m.gguf" ]]; then
    wget -nc -q https://huggingface.co/openbmb/MiniCPM-V-2.6-gguf/resolve/main/MiniCPM-V-2.6-q4_k_m.gguf
fi
ok "MiniCPM-V-2.6 模型下载完成"

# Whisper Medium (语音识别, ~1.5GB)
# faster-whisper 格式
if [[ ! -d "whisper-medium" ]]; then
    mkdir -p whisper-medium
    wget -nc -q https://huggingface.co/Systran/faster-whisper-medium/resolve/main/model.bin -O whisper-medium/model.bin
fi
ok "Whisper Medium 模型下载完成"

# ========== 安装 LiveKit Server ==========
info "安装 LiveKit Server..."
if [[ ! -f "/opt/livekit-server" ]]; then
    wget -q https://github.com/livekit/livekit/releases/download/v1.9.11/livekit_1.9.11_linux_amd64.tar.gz -O /tmp/livekit.tar.gz
    tar -xzf /tmp/livekit.tar.gz -C /opt
    mv /opt/livekit-server /opt/livekit-server-bin
    ln -sf /opt/livekit-server-bin /opt/livekit-server
fi
ok "LiveKit Server 安装完成"

# ========== 启动服务 ==========
info "启动所有服务..."

source /root/miniconda3/etc/profile.d/conda.sh
conda activate friday

LOCAL_IP=$(hostname -I | awk '{print $1}')

# ---------------------------------------------------------------------------
# 服务启动顺序: LiveKit → 后端 → C++推理 → 前端
# ---------------------------------------------------------------------------

# [1/4] 启动 LiveKit Server
echo "[1/4] 启动 LiveKit Server (SFU)..."
/opt/livekit-server \
    --config "$OPT_DIR/MiniCPM-V-CookBook/demo/web_demo/WebRTC_Demo/omini_backend_code/config/livekit.yaml" \
    > "$OPT_DIR/.logs/livekit.log" 2>&1 &
echo $! > "$OPT_DIR/.pids/livekit.pid"
sleep 2
ok "LiveKit Server 已启动 (端口 $LIVEKIT_PORT)"

# [2/4] 启动 Python 后端
echo "[2/4] 启动 Python 后端 (FastAPI)..."
cd "$OPT_DIR/MiniCPM-V-CookBook/demo/web_demo/WebRTC_Demo/omini_backend_code/code"

LIVEKIT_URL="ws://localhost:$LIVEKIT_PORT" \
LIVEKIT_API_KEY="devkey" \
LIVEKIT_API_SECRET="secretsecretsecretsecretsecretsecret" \
WORKERS=1 \
NUMBA_CACHE_DIR=/tmp/numba_cache \
python main.py > "$OPT_DIR/.logs/backend.log" 2>&1 &
echo $! > "$OPT_DIR/.pids/backend.pid"
sleep 3
ok "Python 后端已启动 (端口 $BACKEND_PORT)"

# [3/4] 启动 C++ 推理服务
echo "[3/4] 启动 C++ 推理服务 (llama.cpp)..."
cd "$OPT_DIR/llama.cpp-omni"

CUDA_VISIBLE_DEVICES=0 \
python "$OPT_DIR/MiniCPM-V-CookBook/demo/web_demo/WebRTC_Demo/cpp_server/minicpmo_cpp_http_server.py" \
    --llamacpp-root "$OPT_DIR/llama.cpp-omni" \
    --model-dir "$MODEL_DIR" \
    --port $CPP_PORT \
    --gpu-devices 0 \
    --duplex \
    > "$OPT_DIR/.logs/cpp.log" 2>&1 &
echo $! > "$OPT_DIR/.pids/cpp.pid"
ok "C++ 推理服务启动中 (首次需加载模型，约1-2分钟)..."

# [4/4] 启动前端
echo "[4/4] 启动前端 (Vite Dev Server)..."
cd "$OPT_DIR/MiniCPM-V-CookBook/demo/web_demo/WebRTC_Demo/o45-frontend"

# 设置 LiveKit URL 为本机 IP
VITE_LIVEKIT_URL="ws://$LOCAL_IP:$LIVEKIT_PORT" \
pnpm dev > "$OPT_DIR/.logs/frontend.log" 2>&1 &
echo $! > "$OPT_DIR/.pids/frontend.pid"
sleep 3
ok "前端已启动 (端口 $FRONTEND_PORT)"

# ---------------------------------------------------------------------------
# 等待服务就绪
# ---------------------------------------------------------------------------
info "等待服务就绪..."
sleep 5

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   部署完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "访问地址: ${YELLOW}http://$LOCAL_IP:$FRONTEND_PORT${NC}"
echo ""
echo "服务状态:"
echo "  - LiveKit Server:  http://localhost:$LIVEKIT_PORT (SFU)"
echo "  - Python 后端:     http://localhost:$BACKEND_PORT (FastAPI)"
echo "  - C++ 推理:        http://localhost:$CPP_PORT (llama.cpp)"
echo "  - 前端:            http://localhost:$FRONTEND_PORT (Vite)"
echo ""
echo "日志查看:"
echo "  tail -f $OPT_DIR/.logs/livekit.log"
echo "  tail -f $OPT_DIR/.logs/backend.log"
echo "  tail -f $OPT_DIR/.logs/cpp.log"
echo "  tail -f $OPT_DIR/.logs/frontend.log"
echo ""
echo "停止服务:"
echo "  kill \$(cat $OPT_DIR/.pids/*.pid)"
