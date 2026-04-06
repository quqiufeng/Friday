#!/bin/bash
set -e

# ========== 已完成的配置 ==========
export LLAMACPP_ROOT="/opt/llama.cpp-omni"
export MODEL_DIR="/opt/gguf/MiniCPM-o-4_5"
export PYTHON_CMD="/root/miniconda3/bin/python3"
export CPP_MODE="duplex"

# ========== 路径配置 ==========
SCRIPT_DIR="/opt/Friday/WebRTC"
PROJECT_DIR="$SCRIPT_DIR"
LIVEKIT_CONFIG="$PROJECT_DIR/omini_backend_code/config/livekit.yaml"
BACKEND_DIR="$PROJECT_DIR/omini_backend_code/code"
FRONTEND_DIR="$PROJECT_DIR/o45-frontend"
CPP_SERVER_SCRIPT="$PROJECT_DIR/cpp_server/minicpmo_cpp_http_server.py"
CPP_REF_AUDIO="$PROJECT_DIR/cpp_server/assets/default_ref_audio.wav"

# ========== 端口配置 ==========
LIVEKIT_PORT=7880
BACKEND_PORT=8021
FRONTEND_PORT=3000
CPP_SERVER_PORT=9060
CPP_HEALTH_PORT=$((CPP_SERVER_PORT + 1))

# ========== PID/日志目录 ==========
PID_DIR="$SCRIPT_DIR/.pids"
LOG_DIR="$SCRIPT_DIR/.logs"
mkdir -p "$PID_DIR" "$LOG_DIR"

LIVEKIT_PID="$PID_DIR/livekit.pid"
BACKEND_PID="$PID_DIR/backend.pid"
FRONTEND_PID="$PID_DIR/frontend.pid"
CPP_SERVER_PID="$PID_DIR/cpp_server.pid"

LIVEKIT_LOG="$LOG_DIR/livekit.log"
BACKEND_LOG="$LOG_DIR/backend.log"
FRONTEND_LOG="$LOG_DIR/frontend.log"
CPP_SERVER_LOG="$LOG_DIR/cpp_server.log"

# ========== 颜色 ==========
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
err()   { echo -e "${RED}[ERROR]${NC} $*"; }

get_local_ip() { hostname -I 2>/dev/null | awk '{print $1}' || echo "127.0.0.1"; }
get_public_ip() { curl -s ifconfig.me || curl -s ip.sb || echo ""; }
check_port() { (echo >/dev/tcp/127.0.0.1/"$1") 2>/dev/null && return 0; return 1; }

wait_for_port() {
    local port=$1 name=$2 max_wait=${3:-30} i=0
    while ! check_port "$port"; do
        sleep 1; i=$((i + 1))
        if [[ $i -ge $max_wait ]]; then err "$name 启动超时"; return 1; fi
    done
    ok "$name 已启动 (端口 $port)"
}

kill_old() {
    local pidfile=$1 name=$2
    if [[ -f "$pidfile" ]]; then
        local pid=$(cat "$pidfile")
        if kill -0 "$pid" 2>/dev/null; then
            info "停止旧 $name (PID: $pid)..."
            kill "$pid" 2>/dev/null || true; sleep 1
        fi
        rm -f "$pidfile"
    fi
}

start_livekit() {
    echo ""; info "========== [1/4] 启动 LiveKit =========="
    kill_old "$LIVEKIT_PID" "LiveKit"
    local local_ip=$(get_local_ip)
    local public_ip=$(get_public_ip)
    info "内网IP: $local_ip, 公网IP: $public_ip"
    sed -i "s/node_ip: .*/node_ip: \"$public_ip\"/" "$LIVEKIT_CONFIG"
    sed -i "s/domain: .*/domain: \"$public_ip\"/" "$LIVEKIT_CONFIG"
    /opt/livekit-server --config "$LIVEKIT_CONFIG" > "$LIVEKIT_LOG" 2>&1 &
    echo $! > "$LIVEKIT_PID"
    wait_for_port "$LIVEKIT_PORT" "LiveKit" 10
}

start_backend() {
    echo ""; info "========== [2/4] 启动后端 =========="
    kill_old "$BACKEND_PID" "Backend"
    LIVEKIT_URL="ws://localhost:$LIVEKIT_PORT" \
    LIVEKIT_API_KEY="devkey" \
    LIVEKIT_API_SECRET="secretsecretsecretsecretsecretsecret" \
    WORKERS=1 NUMBA_CACHE_DIR=/tmp/numba_cache \
    $PYTHON_CMD "$BACKEND_DIR/main.py" > "$BACKEND_LOG" 2>&1 &
    echo $! > "$BACKEND_PID"
    wait_for_port "$BACKEND_PORT" "Backend" 30
}

