# Friday - 本地贾维斯 AI 助手系统

> 类似钢铁侠的贾维斯 (JARVIS)，支持语音、视频、手机远程控制

---

## 1. 系统架构

### 1.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              🏠 家庭 AI 中心 (Friday)                                │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                           多入口 (Anywhere Access)                          │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │   │
│  │  │    钉钉       │  │   WebUI      │  │   语音输入    │  │  视频对话    │   │   │
│  │  │  (手机/外出)  │  │   (浏览器)   │  │  (SenseVoice)│  │  (多模态)   │   │   │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘   │   │
│  └─────────┼──────────────────┼──────────────────┼──────────────────┼───────────┘   │
│            │                  │                  │                  │                │
│            └──────────────────┴──────────────────┴──────────────────┘                │
│                                         │                                             │
│                                         ▼                                             │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                         OpenCode (AI 大脑 + MCP)                          │   │
│  │  ┌─────────────────────────────────────────────────────────────────────┐  │   │
│  │  │  ACP 服务器 (port 4096)                                             │  │   │
│  │  │  ├── /tui/append-prompt  - 添加指令                                │  │   │
│  │  │  └── /tui/submit-prompt  - 提交执行                                │  │   │
│  │  └─────────────────────────────────────────────────────────────────────┘  │   │
│  │                                    │                                         │   │
│  │                    ┌───────────────┼───────────────┐                       │   │
│  │                    ▼               ▼               ▼                       │   │
│  │            ┌──────────────┐ ┌──────────────┐ ┌──────────────┐              │   │
│  │            │ Code Search  │ │ MiniMax-Tools│ │   其他 MCP   │              │   │
│  │            │ (向量检索)   │ │   (编程辅助)  │ │    插件      │              │   │
│  │            └──────────────┘ └──────────────┘ └──────────────┘              │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                         │                                             │
│                                         ▼                                             │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                         大模型推理层 (GPU)                                  │   │
│  │  ┌──────────────────────┐  ┌──────────────────────┐                       │   │
│  │  │   MiniCPM-o 2.6      │  │    Qwen 3.5 9B       │                       │   │
│  │  │   多模态大模型        │  │    文本模型           │                       │   │
│  │  │   (llama.cpp)        │  │    (llama.cpp)       │                       │   │
│  │  │   port: 11434        │  │    port: 11434       │                       │   │
│  │  └──────────────────────┘  └──────────────────────┘                       │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 分布式部署

```
☁️ 云端贾维斯                      🏠 本地贾维斯
┌─────────────────┐           ┌─────────────────┐
│  钉钉机器人      │           │  钉钉机器人      │
│  OpenCode      │◄─attach──►│  OpenCode       │
│  大模型        │  IP:Port   │  大模型         │
│  Code Search   │           │  Code Search    │
└─────────────────┘           └─────────────────┘
       │                             │
       │    独立运行，各自配置        │
       └─────────────────────────────┘
```

**注意**：云端和本地是**两套独立的环境**，各自有完整的组件，通过 IP:Port 互相挂载。

---

## 2. 快速开始

### 2.1 启动顺序

```
┌─────────────────────────────────────────────────────────┐
│  步骤1          步骤2            步骤3           步骤4   │
│  大模型    →   OpenCode    →   Gateway    →   WebUI    │
│  (llama.cpp)   (ACP+TUI)     (API网关)      (浏览器)    │
└─────────────────────────────────────────────────────────┘
```

### 2.2 启动命令

#### 步骤 1: 启动大模型 (llama.cpp)

```bash
# 3080 GPU 服务器
$HOME/llama.cpp/build/bin/llama-server \
  -m /opt/image/Model-7.6B-Q4_K_M.gguf \
  --mmproj /opt/image/mmproj-model-f16.gguf \
  --host 0.0.0.0 \
  --port 11434 \
  -ngl 99 \
  -c 8192 \
  --batch-size 256 \
  --flash-attn on \
  --threads 12 \
  --parallel 1 \
  --n-predict 4096
```

