# Friday - 本地贾维斯 AI 助手系统

> 类似钢铁侠的贾维斯 (JARVIS)，支持语音、视频、手机远程控制
> 
> **针对 RTX 3080 10GB 显存优化**，采用分离架构实现多模态 AI 助手

---

## 系统架构

针对 **RTX 3080 10GB 显存** 优化的轻量化版本：

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

---

## 快速开始

### 1. 启动模型服务

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

### 2. 启动 Friday Gateway

```bash
cd /home/dministrator/Friday
python gateway_simple.py
```

### 3. 访问 WebUI

浏览器打开: **http://localhost:10024/static/chat.html**

---

## 功能特性

✅ **语音对话** - 按住麦克风说话，自动识别并语音回复  
✅ **文字聊天** - 支持多轮对话，Shift+Enter 换行  
✅ **图片理解** - 开启摄像头或上传图片，AI 实时分析  
✅ **实时通信** - WebSocket 双向通信，低延迟  
✅ **现代化界面** - 响应式设计，支持移动端

---

## 脚本使用方式

| 脚本 | 用途 | 命令 |
|------|------|------|
| `start_friday.sh` | 简单启动 llama-mtmd-cli 交互模式 | `./start_friday.sh` |
| `start_friday_complete.sh` | 启动完整 API 服务 | `./start_friday_complete.sh` |
| `stop_friday.sh` | 停止所有服务 | `./stop_friday.sh` |
| `test_friday.sh` | 测试 API 功能 | `./test_friday.sh` |

---

## 项目结构

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
├── docs/
│   ├── design.md               # 详细设计方案
│   └── task.md                 # 开发任务列表
├── start_friday.sh             # 启动脚本
├── stop_friday.sh              # 停止脚本
└── test_friday.sh              # 测试脚本
```

---

## 技术方案

### MiniCPM-V-2_6

- **模型**: MiniCPM-V-2_6 (8B 参数)
- **量化**: Q4_K_M GGUF (4.68GB)
- **功能**: 视觉理解 + 文本对话
- **显存**: ~6GB

### SenseVoice

- **功能**: 语音识别 (ASR)
- **运行**: CPU
- **输入**: 16kHz, 16bit, 单声道 PCM

### CosyVoice

- **模型**: CosyVoice-300M-SFT
- **功能**: 语音合成 (TTS)
- **显存**: ~2GB

---

## 端口说明

| 端口 | 服务 | 说明 |
|------|------|------|
| 11434 | llama.cpp | MiniCPM-V-2_6 API |
| 11435 | SenseVoice | 语音识别 API |
| 11436 | CosyVoice | 语音合成 API |
| 10024 | Gateway | WebUI + WebSocket |

---

## 模型下载

### MiniCPM-V-2_6 GGUF

```bash
# 使用 ModelScope (国内推荐)
python -c "
from modelscope import snapshot_download
model_dir = snapshot_download('OpenBMB/MiniCPM-V-2_6-gguf', cache_dir='/opt/image')
print(f'Downloaded to: {model_dir}')
"
```

### SenseVoice

```bash
# 编译 SenseVoice.cpp
cd ~/SenseVoice.cpp
mkdir build && cd build
cmake -DGGML_CUDA=ON ..
make -j
```

### CosyVoice

```bash
# 使用 ModelScope
python -c "
from modelscope import snapshot_download
snapshot_download('FunAudioLLM/CosyVoice-300M-SFT', local_dir='/opt/image/CosyVoice-300M-SFT')
"
```

---

## 开发文档

- [design.md](docs/design.md) - 详细设计方案
- [task.md](docs/task.md) - 开发任务列表

---

## 相关项目

- [MiniCPM-V](https://github.com/OpenBMB/MiniCPM-V) - 视觉语言模型
- [SenseVoice](https://github.com/FunAudioLLM/SenseVoice) - 语音识别
- [CosyVoice](https://github.com/FunAudioLLM/CosyVoice) - 语音合成
- [llama.cpp](https://github.com/ggerganov/llama.cpp) - 模型推理

---

**这就是你的贾维斯 - 随时随地为你服务的 AI 助手！** 🤖
