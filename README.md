# Friday - 本地贾维斯 AI 助手系统

> 类似钢铁侠的贾维斯 (JARVIS)，支持语音、视频、手机远程控制
> 
> **最新更新**: 新增分离架构版本，支持 RTX 3080 10GB 显存运行！

---

## 🆕 新增: Friday AI 助手分离架构

针对 **RTX 3080 10GB 显存** 优化的轻量化版本，采用分离架构实现多模态 AI 助手：

### 技术方案

| 模块 | 技术方案 | 显存占用 | 功能 |
|------|----------|----------|------|
| **视觉+文本** | MiniCPM-V-2_6 (GGUF Q4_K_M) | ~6GB | 图片理解、文本对话 |
| **语音识别** | SenseVoice (本地 ASR) | CPU | 语音转文字 |
| **语音合成** | CosyVoice (本地 TTS) | ~2GB | 文字转语音 |
| **Web界面** | FastAPI + WebSocket | - | 实时语音视频对话 |

**总显存占用**: ~8GB (适合 RTX 3080 10GB)

### 架构图

```
用户语音 → SenseVoice ASR → 文本 → MiniCPM-V-2_6 → 文本回复 → CosyVoice TTS → 语音播放
                ↑                                              ↓
         [WebSocket 实时通信]                          [FastAPI Gateway]
                ↑                                              ↓
         浏览器 (摄像头+麦克风) ←────────────────────────── WebUI
```

### 快速开始

#### 1. 启动模型服务

```bash
# 启动 MiniCPM-V-2_6 (llama.cpp)
~/llama.cpp/build/bin/llama-server \
  -m /opt/image/OpenBMB/MiniCPM-V-2_6-gguf/ggml-model-Q4_K_M.gguf \
  --mmproj /opt/image/OpenBMB/MiniCPM-V-2_6-gguf/mmproj-model-f16.gguf \
  --port 11434 -ngl 99

# 启动 SenseVoice (语音识别)
~/SenseVoice.cpp/bin/sense-voice-server -p 11435

# 启动 CosyVoice (语音合成)
conda activate cosyvoice
cd ~/CosyVoice
python cosyvoice_server.py --port 11436
```

#### 2. 启动 Friday Gateway

```bash
cd /home/dministrator/Friday
python gateway_simple.py
```

#### 3. 访问 WebUI

浏览器打开: **http://localhost:10024/static/chat.html**

### 功能特性

✅ **语音对话** - 按住麦克风说话，自动识别并语音回复  
✅ **文字聊天** - 支持多轮对话，Shift+Enter 换行  
✅ **图片理解** - 开启摄像头或上传图片，AI 实时分析  
✅ **实时通信** - WebSocket 双向通信，低延迟  
✅ **现代化界面** - 响应式设计，支持移动端

### 脚本使用方式

| 脚本 | 用途 | 命令 |
|------|------|------|
| `start_friday.sh` | 简单启动 llama-mtmd-cli 交互模式 | `./start_friday.sh` |
| `start_friday_complete.sh` | 启动完整 API 服务 | `./start_friday_complete.sh` |
| `stop_friday.sh` | 停止所有服务 | `./stop_friday.sh` |
| `test_friday.sh` | 测试 API 功能 | `./test_friday.sh` |

### 文件说明

```
/home/dministrator/Friday/
├── gateway_simple.py           # FastAPI 主服务 (WebSocket + REST API)
├── modules/
│   ├── llama_client.py         # MiniCPM-V-2_6 客户端
│   ├── sensevoice_client.py    # 语音识别客户端
│   └── cosyvoice_client.py     # 语音合成客户端
├── static/
│   ├── chat.html               # WebUI 主页面
│   ├── css/chat.css            # 样式文件
│   └── js/
│       ├── audio.js            # 音频处理 (录音/播放/可视化)
│       ├── vision.js           # 摄像头/图片处理
│       ├── websocket.js        # WebSocket 通信
│       └── app.js              # 主应用逻辑
└── docs/
    ├── design.md               # 详细设计方案
    └── task.md                 # 开发任务列表
```

---

## 1. 系统架构 (原版 MiniCPM-o 4.5)

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

### 2.3 大模型介绍: MiniCPM-o 4.5

> **MiniCPM-o 4.5** 是本系统使用的核心多模态大模型，被称为"端侧 GPT-4o"，2026年2月发布

#### 模型基本信息

