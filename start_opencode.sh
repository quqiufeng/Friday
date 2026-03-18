#!/bin/bash
# =============================================================================
# OpenCode 启动脚本
# =============================================================================
# 
# 用途：
#   使用 tmux 在一个会话中同时启动 OpenCode ACP 服务器和 TUI attach
#   - 窗口1 (acp): 运行 OpenCode ACP 服务器，监听 port 4096
#   - 窗口2 (attach): 自动附加到 OpenCode 服务器的 TUI 界面
#
# 解决的问题：
#   - OpenCode ACP 需要服务器常驻运行
#   - attach 需要连接到已启动的服务器
#   - 使用 tmux 可以在一个终端中同时管理多个窗口
#
# 使用方法：
#   1. 运行脚本: ./start_opencode.sh
#   2. 进入 tmux:  tmux attach -t opencode
#   3. 切换窗口:   Ctrl+b 0 (acp) 或 Ctrl+b 1 (attach)
#   4. 退出 tmux:  Ctrl+b d (detach，不关闭窗口)
# =============================================================================

SESSION="opencode"
PORT=4096

# 检查 tmux 是否安装
if ! command -v tmux &> /dev/null; then
    echo "Error: tmux not installed"
    exit 1
fi

# 如果会话已存在，先杀掉
tmux kill-session -t $SESSION 2>/dev/null

# -----------------------------------------------------------------------------
# 创建 tmux 会话
# -----------------------------------------------------------------------------

# 窗口1: OpenCode ACP 服务器
tmux new-session -d -s $SESSION -n "acp"
tmux send-keys -t $SESSION:0 "opencode serve --port $PORT --hostname 0.0.0.0" C-m

# 窗口2: attach 到 OpenCode
tmux new-window -t $SESSION -n "attach"
tmux send-keys -t $SESSION:1 "sleep 2 && opencode attach http://localhost:$PORT" C-m

# -----------------------------------------------------------------------------
# 显示帮助信息
# -----------------------------------------------------------------------------
echo "=============================================="
echo "  OpenCode 启动完成！"
echo "=============================================="
echo ""
echo "Session: $SESSION"
echo "Port: $PORT"
echo ""
echo "窗口说明:"
echo "  [0] acp    - OpenCode ACP 服务器 (后台运行)"
echo "  [1] attach - TUI 附加到 OpenCode (交互界面)"
echo ""
echo "=============================================="
echo "  tmux 快捷键"
echo "=============================================="
echo ""
echo "进入 tmux:     tmux attach -t opencode"
echo "退出 tmux:     Ctrl+b d"
echo ""
echo "窗口操作:"
echo "  Ctrl+b 0     切换到 acp 窗口"
echo "  Ctrl+b 1     切换到 attach 窗口"
echo "  Ctrl+b n     切换到下一个窗口"
echo "  Ctrl+b p     切换到上一个窗口"
echo "  Ctrl+b w     列出所有窗口"
echo "  Ctrl+b ,     重命名当前窗口"
echo ""
echo "窗格操作 (可选):"
echo "  Ctrl+b %     垂直分屏"
echo "  Ctrl+b \"     水平分屏"
echo "  Ctrl+b o     切换窗格"
echo "  Ctrl+b x     关闭当前窗格"
echo ""
echo "=============================================="
echo ""
