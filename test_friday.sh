#!/bin/bash
# Friday AI 助手 - 快速测试脚本

echo "=========================================="
echo "Friday AI 助手 - 功能测试"
echo "=========================================="

API_URL="http://localhost:11434"

# 测试服务是否运行
echo ""
echo "1. 测试服务状态..."
if curl -s "$API_URL/health" > /dev/null 2>&1; then
    echo "✅ 服务运行正常"
else
    echo "❌ 服务未运行，请先执行: ./start_friday_complete.sh"
    exit 1
fi

# 测试文本对话
echo ""
echo "2. 测试文本对话..."
curl -s -X POST "$API_URL/completion" \
    -H "Content-Type: application/json" \
    -d '{
        "prompt": "Hello! Please introduce yourself briefly.",
        "max_tokens": 100,
        "temperature": 0.7
    }' | head -c 500

echo ""
echo ""
echo "=========================================="
echo "✅ 测试完成"
echo "=========================================="
