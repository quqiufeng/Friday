#!/bin/bash
# Friday 本地部署脚本 (RTX 3080 10GB 适配版)
# 支持：MiniCPM-V-2.6 视觉理解 + Faster-Whisper 语音识别 + TTS 语音合成

set -e

# ========== 配置 ==========
export CUDA_HOME="${CUDA_HOME:-/usr/local/cuda}"
export PATH=$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH

# 模型目录
MODEL_DIR="${MODEL_DIR:-/opt/models}"
mkdir -p "$MODEL_DIR"

# 安装目录
OPT_DIR="${OPT_DIR:-/opt/friday}"
mkdir -p "$OPT_DIR"

# 端口
LIVEKIT_PORT=7880
BACKEND_PORT=8021
FRONTEND_PORT=3000

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
err()   { echo -e "${RED}[ERROR]${NC} $*"; }

# ========== 依赖检查 ==========
check_dependencies() {
    info "检查系统依赖..."
    
    # CUDA
    if command -v nvcc &> /dev/null; then
        ok "CUDA: $(nvcc --version | grep "release" | awk '{print $5}' | tr -d ',')"
    else
        err "CUDA 未安装，请先安装 CUDA Toolkit"
        exit 1
    fi
    
    # Python
    if command -v python3 &> /dev/null; then
        ok "Python: $(python3 --version)"
    else
        err "Python3 未安装"
        exit 1
    fi
    
    # Git
    if command -v git &> /dev/null; then
        ok "Git: $(git --version)"
    else
        err "Git 未安装"
        exit 1
    fi
    
    # CMake
    if command -v cmake &> /dev/null; then
        ok "CMake: $(cmake --version | head -1)"
    else
        info "安装 CMake..."
        apt-get update && apt-get install -y cmake
    fi
    
    # libcurl
    if pkg-config --exists libcurl 2>/dev/null || ldconfig -p | grep -q libcurl; then
        ok "libcurl 已安装"
    else
        info "安装 libcurl..."
        apt-get update && apt-get install -y libcurl4-openssl-dev
    fi
}

# ========== 克隆项目 ==========
clone_projects() {
    info "克隆项目..."
    
    cd "$OPT_DIR"
    
    # Friday 主项目
    if [[ ! -d "Friday" ]]; then
        git clone https://github.com/quqiufeng/Friday.git
    fi
    ok "Friday 已克隆"
    
    # llama.cpp-omni (用于语音/视频推理)
    if [[ ! -d "llama.cpp-omni" ]]; then
        git clone https://github.com/tc-mb/llama.cpp-omni.git
    fi
    ok "llama.cpp-omni 已克隆"
    
    # MiniCPM-V-CookBook (WebRTC Demo)
    if [[ ! -d "MiniCPM-V-CookBook" ]]; then
        git clone https://github.com/OpenSQZ/MiniCPM-V-CookBook.git
    fi
    ok "MiniCPM-V-CookBook 已克隆"
}

# ========== 编译 llama.cpp-omni ==========
build_llama_cpp() {
    info "编译 llama.cpp-omni..."
    
    cd "$OPT_DIR/llama.cpp-omni"
    
    cmake -B build \
        -DCMAKE_BUILD_TYPE=Release \
        -DGGML_CUDA=ON \
        -DLLAMA_CURL=OFF \
        -DCMAKE_CUDA_COMPILER=$CUDA_HOME/bin/nvcc
    
    cmake --build build --target llama-server -j$(nproc)
    
    ok "llama.cpp-omni 编译完成"
}

