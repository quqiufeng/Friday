#!/usr/bin/env python3
"""
MiniCPM-o-2.6 视觉模块单独测试
"""

import os
import sys
import torch
from transformers import AutoModel, AutoTokenizer
from PIL import Image
import numpy as np


def check_gpu():
    """检查 GPU 状态"""
    if not torch.cuda.is_available():
        print("❌ 错误：没有检测到 CUDA GPU")
        sys.exit(1)

    gpu_name = torch.cuda.get_device_name(0)
    gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3

    print(f"✅ 检测到 GPU: {gpu_name}")
    print(f"✅ 显存: {gpu_memory:.1f} GB")

    return gpu_memory


def load_model():
    """加载模型"""
    print("\n🔄 正在加载 MiniCPM-o-2.6...")
    print("📁 使用本地模型: /opt/image/MiniCPM-o-2_6")

    # 先加载 tokenizer
    tokenizer = AutoTokenizer.from_pretrained(
        "/opt/image/MiniCPM-o-2_6", trust_remote_code=True
    )

    # 加载模型
    model = AutoModel.from_pretrained(
        "/opt/image/MiniCPM-o-2_6",
        trust_remote_code=True,
        torch_dtype=torch.float16,
        device_map="auto",
        init_vision=True,
        init_audio=False,  # 不加载音频
        init_tts=False,  # 不加载 TTS
    )

    print(f"\n📍 模型设备信息:")
    if hasattr(model, "vpm"):
        print(f"   VPM (视觉): {next(model.vpm.parameters()).device}")

    return model, tokenizer


def print_memory_usage():
    """打印显存使用情况"""
    allocated = torch.cuda.memory_allocated(0) / 1024**3
    reserved = torch.cuda.memory_reserved(0) / 1024**3
    print(f"\n📊 显存使用:")
    print(f"   已分配: {allocated:.2f} GB")
    print(f"   已预留: {reserved:.2f} GB")


def test_vision_only(model, tokenizer):
    """单独测试视觉模块"""
    print("\n" + "=" * 60)
    print("🖼️  测试视觉理解")
    print("=" * 60)

    try:
        # 创建测试图片
        img_array = np.zeros((224, 224, 3), dtype=np.uint8)
        for i in range(224):
            img_array[i, :, 0] = int(255 * i / 224)
            img_array[:, i, 1] = int(255 * i / 224)

        image = Image.fromarray(img_array)
        print("✅ 测试图片已创建")

        question = "What colors do you see in this image?"
        msgs = [{"role": "user", "content": [image, question]}]

        print("🔄 正在推理...")
        res = model.chat(
            image=None,
            msgs=msgs,
            tokenizer=tokenizer,
            sampling=True,
            temperature=0.7,
            max_new_tokens=64,
        )

        print(f"📝 回答: {res}")
        return True

    except Exception as e:
        print(f"❌ 视觉测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("MiniCPM-o-2.6 视觉模块单独测试")
    print("RTX 3080 10GB")
    print("=" * 60)

    # 检查 GPU
    gpu_memory = check_gpu()

    # 加载模型
    try:
        model, tokenizer = load_model()

        print("\n✅ 模型加载完成！")
        print_memory_usage()

        # 只测试视觉
        success = test_vision_only(model, tokenizer)
        print_memory_usage()

        if success:
            print("\n✅ 视觉模块测试通过！")
        else:
            print("\n❌ 视觉模块测试失败")

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
