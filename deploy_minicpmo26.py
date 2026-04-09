#!/usr/bin/env python3
"""
MiniCPM-o-2.6 4bit 量化部署脚本 for RTX 3080 10GB
禁用 TTS，只测试视觉+文本
"""

import os
import sys
import torch
from transformers import AutoModel, AutoTokenizer, BitsAndBytesConfig


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


def load_model_4bit():
    """加载 4bit 量化模型 - 禁用 TTS"""
    print("\n🔄 正在加载 MiniCPM-o-2.6 (4bit 量化)...")
    print("📁 使用本地模型: /opt/image/MiniCPM-o-2_6")
    print("⚠️  注意：TTS 功能已禁用（4bit 量化不支持）")

    # 先加载 tokenizer
    tokenizer = AutoTokenizer.from_pretrained(
        "/opt/image/MiniCPM-o-2_6", trust_remote_code=True
    )

    # 4bit 量化配置
    quantization_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
    )

    # 加载模型 - 使用 device_map 强制所有层在 GPU 0
    # 注意：4bit/8bit 量化需要特殊处理 device_map
    # 使用 {"": 0} 强制所有层在 GPU 0 上
    model = AutoModel.from_pretrained(
        "/opt/image/MiniCPM-o-2_6",
        trust_remote_code=True,
        torch_dtype=torch.bfloat16,
        quantization_config=quantization_config,
        device_map={"": 0},  # 强制所有层在 GPU 0
        init_vision=True,
        init_audio=True,
        init_tts=False,  # 禁用 TTS
    )

    # 不调用 init_tts()

    return model, tokenizer


def print_memory_usage():
    """打印显存使用情况"""
    allocated = torch.cuda.memory_allocated(0) / 1024**3
    reserved = torch.cuda.memory_reserved(0) / 1024**3
    print(f"\n📊 显存使用:")
    print(f"   已分配: {allocated:.2f} GB")
    print(f"   已预留: {reserved:.2f} GB")


def test_vision(model, tokenizer):
    """测试视觉理解"""
    from PIL import Image
    import numpy as np

    print("\n🖼️  测试视觉理解...")

    try:
        # 创建测试图片
        img_array = np.zeros((224, 224, 3), dtype=np.uint8)
        for i in range(224):
            img_array[i, :, 0] = int(255 * i / 224)
            img_array[:, i, 1] = int(255 * i / 224)

        image = Image.fromarray(img_array)

        question = "What colors do you see in this image?"
        msgs = [{"role": "user", "content": [image, question]}]

        res = model.chat(
            image=None,
            msgs=msgs,
            tokenizer=tokenizer,
            sampling=True,
            temperature=0.7,
        )

        print(f"📝 回答: {res}")
        return res
    except Exception as e:
        print(f"❌ 视觉测试失败: {e}")
        import traceback

        traceback.print_exc()
        return None


def test_text(model, tokenizer):
    """测试纯文本对话"""
    print("\n💬 测试文本对话...")

    try:
        msgs = [
            {"role": "user", "content": "Hello! Please introduce yourself briefly."}
        ]

        res = model.chat(
            msgs=msgs,
            tokenizer=tokenizer,
            sampling=True,
            max_new_tokens=128,
            temperature=0.7,
        )

        print(f"📝 回答: {res}")
        return res
    except Exception as e:
        print(f"❌ 文本测试失败: {e}")
        import traceback

        traceback.print_exc()
        return None


def main():
    """主函数"""
    print("=" * 60)
    print("MiniCPM-o-2.6 4bit 量化部署工具")
    print("RTX 3080 10GB - 视觉+文本模式")
    print("=" * 60)

    # 检查 GPU
    gpu_memory = check_gpu()

    # 加载模型
    try:
        model, tokenizer = load_model_4bit()

        print("\n✅ 模型加载完成！")
        print("⚠️  TTS 语音功能已禁用（4bit 量化不支持）")
        print_memory_usage()

        # 测试功能
        print("\n" + "=" * 60)
        print("开始功能测试")
        print("=" * 60)

        # 测试文本
        test_text(model, tokenizer)
        print_memory_usage()

        # 测试视觉
        test_vision(model, tokenizer)
        print_memory_usage()

        print("\n" + "=" * 60)
        print("✅ 测试完成！")
        print("=" * 60)

        # 进入交互模式
        print("\n进入交互模式 (输入 'quit' 退出)")
        print("支持：文本对话、图片理解")
        print("不支持：语音合成（TTS）")

        while True:
            try:
                user_input = input("\n你: ").strip()
                if user_input.lower() in ["quit", "exit", "q"]:
                    break

                msgs = [{"role": "user", "content": user_input}]
                res = model.chat(
                    msgs=msgs,
                    tokenizer=tokenizer,
                    sampling=True,
                    temperature=0.7,
                )
                print(f"助手: {res}")
            except EOFError:
                break
            except Exception as e:
                print(f"❌ 错误: {e}")

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
