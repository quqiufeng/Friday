#!/bin/bash
# MiniCPM-o-2.6 环境安装脚本 for RTX 3080

set -e

echo "=========================================="
echo "MiniCPM-o-2.6 环境安装"
echo "=========================================="

# 检查 CUDA
if ! command -v nvcc &> /dev/null; then
    echo "❌ 错误：未检测到 CUDA，请先安装 CUDA 12.1+"
    exit 1
fi

echo "✅ 检测到 CUDA: $(nvcc --version | grep release | awk '{print $5}' | cut -d',' -f1)"

# 创建虚拟环境
echo ""
echo "🔄 创建虚拟环境..."
python3 -m venv venv_minicpmo26
source venv_minicpmo26/bin/activate

# 升级 pip
echo "🔄 升级 pip..."
pip install --upgrade pip

# 安装 PyTorch (CUDA 12.1)
echo ""
echo "🔄 安装 PyTorch (CUDA 12.1)..."
pip install torch==2.3.1 torchvision==0.18.1 torchaudio==2.3.1 --index-url https://download.pytorch.org/whl/cu121

# 安装 transformers
echo ""
echo "🔄 安装 transformers..."
pip install transformers==4.44.2

# 安装 bitsandbytes (用于量化)
echo ""
echo "🔄 安装 bitsandbytes..."
pip install bitsandbytes

# 安装其他依赖
echo ""
echo "🔄 安装其他依赖..."
pip install Pillow==10.1.0 librosa==0.9.0 soundfile==0.12.1
pip install vector-quantize-pytorch==1.18.5 vocos==0.1.0
pip install decord moviepy
pip install requests numpy scipy

# 安装 accelerate (用于 device_map)
echo ""
echo "🔄 安装 accelerate..."
pip install accelerate

echo ""
echo "=========================================="
echo "✅ 环境安装完成！"
echo "=========================================="
echo ""
echo "使用方法:"
echo "1. 激活环境: source venv_minicpmo26/bin/activate"
echo "2. 运行部署: python deploy_minicpmo26.py"
echo ""
echo "注意: 首次运行会自动下载模型 (~16GB)"
echo "模型缓存位置: ~/.cache/huggingface/hub"
echo ""