# ========== 下载模型 ==========
download_models() {
    info "下载模型到 $MODEL_DIR..."
    
    mkdir -p "$MODEL_DIR"
    cd "$MODEL_DIR"
    
    # MiniCPM-V-2.6 (视觉模型，7B INT4)
    if [[ ! -f "MiniCPM-V-2.6-q4_k_m.gguf" ]]; then
        info "下载 MiniCPM-V-2.6 视觉模型..."
        wget -nc https://huggingface.co/openbmb/MiniCPM-V-2.6-gguf/resolve/main/MiniCPM-V-2.6-q4_k_m.gguf
    fi
    ok "MiniCPM-V-2.6 下载完成"
    
    # MiniCPM-o 音频编码器 (用于语音识别)
    if [[ ! -d "MiniCPM-o-audio" ]]; then
        info "下载 MiniCPM-o 音频编码器..."
        mkdir -p MiniCPM-o-audio
        wget -nc -P MiniCPM-o-audio https://huggingface.co/openbmb/MiniCPM-o-4_5-gguf/resolve/main/audio/MiniCPM-o-4_5-audio-F16.gguf
    fi
    ok "音频编码器下载完成"
    
    # TTS 模型
    if [[ ! -d "tts_model" ]]; then
        info "下载 TTS 模型..."
        mkdir -p tts_model
        wget -nc -P tts_model https://huggingface.co/openbmb/MiniCPM-o-4_5-gguf/resolve/main/tts/MiniCPM-o-4_5-tts-F16.gguf
    fi
    ok "TTS 模型下载完成"
    
    # Whisper 模型 (语音识别)
    if [[ ! -d "whisper-medium" ]]; then
        info "下载 Whisper 模型..."
        # 可以用 faster-whisper 下载，或手动下载
        mkdir -p whisper-medium
    fi
    ok "Whisper 模型准备完成"
}

# ========== 安装 Python 依赖 ==========
install_python_deps() {
    info "安装 Python 依赖..."
    
    # 创建 conda 环境（推荐）
    if command -v conda &> /dev/null; then
        info "使用现有 conda"
    else
        info "安装 Miniconda..."
        wget -q https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /tmp/miniconda.sh
        bash /tmp/miniconda.sh -b -p /root/miniconda3
        export PATH=/root/miniconda3/bin:$PATH
    fi
    
    export PATH=/root/miniconda3/bin:$PATH
    
    # 创建环境
    conda create -n friday python=3.10 -y
    conda activate friday
    
    # 安装 PyTorch (CUDA)
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
    
    # 安装 WebRTC 相关
    pip install fastapi uvicorn websockets
    
    # 安装 LiveKit SDK
    pip install livekit-api livekit
    
    # 安装音频处理
    pip install soundfile librosa numpy
    
    # 安装 curl-cffi (HTTP)
    pip install curl-cffi
    
    ok "Python 依赖安装完成"
}

# ========== 配置 WebRTC ==========
setup_webrtc() {
    info "配置 WebRTC..."
    
    # 复制 WebRTC Demo
    WEBRTC_DIR="$OPT_DIR/MiniCPM-V-CookBook/demo/web_demo/WebRTC_Demo"
    
    # 修改 livekit 配置（使用本地 IP）
    LOCAL_IP=$(hostname -I | awk '{print $1}')
    info "本地 IP: $LOCAL_IP"
    
    # 创建软链接
    ln -sf "$WEBRTC_DIR" "$OPT_DIR/WebRTC_Demo"
    
    ok "WebRTC 配置完成"
}

