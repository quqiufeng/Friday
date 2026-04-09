#!/bin/bash
# Friday AI 助手 - 停止脚本

echo "🛑 正在停止 Friday AI 助手..."

# 停止 llama-server
if [ -f /tmp/friday_llama.pid ]; then
    PID=$(cat /tmp/friday_llama.pid)
    if kill -0 $PID 2>/dev/null; then
        kill $PID
        echo "✅ llama-server 已停止"
    fi
    rm -f /tmp/friday_llama.pid
fi

# 停止其他相关进程
pkill -f "llama-server" 2>/dev/null && echo "✅ 已清理 llama-server 进程"

echo "✅ Friday AI 助手已完全停止"
