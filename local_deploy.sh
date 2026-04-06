#!/bin/bash
# Friday 本地部署脚本 (RTX 3080 10GB)
# 模型: MiniCPM-V-2.6 (视觉) + Faster-Whisper (语音) + ChatTTS (TTS)

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

pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118 -q
pip install fastapi uvicorn websockets livekit-api soundfile librosa numpy curl-cffi -q
pip install "faster-whisper>=0.10" -q

ok "Python 包安装完成"

# ========== 克隆项目 ==========
info "克隆项目..."

cd "$OPT_DIR"

if [[ ! -d "Friday" ]]; then
    git clone https://github.com/quqiufeng/Friday.git
fi

if [[ ! -d "llama.cpp-omni" ]]; then
    git clone https://github.com/tc-mb/llama.cpp-omni.git
fi

if [[ ! -d "MiniCPM-V-CookBook" ]]; then
    git clone https://github.com/OpenSQZ/MiniCPM-V-CookBook.git
fi

ok "项目克隆完成"

# ========== 编译 llama.cpp ==========
info "编译 llama.cpp-omni..."

cd "$OPT_DIR/llama.cpp-omni"

cmake -B build \
    -DCMAKE_BUILD_TYPE=Release \
    -DGGML_CUDA=ON \
    -DLLAMA_CURL=OFF \
    -DCMAKE_CUDA_COMPILER=$CUDA_HOME/bin/nvcc > /dev/null 2>&1

cmake --build build --target llama-server -j$(nproc) > /dev/null 2>&1

ok "llama.cpp 编译完成"

# ========== 下载模型 ==========
info "下载模型 (约 5GB)..."

cd "$MODEL_DIR"

# MiniCPM-V-2.6 Q4 量化 (约 4GB)
if [[ ! -f "MiniCPM-V-2.6-q4_k_m.gguf" ]]; then
    wget -nc -q https://huggingface.co/openbmb/MiniCPM-V-2.6-gguf/resolve/main/MiniCPM-V-2.6-q4_k_m.gguf
fi

# Whisper Medium (约 1.5GB)
if [[ ! -d "whisper-medium" ]]; then
    mkdir -p whisper-medium
    wget -nc -q https://huggingface.co/Systran/faster-whisper-medium/resolve/main/model.bin -O whisper-medium/model.bin
fi

ok "模型下载完成"

# ========== 启动服务 ==========
info "启动服务..."

source /root/miniconda3/etc/profile.d/conda.sh
conda activate friday

LOCAL_IP=$(hostname -I | awk '{print $1}')

# 启动 LiveKit
echo "[1/4] LiveKit..."
livekit-server --config "$OPT_DIR/MiniCPM-V-CookBook/demo/web_demo/WebRTC_Demo/omini_backend_code/config/livekit.yaml" \
    > "$OPT_DIR/.logs/livekit.log" 2>&1 &
echo $! > "$OPT_DIR/.pids/livekit.pid"
sleep 2

# 启动后端
echo "[2/4] 后端..."
cd "$OPT_DIR/MiniCPM-V-CookBook/demo/web_demo/WebRTC_Demo/omini_backend_code/code"
LIVEKIT_URL="ws://localhost:$LIVEKIT_PORT" \
LIVEKIT_API_KEY="devkey" \
LIVEKIT_API_SECRET="secretsecretsecretsecretsecretsecret" \
python main.py > "$OPT_DIR/.logs/backend.log" 2>&1 &
echo $! > "$OPT_DIR/.pids/backend.pid"
sleep 3

# 启动 C++ 推理
echo "[3/4] C++ 推理..."
cd "$OPT_DIR/llama.cpp-omni"
python "$OPT_DIR/MiniCPM-V-CookBook/demo/web_demo/WebRTC_Demo/cpp_server/minicpmo_cpp_http_server.py" \
    --llamacpp-root "$OPT_DIR/llama.cpp-omni" \
    --model-dir "$MODEL_DIR" \
    --port $CPP_PORT \
    --gpu-devices 0 \
    > "$OPT_DIR/.logs/cpp.log" 2>&1 &
echo $! > "$OPT_DIR/.pids/cpp.pid"

# 启动前端
echo "[4/4] 前端..."
cd "$OPT_DIR/MiniCPM-V-CookBook/demo/web_demo/WebRTC_Demo/o45-frontend"
VITE_LIVEKIT_URL="ws://$LOCAL_IP:$LIVEKIT_PORT" \
pnpm dev > "$OPT_DIR/.logs/frontend.log" 2>&1 &
echo $! > "$OPT_DIR/.pids/frontend.pid"

sleep 5

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   部署完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "访问地址: ${YELLOW}http://$LOCAL_IP:$FRONTEND_PORT${NC}"
echo ""
echo "日志: tail -f $OPT_DIR/.logs/*.log"
