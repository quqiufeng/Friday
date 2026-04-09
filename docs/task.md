# Friday AI 助手开发任务列表

## 任务总览
- [ ] 阶段1: 环境准备与模型部署 (预计2小时)
- [ ] 阶段2: 后端API开发 (预计3小时)
- [ ] 阶段3: 前端WebUI开发 (预计3小时)
- [ ] 阶段4: 集成测试与优化 (预计2小时)

---

## 阶段1: 环境准备与模型部署

### 1.1 检查并启动 llama.cpp 服务
- [ ] 确认 MiniCPM-V-2_6 GGUF 模型文件完整
  - 检查 `/opt/image/OpenBMB/MiniCPM-V-2_6-gguf/ggml-model-Q4_K_M.gguf`
  - 检查 `/opt/image/OpenBMB/MiniCPM-V-2_6-gguf/mmproj-model-f16.gguf`
- [ ] 编写 llama-server 启动脚本
- [ ] 测试 llama-server API 是否正常
- **状态**: pending

### 1.2 部署 SenseVoice 语音识别
- [ ] 检查 SenseVoice.cpp 是否已编译
  - 检查 `~/SenseVoice.cpp/build/bin/sense-voice-server`
- [ ] 下载 SenseVoice 模型 (如需要)
- [ ] 编写 SenseVoice 启动脚本
- [ ] 测试语音识别功能
- **状态**: pending

### 1.3 部署 CosyVoice 语音合成
- [ ] 检查 CosyVoice 环境
  - 检查 conda 环境 `cosyvoice`
  - 检查模型 `/opt/image/CosyVoice-300M-SFT`
- [ ] 编写 CosyVoice API 服务
- [ ] 测试语音合成功能
- **状态**: pending

---

## 阶段2: 后端API开发

### 2.1 创建 Gateway 服务框架
- [ ] 创建 `gateway.py` FastAPI 应用
- [ ] 配置 CORS 和 HTTPS
- [ ] 实现健康检查端点 `/health`
- **状态**: pending

### 2.2 实现模型客户端模块
- [ ] `modules/llama_client.py` - llama.cpp HTTP 客户端
- [ ] `modules/sensevoice_client.py` - SenseVoice 客户端
- [ ] `modules/cosyvoice_client.py` - CosyVoice 客户端
- **状态**: pending

### 2.3 实现 REST API
- [ ] `POST /api/chat` - 文本对话
- [ ] `POST /api/vision` - 图片理解
- [ ] `POST /api/asr` - 语音识别 (文件上传)
- [ ] `POST /api/tts` - 语音合成
- **状态**: pending

### 2.4 实现 WebSocket 实时通信
- [ ] `ws://localhost:10024/ws/chat`
- [ ] 处理音频流 (分块接收)
- [ ] 实现 ASR 实时识别
- [ ] 实现 AI 回复流式返回
- [ ] 实现 TTS 语音流发送
- **状态**: pending

---

## 阶段3: 前端WebUI开发

### 3.1 创建基础页面
- [ ] `static/index.html` - 主页面结构
- [ ] `static/css/style.css` - 样式美化
- **状态**: pending

### 3.2 实现音频处理模块
- [ ] `static/js/audio.js`
  - 麦克风权限获取
  - 音频录制 (Web Audio API)
  - 音频播放
  - 音频格式转换 (PCM → WAV)
- **状态**: pending

### 3.3 实现摄像头模块
- [ ] `static/js/vision.js`
  - 摄像头权限获取
  - 视频流显示
  - 截图功能
- **状态**: pending

### 3.4 实现 WebSocket 通信
- [ ] `static/js/websocket.js`
  - WebSocket 连接管理
  - 消息发送/接收
  - 重连机制
- **状态**: pending

### 3.5 实现主应用逻辑
- [ ] `static/js/app.js`
  - 界面交互逻辑
  - 消息显示
  - 语音/视觉模式切换
- **状态**: pending

---

## 阶段4: 集成测试与优化

### 4.1 功能测试
- [ ] 测试纯语音对话流程
- [ ] 测试纯文本对话
- [ ] 测试图片理解
- [ ] 测试多模态 (语音+图片)
- **状态**: pending

### 4.2 性能优化
- [ ] 优化首token延迟
- [ ] 优化语音合成速度
- [ ] 优化显存占用
- **状态**: pending

### 4.3 文档与部署
- [ ] 更新 README.md
- [ ] 创建一键启动脚本
- [ ] 测试完整部署流程
- **状态**: pending

---

## 当前进度

**当前阶段**: 阶段1 - 环境准备
**正在执行**: 1.1 检查并启动 llama.cpp 服务
**总体进度**: 0%

---

## 开发日志

### 2026-04-09
- [x] 创建 design.md 设计文档
- [x] 创建 task.md 任务列表
- [ ] 开始阶段1: 环境准备

---

## 备注

- 所有模型服务必须在 Gateway 启动前运行
- HTTPS 证书使用自签名证书 (开发环境)
- 音频格式统一: 16kHz, 16bit, 单声道