start_cpp_server() {
    echo ""; info "========== [3/4] 启动 C++ 推理服务 (首次2-3分钟) =========="
    kill_old "$CPP_SERVER_PID" "C++推理"
    pkill -f "minicpmo_cpp_http_server" 2>/dev/null || true
    local mode_flag="--simplex"; [[ "$CPP_MODE" == "duplex" ]] && mode_flag="--duplex"
    cd "$LLAMACPP_ROOT"
    CUDA_VISIBLE_DEVICES=0 REGISTER_URL="http://127.0.0.1:$BACKEND_PORT" REF_AUDIO="$CPP_REF_AUDIO" \
    $PYTHON_CMD "$CPP_SERVER_SCRIPT" \
        --llamacpp-root "$LLAMACPP_ROOT" --model-dir "$MODEL_DIR" \
        --port "$CPP_SERVER_PORT" --gpu-devices 0 $mode_flag > "$CPP_SERVER_LOG" 2>&1 &
    echo $! > "$CPP_SERVER_PID"
    wait_for_port "$CPP_HEALTH_PORT" "C++推理(健康检查)" 60
    info "等待模型加载..."
    local i=0
    while true; do
        local health=$(curl -s "http://localhost:$CPP_SERVER_PORT/health" 2>/dev/null || echo "")
        if echo "$health" | grep -q '"healthy"'; then ok "C++ 推理服务已就绪"; break; fi
        sleep 5; i=$((i + 5))
        if [[ $i -ge 300 ]]; then warn "C++ 推理服务启动超时"; break; fi
        [[ $((i % 30)) -eq 0 ]] && info "仍在等待模型加载... (${i}s)"
    done
    curl -s -X POST "http://localhost:$BACKEND_PORT/api/inference/register" \
        -H 'Content-Type: application/json' \
        -d "{\"ip\": \"$(get_local_ip)\", \"port\": $CPP_SERVER_PORT, \"model_port\": $CPP_SERVER_PORT, \"model_type\": \"$CPP_MODE\", \"session_type\": \"release\", \"service_name\": \"o45-cpp\"}" || true
    ok "推理服务已注册"
}

start_frontend() {
    echo ""; info "========== [4/4] 启动前端 =========="
    kill_old "$FRONTEND_PID" "Frontend"
    cd "$FRONTEND_DIR"
    INSTANCE_ID="${XGC_INSTANCE_ID:-}"
    if [[ -n "$INSTANCE_ID" ]]; then
        export VITE_API_URL="https://${INSTANCE_ID}-${BACKEND_PORT}.container.x-gpu.com"
        export VITE_LIVEKIT_URL="wss://${INSTANCE_ID}-${LIVEKIT_PORT}.container.x-gpu.com"
        info "使用公网URL: API=$VITE_API_URL LiveKit=$VITE_LIVEKIT_URL"
    else
        export VITE_API_URL="http://localhost:$BACKEND_PORT"
        export VITE_LIVEKIT_URL="ws://localhost:$LIVEKIT_PORT"
        info "使用内网URL: API=$VITE_API_URL LiveKit=$VITE_LIVEKIT_URL"
    fi
    pnpm run dev > "$FRONTEND_LOG" 2>&1 &
    echo $! > "$FRONTEND_PID"
    wait_for_port "$FRONTEND_PORT" "Frontend" 60
}

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   MiniCPM-o WebRTC 启动脚本${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
info "LLAMACPP_ROOT: $LLAMACPP_ROOT"
info "MODEL_DIR: $MODEL_DIR"
info "PYTHON_CMD: $PYTHON_CMD"
info "模式: $CPP_MODE"

[[ ! -x "$LLAMACPP_ROOT/build/bin/llama-server" ]] && err "llama-server 未编译" && exit 1
[[ ! -f "$CPP_SERVER_SCRIPT" ]] && err "C++ 服务脚本不存在" && exit 1

start_livekit
start_backend
start_cpp_server
start_frontend

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   启动完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${GREEN}访问地址: http://localhost:$FRONTEND_PORT${NC}"
echo ""
INSTANCE_ID="${XGC_INSTANCE_ID:-}"
if [[ -n "$INSTANCE_ID" ]]; then
    echo -e "${YELLOW}公网访问地址:${NC}"
    echo "  Frontend: https://${INSTANCE_ID}-${FRONTEND_PORT}.container.x-gpu.com"
    echo "  Backend:  https://${INSTANCE_ID}-${BACKEND_PORT}.container.x-gpu.com"
    echo "  LiveKit:  wss://${INSTANCE_ID}-${LIVEKIT_PORT}.container.x-gpu.com"
fi
echo ""
echo "日志查看: tail -f $LOG_DIR/*.log"