| 属性 | 值 |
|------|-----|
| **模型名称** | MiniCPM-o 4.5 |
| **参数量** | 9B (90亿) |
| **开发团队** | 面壁智能 (OpenBMB) |
| **发布时间** | 2026年2月 |
| **开源地址** | [GitHub](https://github.com/OpenBMB/MiniCPM-o) |

#### 核心能力

| 能力 | 说明 | 水平 |
|------|------|------|
| **视觉理解** | 支持任意长宽比图像，高达180万像素 | 接近 Gemini 2.5 Flash |
| **实时语音** | 双语实时对话，支持30+语言 | 开源SOTA |
| **视频理解** | 实时视频流分析 | 接近 Gemini 2.5 Flash |
| **语音生成** | 可配置声音、情感、语速、风格控制 | 超越 CosyVoice2 |
| **声音克隆** | 端到端声音克隆，简单参考音频即可 | 超越 CosyVoice2 |
| **全双工交互** | 边看边听边说，可主动发起提醒 | 首个开源 |
| **OCR** | 高精度文档解析 | 超越 GPT-5、Gemini-3 |

#### 技术亮点

- **端到端全模态架构**: 文本、图像、音频、视频统一输入输出
- **全双公实时流**: 输入输出互不阻塞，真正的实时对话
- **高效推理**: int4 量化仅需 11GB 显存，推理速度 212 tokens/s
- **端侧运行**: 首个可在 Mac/iPad 等设备上实时流式交互的多模态模型
- **GGUF量化**: 提供多种量化版本，适配不同硬件

#### 本系统使用版本

| 文件 | 说明 |
|------|------|
| `/opt/image/Model-7.6B-Q4_K_M.gguf` | 量化模型 (4.4GB) |
| `/opt/image/mmproj-model-f16.gguf` | 多模态投影器 |

#### 进阶玩法 (官方文档)

更多高级用法请参考 [MiniCPM-o 官方文档](https://github.com/OpenBMB/MiniCPM-o/blob/main/README_zh.md)：

- **声音克隆**: 通过简单的参考音频实现声音克隆和角色扮演
- **情感控制**: 控制生成语音的情感、语速、风格
- **多框架支持**: llama.cpp、Ollama、vLLM、SGLang 部署
- **本地 Demo**: WebRTC 实时视频对话 Demo

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

## 9. llama.cpp-omni 全双工部署 (WebRTC Demo)

> 基于 [llama.cpp-omni](https://github.com/tc-mb/llama.cpp-omni) + WebRTC 实现全双工实时视频交互，支持量化版本

### 9.1 硬件要求

| 显卡 | 显存 | 单工 | 双工 | 说明 |
|------|------|------|------|------|
| RTX 4060 | 8GB | ❌ | ❌ | 显存不足 |
| RTX 3060 | 12GB | ✅ | ⚠️ 勉强 | 部分模块需 CPU offload |
| RTX 4070 | 12GB | ✅ | ✅ | 双工入门级 |
| RTX 4080 | 16GB | ✅ | ✅ | 推荐配置 |
| RTX 3090/4090 | 24GB | ✅ | ✅ | 充裕/最佳 |

**3080 10GB**: 不在官方支持列表，可尝试

### 9.2 模型文件 (~8.3GB)

```
<MODEL_DIR>/
├── MiniCPM-o-4_5-Q4_K_M.gguf        # LLM 主模型 (~5GB)
├── audio/
│   └── MiniCPM-o-4_5-audio-F16.gguf  # 音频编码器
├── vision/
│   └── MiniCPM-o-4_5-vision-F16.gguf # 视觉编码器
├── tts/
│   ├── MiniCPM-o-4_5-tts-F16.gguf    # TTS 模型
│   └── MiniCPM-o-4_5-projector-F16.gguf
└── token2wav-gguf/                   # Token2Wav 模型
    ├── encoder.gguf
    ├── flow_matching.gguf
    ├── flow_extra.gguf
    ├── hifigan2.gguf
    └── prompt_cache.gguf
```

### 9.3 部署步骤

#### 步骤 1: 克隆项目

```bash
git clone https://github.com/tc-mb/llama.cpp-omni.git
cd llama.cpp-omni
```

#### 步骤 2: 编译 (CUDA 支持)

```bash
cmake -B build -DCMAKE_BUILD_TYPE=Release -DGGML_CUDA=ON
cmake --build build --target llama-server -j
```

验证编译:
```bash
ls -la build/bin/llama-server
```

#### 步骤 3: 下载模型 (~8.3GB)

```bash
cd /home/dministrator/Friday/WebRTC_Demo

# 使用 HuggingFace 镜像 (国内推荐)
./download_models.sh --model-dir /opt/image/MiniCPM-o-4_5-GGUF --hf-mirror https://hf-mirror.com

# 或使用 ModelScope (国内更快)
./download_models.sh --model-dir /opt/image/MiniCPM-o-4_5-GGUF --source ms
```

#### 步骤 4: 一键启动

```bash
cd /home/dministrator/Friday/WebRTC_Demo

# 单工模式
./deploy_all.sh \
    --cpp-dir /path/to/llama.cpp-omni \
    --model-dir /opt/image/MiniCPM-o-4_5-GGUF

# 双工模式
./deploy_all.sh \
    --cpp-dir /path/to/llama.cpp-omni \
    --model-dir /opt/image/MiniCPM-o-4_5-GGUF \
    --duplex
```

#### 步骤 5: 访问

启动完成后浏览器打开: **https://localhost:8088**

### 9.4 服务端口

| 服务 | 端口 | 说明 |
|------|------|------|
| Frontend | 3000/8088 | Web UI |
| Backend | 8025 | 后端 API |
| LiveKit | 7880 | 实时通信 |
| Inference | 9060 | C++ HTTP API |

### 9.5 量化版本选择

可选 LLM 量化: `Q4_0`, `Q4_1`, `Q4_K_M` (推荐), `Q4_K_S`, `Q5_0`, `Q5_1`, `Q5_K_M`, `Q5_K_S`, `Q6_K`, `Q8_0`, `F16`

下载时指定:
```bash
./download_models.sh --model-dir /opt/image/MiniCPM-o-4_5-GGUF --quant Q4_K_M
```

### 9.6 相关资源

- [llama.cpp-omni](https://github.com/tc-mb/llama.cpp-omni)
- [WebRTC Demo 文档](https://github.com/OpenSQZ/MiniCPM-V-CookBook/blob/main/demo/web_demo/WebRTC_Demo/README_zh.md)
- [MiniCPM-o 4.5 模型](https://huggingface.co/openbmb/MiniCPM-o-4_5)

---

**这就是你的贾维斯 - 随时随地为你服务的 AI 助手！** 🤖
