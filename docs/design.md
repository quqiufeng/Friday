# Friday AI 助手 - 分离架构设计方案

## 项目概述
基于 RTX 3080 10GB 显存限制，采用分离架构实现多模态 AI 助手：
- **视觉理解**: MiniCPM-V-2_6 (4.68GB Q4_K_M GGUF)
- **语音识别**: SenseVoice (本地 ASR)
- **语音合成**: CosyVoice (本地 TTS)
- **Web界面**: 支持摄像头、麦克风、实时对话

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                      Web 前端 (浏览器)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   摄像头     │  │   麦克风     │  │   扬声器     │       │
│  │  (WebRTC)    │  │  (WebRTC)    │  │  (Web Audio) │       │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘       │
└─────────┼─────────────────┼─────────────────┼───────────────┘
          │                 │                 │
          ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Web 服务 (Gateway)                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  /api/chat   │  │ /api/vision  │  │  /api/audio  │       │
│  │  文本对话    │  │  图片理解    │  │  语音处理    │       │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘       │
└─────────┼─────────────────┼─────────────────┼───────────────┘
          │                 │                 │
          ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────┐
│                      AI 模型层                               │
│  ┌──────────────────┐  ┌──────────────────┐                 │
│  │ MiniCPM-V-2_6    │  │   SenseVoice     │                 │
│  │ (llama.cpp)      │  │   (语音识别)      │                 │
│  │ 显存: ~6GB       │  │   CPU/GPU        │                 │
│  └──────────────────┘  └──────────────────┘                 │
│  ┌──────────────────┐                                        │
│  │   CosyVoice      │                                        │
│  │   (语音合成)      │                                        │
│  │   显存: ~2GB     │                                        │
│  └──────────────────┘                                        │
└─────────────────────────────────────────────────────────────┘
```

## 技术栈

### 前端
- **框架**: HTML5 + JavaScript (原生)
- **实时通信**: WebSocket (与后端双向通信)
- **媒体捕获**: WebRTC getUserMedia API
- **音频处理**: Web Audio API

### 后端
- **框架**: FastAPI (Python)
- **WebSocket**: 实时语音流处理
- **模型推理**: 
  - llama.cpp (MiniCPM-V-2_6 GGUF)
  - SenseVoice.cpp (语音识别)
  - CosyVoice (语音合成)

### 模型配置

| 模型 | 路径 | 显存占用 | 功能 |
|------|------|----------|------|
| MiniCPM-V-2_6 | `/opt/image/OpenBMB/MiniCPM-V-2_6-gguf` | ~6GB | 视觉+文本 |
| SenseVoice | `~/SenseVoice.cpp` | CPU | 语音识别 |
| CosyVoice | `/opt/image/CosyVoice-300M-SFT` | ~2GB | 语音合成 |

**总显存占用**: ~8GB (在 RTX 3080 10GB 范围内)

## 核心功能

### 1. 语音对话模式
```
用户说话 → 麦克风采集 → SenseVoice ASR → 文本
                                        ↓
扬声器播放 ← CosyVoice TTS ← 文本回复 ← MiniCPM-V-2_6
```

### 2. 视觉理解模式
```
摄像头捕获 → 图片 → MiniCPM-V-2_6 视觉理解 → 文本回复
```

### 3. 多模态模式
```
摄像头 + 麦克风同时输入
        ↓
图片 → MiniCPM-V-2_6
文本 → MiniCPM-V-2_6 (作为问题)
        ↓
    文本回复
        ↓
CosyVoice TTS → 语音播放
```

## API 设计

### WebSocket 端点
```
ws://localhost:10024/ws/chat
```

**消息格式**:
```json
// 客户端 → 服务端 (语音数据)
{
  "type": "audio_chunk",
  "data": "base64_encoded_audio_pcm"
}

// 服务端 → 客户端 (识别结果)
{
  "type": "asr_result",
  "text": "用户说的话"
}

// 服务端 → 客户端 (AI 回复)
{
  "type": "ai_response",
  "text": "AI 回复文本",
  "audio": "base64_encoded_wav"
}

// 客户端 → 服务端 (图片)
{
  "type": "image",
  "data": "base64_encoded_jpg"
}
```

### REST API
```
POST /api/chat              # 文本对话
POST /api/vision            # 图片理解
POST /api/asr               # 语音识别 (文件上传)
POST /api/tts               # 语音合成
GET  /health                # 健康检查
```

## 文件结构

```
/home/dministrator/Friday/
├── gateway.py              # 主服务 (FastAPI + WebSocket)
├── static/
│   ├── index.html          # WebUI 主页面
│   ├── css/
│   │   └── style.css       # 样式
│   └── js/
│       ├── app.js          # 主应用逻辑
│       ├── audio.js        # 音频处理 (录音/播放)
│       ├── vision.js       # 摄像头处理
│       └── websocket.js    # WebSocket 通信
├── modules/
│   ├── llama_client.py     # llama.cpp 客户端
│   ├── sensevoice_client.py # SenseVoice 客户端
│   └── cosyvoice_client.py  # CosyVoice 客户端
├── scripts/
│   ├── start_friday.sh     # 启动脚本
│   └── stop_friday.sh      # 停止脚本
└── docs/
    ├── design.md           # 本文件
    └── task.md             # 任务列表
```

## 启动流程

1. **启动 llama.cpp 服务** (MiniCPM-V-2_6)
   ```bash
   llama-server -m model.gguf --mmproj mmproj.gguf --port 11434
   ```

2. **启动 SenseVoice 服务**
   ```bash
   sense-voice-server -m sense-voice.gguf --port 11435
   ```

3. **启动 CosyVoice 服务**
   ```bash
   python cosyvoice_server.py --port 11436
   ```

4. **启动 Gateway**
   ```bash
   python gateway.py --port 10024
   ```

5. **打开浏览器**
   ```
   https://localhost:10024
   ```

## 性能指标

| 指标 | 目标值 |
|------|--------|
| 语音识别延迟 | < 500ms |
| 文本生成延迟 | < 2s (首token) |
| 语音合成延迟 | < 1s |
| 端到端延迟 | < 3s |
| 并发用户 | 1 (本地使用) |

## 注意事项

1. **HTTPS 必需**: 浏览器要求 HTTPS 才能访问摄像头和麦克风
2. **显存管理**: 总显存占用控制在 8GB 以内
3. **模型预热**: 首次推理较慢，建议启动后预热
4. **音频格式**: 统一使用 16kHz, 16bit, 单声道 PCM

## 扩展计划

- [ ] 支持多语言 (中文/英文切换)
- [ ] 支持声音克隆 (CosyVoice 3s 极速克隆)
- [ ] 支持实时字幕显示
- [ ] 支持对话历史保存
- [ ] 支持移动端访问
