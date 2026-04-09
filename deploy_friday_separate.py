#!/usr/bin/env python3
"""
Friday AI 助手 - 分离架构部署
使用 MiniCPM-V-4.0 (视觉+文本) + CosyVoice (语音)
适用于 RTX 3080 10GB
"""

import os
import sys
import torch
import numpy as np
from transformers import AutoModel, AutoTokenizer
from PIL import Image
import io
import base64

# 添加 CosyVoice 路径
sys.path.insert(0, "/home/dministrator/CosyVoice")


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


def load_vision_model():
    """加载 MiniCPM-V-2_6-int4 视觉模型"""
    print("\n🔄 正在加载 MiniCPM-V-2_6-int4 (视觉+文本)...")
    print("📁 使用本地模型: /opt/image/OpenBMB/MiniCPM-V-2_6-int4")

    model = AutoModel.from_pretrained(
        "/opt/image/OpenBMB/MiniCPM-V-2_6-int4",
        trust_remote_code=True,
        attn_implementation="sdpa",
        torch_dtype=torch.float16,
        device_map={"": 0},  # 使用 device_map 而不是 .cuda()
    )
    tokenizer = AutoTokenizer.from_pretrained(
        "/opt/image/OpenBMB/MiniCPM-V-2_6-int4", trust_remote_code=True
    )
    model.eval()

    return model, tokenizer


def load_cosyvoice():
    """加载 CosyVoice 语音模型"""
    print("\n🔄 正在加载 CosyVoice (语音合成)...")

    try:
        from cosyvoice.cli.cosyvoice import CosyVoice
        from cosyvoice.utils.file_utils import load_wav

        cosyvoice = CosyVoice("/opt/image/CosyVoice-300M-SFT")
        print("✅ CosyVoice 加载成功")
        return cosyvoice
    except Exception as e:
        print(f"⚠️  CosyVoice 加载失败: {e}")
        print("   语音功能将不可用")
        return None


def chat_with_vision(model, tokenizer, text, image=None):
    """与视觉模型对话"""
    try:
        if image is not None:
            # 视觉+文本对话
            msgs = [{"role": "user", "content": [image, text]}]
        else:
            # 纯文本对话
            msgs = [{"role": "user", "content": text}]

        res = model.chat(
            image=None,
            msgs=msgs,
            tokenizer=tokenizer,
            sampling=True,
            temperature=0.7,
        )
        return res
    except Exception as e:
        print(f"❌ 对话错误: {e}")
        return None


def text_to_speech(cosyvoice, text, output_file="output.wav"):
    """文本转语音"""
    if cosyvoice is None:
        print("❌ CosyVoice 未加载，无法合成语音")
        return None

    try:
        print(f"🎙️  正在合成语音: {text[:50]}...")

        # 使用默认音色合成
        for result in cosyvoice.inference_sft(text, "中文女"):
            import torchaudio

            torchaudio.save(output_file, result["tts_speech"], 22050)

        print(f"✅ 语音已保存: {output_file}")
        return output_file
    except Exception as e:
        print(f"❌ 语音合成失败: {e}")
        return None


def print_memory_usage():
    """打印显存使用情况"""
    allocated = torch.cuda.memory_allocated(0) / 1024**3
    reserved = torch.cuda.memory_reserved(0) / 1024**3
    print(f"\n📊 显存使用:")
    print(f"   已分配: {allocated:.2f} GB")
    print(f"   已预留: {reserved:.2f} GB")


def main():
    """主函数"""
    print("=" * 60)
    print("Friday AI 助手 - 分离架构")
    print("MiniCPM-V-2_6-int4 + CosyVoice")
    print("RTX 3080 10GB")
    print("=" * 60)

    # 检查 GPU
    gpu_memory = check_gpu()

    # 加载模型
    try:
        print("\n📦 正在加载模型...")
        vision_model, tokenizer = load_vision_model()
        cosyvoice = load_cosyvoice()

        print("\n✅ 所有模型加载完成！")
        print_memory_usage()

        # 功能说明
        print("\n" + "=" * 60)
        print("功能说明:")
        print("  • 文本对话: 直接输入文字")
        print("  • 图片理解: 输入图片路径")
        print("  • 语音合成: 输入 'tts:你的文字'")
        print("  • 退出: 输入 'quit'")
        print("=" * 60)

        # 交互模式
        while True:
            try:
                user_input = input("\n你: ").strip()

                if user_input.lower() in ["quit", "exit", "q"]:
                    break

                # TTS 模式
                if user_input.lower().startswith("tts:"):
                    text = user_input[4:].strip()
                    text_to_speech(cosyvoice, text)
                    continue

                # 检查是否是图片路径
                if os.path.exists(user_input) and user_input.lower().endswith(
                    (".png", ".jpg", ".jpeg", ".bmp")
                ):
                    print(f"🖼️  正在分析图片: {user_input}")
                    image = Image.open(user_input).convert("RGB")
                    response = chat_with_vision(
                        vision_model, tokenizer, "Describe this image.", image
                    )
                else:
                    # 纯文本对话
                    response = chat_with_vision(vision_model, tokenizer, user_input)

                if response:
                    print(f"助手: {response}")

                    # 询问是否转换为语音
                    if cosyvoice is not None:
                        tts_choice = input("🎙️  是否转换为语音? (y/n): ").strip().lower()
                        if tts_choice == "y":
                            text_to_speech(cosyvoice, response)

                print_memory_usage()

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