**参数说明**：
| 参数 | 说明 |
|------|------|
| `-m` | 模型文件路径 |
| `--mmproj` | 多模态投影文件 (MiniCPM 必需) |
| `-ngl 99` | GPU 层数 (全部使用 GPU) |
| `-c 8192` | 上下文长度 |
| `--flash-attn on` | 启用 Flash Attention |

### 2.3 大模型介绍: MiniCPM-o 2.6

> **MiniCPM-o 2.6** 是本系统使用的核心多模态大模型，被称为"端侧 GPT-4o"

#### 模型基本信息

| 属性 | 值 |
|------|-----|
| **模型名称** | MiniCPM-o 2.6 |
| **参数量** | 8B (80亿) |
| **开发团队** | 面壁智能 (OpenBMB) |
| **发布时间** | 2025年1月 |
| **开源地址** | [GitHub](https://github.com/OpenBMB/MiniCPM-o) |

#### 核心能力

| 能力 | 说明 | 水平 |
|------|------|------|
| **视觉理解** | 支持任意长宽比图像，像素可达180万 (1344×1344) | 超越 GPT-4o |
| **实时语音** | 双语实时对话，支持30+语言 | 开源SOTA |
| **视频理解** | 实时视频流分析 | GPT-4o级别 |
| **语音生成** | 可配置声音、情感、语速、风格控制 | 开源SOTA |
| **声音克隆** | 端到端声音克隆 | 支持 |
| **多模态流式** | 连续视频+音频流实时交互 | 首个开源 |

#### 技术亮点

- **端到端全模态架构**: 文本、图像、音频、视频统一输入输出
- **高效推理**: 处理180万像素图像仅需640 tokens，比同类少75%
- **端侧运行**: 首个可在 iPad 等设备上实时流式交互的多模态模型
- **GGUF量化**: 提供 Q4/Q5/Q6/Q8 量化版本，适配不同硬件

#### 本系统使用版本

| 文件 | 说明 |
|------|------|
| `/opt/image/Model-7.6B-Q4_K_M.gguf` | 量化模型 (7.6GB) |
| `/opt/image/mmproj-model-f16.gguf` | 多模态投影器 |

#### 相关项目

- [MiniCPM-o 官方](https://github.com/OpenBMB/MiniCPM-o)
- [HuggingFace](https://huggingface.co/openbmb/MiniCPM-o-2_6)

#### 步骤 2: 启动 OpenCode (tmux)

```bash
# 方式1: 使用脚本 (推荐)
cd /home/dministrator/Friday
./start_opencode.sh

# 方式2: 手动启动
tmux new-session -s opencode -n "acp"
tmux send-keys "opencode serve --port 4096 --hostname 0.0.0.0" C-m

# 新窗口 attach
tmux new-window -t opencode -n "attach"
tmux send-keys "sleep 2 && opencode attach http://localhost:4096" C-m
```

#### 步骤 3: 启动 Gateway + Worker

```bash
# 终端1: 启动 Gateway (同时提供 WebUI)
cd /home/dministrator/Friday
python gateway.py --port 10024 --workers localhost:22400

# 终端2: 启动 Worker
cd /home/dministrator/Friday
python worker.py --port 22400
```

#### 步骤 4: 访问 WebUI

```bash
# Gateway 启动后，直接用浏览器访问
http://localhost:10024

# 或访问特定页面
http://localhost:10024/omni/omni.html          # 全能模式
http://localhost:10024/half-duplex/            # 半双工
http://localhost:10024/audio-duplex/           # 音频双工
http://localhost:10024/duplex/                 # 视频双工
```

---

## 3. 语音识别 (Faster-Whisper)

### 3.1 安装

```bash
pip install faster-whisper -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 3.2 模型下载

模型路径: `/opt/image/faster-whisper-large-v3`

如需下载新模型:
```python
from faster_whisper import WhisperModel
# 首次使用会自动下载到默认目录
model = WhisperModel("large-v3")
```

### 3.3 测试识别

```bash
python -c "
import sys
sys.path.insert(0, '/home/dministrator/Friday')
from faster_whisper import WhisperModel

model = WhisperModel('/opt/image/faster-whisper-large-v3', device='cuda', compute_type='float16')
segments, info = model.transcribe('/home/dministrator/video/voice.wav', language='zh', beam_size=5, vad_filter=True)

text = ''
for segment in segments:
    text += segment.text.strip()

print('识别结果:', text)
"
```

参数说明:
- `language="zh"` - 指定中文，其他语言可省略
- `beam_size=5` - 束搜索宽度，越大越准确
- `vad_filter=True` - 启用语音活动检测，过滤噪音
- `device="cuda"` - 使用 GPU 加速
- `compute_type="float16"` - 半精度，更快

---

## 4. tmux 使用指南

### 3.1 启动 tmux 会话

```bash
# 使用脚本启动 (推荐)
cd /home/dministrator/Friday
./start_opencode.sh
```

### 3.2 tmux 快捷键

| 快捷键 | 功能 |
|--------|------|
| `tmux attach -t opencode` | 进入 OpenCode 会话 |
| `Ctrl+b d` | 退出 tmux (不关闭窗口) |
| `Ctrl+b 0` | 切换到第 1 个窗口 (acp) |
| `Ctrl+b 1` | 切换到第 2 个窗口 (attach) |
| `Ctrl+b n` | 切换到下一个窗口 |
| `Ctrl+b p` | 切换到上一个窗口 |
| `Ctrl+b w` | 列出所有窗口 |
| `Ctrl+b ,` | 重命名当前窗口 |
| `Ctrl+b %` | 垂直分屏 |
| `Ctrl+b "` | 水平分屏 |
| `Ctrl+b o` | 切换窗格 |
| `Ctrl+b x` | 关闭当前窗格 |
| `Ctrl+b [` | 进入复制/滚动模式 (按 q 退出) |

### 3.3 opencode attach 远程连接

```bash
# 本地 attach 到云端
opencode attach http://<云端IP>:4096

# 云端 attach 到本地
opencode attach http://<本地IP>:4096
```

---

## 4. 钉钉机器人集成

### 4.1 钉钉机器人目录

```
/home/dministrator/my-game/scripts/autobot/
```

### 4.2 架构

```
钉钉消息 
  → autobot_dingtalk.py (消息分发)
    → 图片消息 → ai_analyze
    → #opencode 指令 → OpenCode 执行
    → 文字消息 → AI 对话 + 生图
      → task_worker.py 执行
```

### 4.3 启动命令

```bash
# 终端1: 启动钉钉机器人
python /home/dministrator/my-game/scripts/autobot/autobot_dingtalk.py

# 终端2: 启动 Worker
python /home/dministrator/my-game/scripts/autobot/task_worker.py
```

### 4.4 钉钉指令

| 指令 | 功能 |
|------|------|
| `#opencode <指令>` | 调用 OpenCode 执行 |
| 普通文字 | AI 对话 + 生图 |
| 图片 | AI 图片分析 |

---

## 5. 代码向量搜索 (Code Search)

### 5.1 简介

基于 **LanceDB + OpenCode MCP** 的本地代码语义检索，解决大模型知识陈旧和幻觉问题。

### 5.2 配置

在 `/home/dministrator/.config/opencode/opencode.json` 中配置：

```json
{
  "mcp": {
    "code-search": {
      "type": "local",
      "command": ["python3", "/home/dministrator/my-agent/code_ai_tools/mcp_lancedb_server.py"],
      "enabled": true
    }
  }
}
```

### 5.3 使用方式

```bash
# 1. 索引项目
python3 ~/my-agent/code_ai_tools/index_lancedb.py <代码路径> <项目ID>

# 2. 启动 MCP 服务
python3 ~/my-agent/code_ai_tools/mcp_lancedb_server.py

# 3. OpenCode 自动调用
# 问: "UNet前向传播实现在哪里"
# → MCP search_code → 向量检索 → 返回结果
```

---

## 6. 使用场景

### 6.1 语音对话 (本地)

```bash
# 启动语音助手
cd /home/dministrator/Friday
python jarvis.py

# 或者只发送文字
python jarvis.py -t "帮我写一个排序算法"
```

### 6.2 视频对话 (WebUI)

```
浏览器访问 http://localhost:10024/omni/omni.html
```

### 6.3 远程控制 (钉钉)

```
手机打开钉钉 → 发送 #opencode 帮我重启服务
```

---

## 7. 项目结构

```
/home/dministrator/Friday/
├── gateway.py              # API 网关 + WebUI 服务器
├── worker.py               # 推理 Worker
├── jarvis.py               # 语音助手 CLI
├── start_opencode.sh       # OpenCode 启动脚本 (tmux)
├── config.py               # 配置管理
├── static/                 # WebUI 静态文件
│   ├── omni/               # 全能模式
│   ├── half-duplex/        # 半双工
│   ├── audio-duplex/       # 音频双工
│   └── duplex/             # 视频双工
├── core/                   # 核心处理器
│   └── processors/         # 推理处理器
└── docs/                  # 文档
```

---

## 8. 附录

### 8.1 端口说明

| 端口 | 服务 |
|------|------|
| 11434 | llama.cpp 大模型 API |
| 4096 | OpenCode ACP 服务器 |
| 10024 | Gateway + WebUI |
| 22400 | Worker |

### 8.2 常用命令

```bash
# 查看 tmux 会话
tmux ls

# 杀掉 tmux 会话
tmux kill-session -t opencode

# 查看进程
ps aux | grep llama-server
ps aux | grep opencode
ps aux | grep gateway.py

# 查看日志
tail -f /tmp/autobot_tasks/result.json
```

### 8.3 相关路径

| 组件 | 路径 |
|------|------|
| 大模型脚本 | `~/my-shell/3080/run_minicpm.sh` |
| 钉钉机器人 | `~/my-game/scripts/autobot/` |
| 代码向量搜索 | `~/my-agent/code_ai_tools/` |
| OpenCode 配置 | `~/.config/opencode/opencode.json` |
| OpenCode 插件 | `~/.agent/skills/` |

### 8.4 WSL2 端口映射 (Windows 宿主机访问)

WSL2 Ubuntu 运行在 Windows 宿主机上的虚拟机中，Windows 浏览器无法直接访问 WSL2 内部服务。需要通过 **端口映射 (Port Proxy)** 将 Windows 端口转发到 WSL2 Ubuntu 实例。

**逻辑说明**：
```
Windows 浏览器 localhost:10024 
    → 转发到 → WSL2 Ubuntu 172.23.212.172:10024
```

**WSL2 Ubuntu IP**: `172.23.212.172` (可通过 `hostname -I` 查看)

```powershell
# 在 Windows 管理员 PowerShell 中执行
# 格式: netsh interface portproxy add v4tov4 listenport=Windows端口 connectaddress=WSL2_IP connectport=WSL2端口

# 映射 Gateway WebUI (10024)
netsh interface portproxy add v4tov4 listenport=10024 connectaddress=172.23.212.172 connectport=10024

# 映射 OpenCode ACP (4096)
netsh interface portproxy add v4tov4 listenport=4096 connectaddress=172.23.212.172 connectport=4096

# 映射 llama.cpp 大模型 (11434)
netsh interface portproxy add v4tov4 listenport=11434 connectaddress=172.23.212.172 connectport=11434

# 查看已映射的端口
netsh interface portproxy show all

# 删除端口映射
netsh interface portproxy delete v4tov4 listenport=10024
```

```powershell
# 方法2: PowerShell 管理员 (推荐)
# 同样效果
netsh interface portproxy add v4tov4 listenport=10024 connectport=10024 connectaddress=localhost
```

**访问方式 (Windows 浏览器)**：

| 服务 | 地址 |
|------|------|
| WebUI | http://localhost:10024/omni/omni.html |
| OpenCode | http://localhost:4096 |
| 大模型 API | http://localhost:11434 |

**注意**：以上命令需要在 **Windows 管理员 PowerShell** 中执行，不是 WSL2 里面！

---

**这就是你的贾维斯 - 随时随地为你服务的 AI 助手！** 🤖
