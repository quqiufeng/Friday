# MiniCPM-o-2.6 RTX 3080 10GB 部署指南

## 快速开始

### 1. 安装环境

```bash
bash install_env.sh
```

这会创建虚拟环境并安装所有依赖。

### 2. 运行部署

```bash
source venv_minicpmo26/bin/activate
python deploy_minicpmo26.py
```

**首次运行会自动下载模型 (~16GB)**，下载位置：`~/.cache/huggingface/hub`

### 3. 选择量化模式

- **8bit 量化** (推荐)：显存占用 ~8-9GB，质量较好
- **4bit 量化**：显存占用 ~6-7GB，质量可能略有下降

## 显存占用预估

| 模式 | 模型加载 | 运行时 | 总占用 |
|------|----------|--------|--------|
| 8bit | ~7GB | ~1-2GB | ~8-9GB |
| 4bit | ~5GB | ~1-2GB | ~6-7GB |

## 注意事项

1. **模型下载**：首次运行需要下载 ~16GB 模型文件，请确保网络稳定
2. **磁盘空间**：需要至少 20GB 可用空间
3. **量化影响**：
   - 8bit：对 TTS 音质影响较小
   - 4bit：可能会有轻微音质下降
4. **推理速度**：量化后推理速度会略有降低

## 手动下载模型（可选）

如果自动下载慢，可以手动下载后放到缓存目录：

```bash
# 安装 huggingface-cli
pip install huggingface-hub

# 下载模型
huggingface-cli download openbmb/MiniCPM-o-2_6 \
    --local-dir ~/.cache/huggingface/hub/models--openbmb--MiniCPM-o-2_6 \
    --resume-download
```

## 国内镜像加速

如果下载慢，可以设置镜像：

```bash
export HF_ENDPOINT=https://hf-mirror.com
python deploy_minicpmo26.py
```

## 测试功能

部署脚本会自动测试：
1. ✅ 视觉理解（图像描述）
2. ✅ 音频理解（语音识别）
3. ✅ 语音合成（TTS）

测试完成后进入交互模式，可以直接对话。

## 故障排除

### 显存不足 (OOM)
- 尝试 4bit 量化
- 减少 `max_new_tokens`
- 关闭其他占用显存的程序

### 模型下载失败
- 检查网络连接
- 使用 `export HF_ENDPOINT=https://hf-mirror.com`
- 手动下载模型

### TTS 音质差
- 8bit 量化通常音质可接受
- 4bit 量化可能音质下降明显
- 可以尝试调整 `temperature` 参数

## 下一步

测试成功后，可以：
1. 集成到你的 Friday 项目中
2. 修改 worker.py 使用量化模型
3. 添加 WebUI 界面
