# Friday - llama.cpp-omni 全双工部署任务

> 硬件: RTX 4090 D, 24GB | 状态: 部署中

## 任务进度表

| 序号 | 任务 | 状态 | 完成时间 |
|------|------|------|----------|
| 1 | 创建任务进度表 task.md | ✅ | 2026-04-06 |
| 2 | 克隆 llama.cpp-omni 项目到 /opt/llama.cpp-omni | ✅ | 2026-04-06 |
| 3 | 编译 llama.cpp-omni (CUDA 支持) | ✅ | 2026-04-06 |
| 4 | 下载 MiniCPM-o-4_5 模型文件 (~8.3GB) | ✅ | 2026-04-06 |
| 5 | 部署全双工服务 | ✅ | 2026-04-06 |
| 6 | 验证部署 (浏览器访问 http://localhost:8088) | ✅ | 2026-04-06 |

## 环境信息

- **GPU**: NVIDIA GeForce RTX 4090 D (24GB)
- **llama.cpp-omni**: /opt/llama.cpp-omni
- **模型目录**: /opt/gguf/MiniCPM-o-4_5
- **WebRTC Demo**: /opt/WebRTC_Demo

## 已完成

- ✅ llama.cpp-omni 编译完成 (`/opt/llama.cpp-omni/build/bin/llama-server`)
- ✅ MiniCPM-o-4_5 模型下载完成 (`/opt/gguf/MiniCPM-o-4_5`)
- ✅ WebRTC Demo 已克隆 (`/opt/WebRTC_Demo`)

## 部署命令

### 双工模式 (duplex) - 推荐

```bash
cd /opt/WebRTC_Demo
./deploy_all.sh \
    --cpp-dir /opt/llama.cpp-omni \
    --model-dir /opt/gguf/MiniCPM-o-4_5 \
    --duplex
```

### 单工模式 (simplex)

```bash
cd /opt/WebRTC_Demo
./deploy_all.sh \
    --cpp-dir /opt/llama.cpp-omni \
    --model-dir /opt/gguf/MiniCPM-o-4_5
```

### 步骤 5: 访问

启动完成后浏览器打开: **https://localhost:8088**

## 服务端口

| 服务 | 端口 | 说明 |
|------|------|------|
| Frontend | 3000/8088 | Web UI |
| Backend | 8025 | 后端 API |
| LiveKit | 7880 | 实时通信 |
| Inference | 9060 | C++ HTTP API |

## 模型文件结构

```
/opt/image/MiniCPM-o-4_5-GGUF/
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