# ========== 生成启动脚本 ==========
generate_start_script() {
    info "生成启动脚本..."
    
    cat > "$OPT_DIR/start_friday.sh" << 'EOF'
#!/bin/bash
# Friday 本地启动脚本

set -e

export PATH=/root/miniconda3/bin:$PATH
conda activate friday

OPT_DIR="/opt/friday"
MODEL_DIR="/opt/models"
LOCAL_IP=$(hostname -I | awk '{print $1}')

# 端口
LIVEKIT_PORT=7880
BACKEND_PORT=8021
FRONTEND_PORT=3000
CPP_PORT=9060

# PID 目录
PID_DIR="$OPT_DIR/.pids"
LOG_DIR="$OPT_DIR/.logs"
mkdir -p "$PID_DIR" "$LOG_DIR"

echo "========================================"
echo "   Friday 本地启动"
echo "========================================"
echo "IP: $LOCAL_IP"
echo ""

# 启动 LiveKit
echo "[1/4] 启动 LiveKit..."
if [[ -f "$PID_DIR/livekit.pid" ]] && kill -0 $(cat "$PID_DIR/livekit.pid") 2>/dev/null; then
    echo "LiveKit 已运行"
else
    cd "$OPT_DIR"
    livekit-server --config "$OPT_DIR/WebRTC_Demo/omini_backend_code/config/livekit.yaml" \
        > "$LOG_DIR/livekit.log" 2>&1 &
    echo $! > "$PID_DIR/livekit.pid"
    sleep 2
fi
echo "LiveKit 启动完成"

# 启动后端
echo "[2/4] 启动后端..."
if [[ -f "$PID_DIR/backend.pid" ]] && kill -0 $(cat "$PID_DIR/backend.pid") 2>/dev/null; then
    echo "后端已运行"
else
    cd "$OPT_DIR/WebRTC_Demo/omini_backend_code/code"
    LIVEKIT_URL="ws://localhost:$LIVEKIT_PORT" \
    LIVEKIT_API_KEY="devkey" \
    LIVEKIT_API_SECRET="secretsecretsecretsecretsecretsecret" \
    python main.py > "$LOG_DIR/backend.log" 2>&1 &
    echo $! > "$PID_DIR/backend.pid"
    sleep 3
fi
echo "后端启动完成"

# 启动 C++ 推理服务
echo "[3/4] 启动 C++ 推理..."
if [[ -f "$PID_DIR/cpp.pid" ]] && kill -0 $(cat "$PID_DIR/cpp.pid") 2>/dev/null; then
    echo "C++ 推理已运行"
else
    cd "$OPT_DIR/llama.cpp-omni"
    python "$OPT_DIR/WebRTC_Demo/cpp_server/minicpmo_cpp_http_server.py" \
        --llamacpp-root "$OPT_DIR/llama.cpp-omni" \
        --model-dir "$MODEL_DIR" \
        --port $CPP_PORT \
        --gpu-devices 0 \
        > "$LOG_DIR/cpp.log" 2>&1 &
    echo $! > "$PID_DIR/cpp.pid"
    echo "C++ 推理启动中（首次需要加载模型，约1-2分钟）..."
    sleep 5
fi
echo "C++ 推理启动完成"

# 启动前端
echo "[4/4] 启动前端..."
if [[ -f "$PID_DIR/frontend.pid" ]] && kill -0 $(cat "$PID_DIR/frontend.pid") 2>/dev/null; then
    echo "前端已运行"
else
    cd "$OPT_DIR/WebRTC_Demo/o45-frontend"
    VITE_LIVEKIT_URL="ws://$LOCAL_IP:$LIVEKIT_PORT" \
    pnpm dev > "$LOG_DIR/frontend.log" 2>&1 &
    echo $! > "$PID_DIR/frontend.pid"
    sleep 3
fi
echo "前端启动完成"

echo ""
echo "========================================"
echo "   启动完成！"
echo "========================================"
echo ""
echo "访问地址: http://$LOCAL_IP:$FRONTEND_PORT"
echo ""
echo "日志查看: tail -f $LOG_DIR/*.log"
EOF

    chmod +x "$OPT_DIR/start_friday.sh"
    ok "启动脚本已生成: $OPT_DIR/start_friday.sh"
}

# ========== 主流程 ==========
main() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}   Friday 本地部署脚本${NC}"
    echo -e "${BLUE}   适配: RTX 3080 10GB${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    
    check_dependencies
    clone_projects
    build_llama_cpp
    download_models
    install_python_deps
    setup_webrtc
    generate_start_script
    
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}   部署完成！${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "下一步："
    echo "  1. 运行: bash $OPT_DIR/start_friday.sh"
    echo "  2. 浏览器访问: http://<本地IP>:3000"
    echo ""
}

main "$@"
