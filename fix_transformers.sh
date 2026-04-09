#!/bin/bash
# 修复 transformers 版本

set -e

echo "🔄 安装兼容的 transformers 版本..."

# MiniCPM-o-2.6 需要 transformers 4.44.2
pip install transformers==4.44.2

echo "✅ 完成！"
