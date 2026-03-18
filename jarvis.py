#!/usr/bin/env python3
"""
贾维斯语音助手
语音输入 → Faster-Whisper识别 → OpenCode执行 → CosyVoice语音回复
"""

import os
import sys
import json
import subprocess
import requests
from pathlib import Path
from faster_whisper import WhisperModel

OPENCODE_ACP_URL = "http://localhost:4096"
WHISPER_MODEL_PATH = "/opt/image/faster-whisper-large-v3"
COSYVOICE_DIR = "/home/dministrator/CosyVoice"
DEFAULT_REF_AUDIO = "/opt/MiniCPM/assets/ref_audio/ref_minicpm_signature.wav"

GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"

whisper_model = None


def get_whisper_model():
    global whisper_model
    if whisper_model is None:
        log_info("加载 Whisper 模型...")
        whisper_model = WhisperModel(WHISPER_MODEL_PATH, device="cuda", compute_type="float16")
        log_info("Whisper 模型加载完成")
    return whisper_model


def log_info(msg):
    print(f"{GREEN}[INFO]{RESET} {msg}")


def log_warn(msg):
    print(f"{YELLOW}[WARN]{RESET} {msg}")


def log_error(msg):
    print(f"{RED}[ERROR]{RESET} {msg}")


def list_ref_audios():
    ref_dir = Path("/opt/MiniCPM/assets/ref_audio")
    if ref_dir.exists():
        audios = list(ref_dir.glob("*.wav"))
        print("\n可用音源:")
        for i, audio in enumerate(audios):
            m = " [默认]" if str(audio) == DEFAULT_REF_AUDIO else ""
            print(f"  {i + 1}. {audio.name}{m}")


def record_audio(duration=5, output="/tmp/jarvis_input.wav"):
    log_info(f"请说话 ({duration}秒)...")
    subprocess.run(f"arecord -f cd -t wav -d {duration} {output}", shell=True)
    return output


def recognize_whisper(audio_file):
    log_info("正在识别...")
    try:
        model = get_whisper_model()
        segments, info = model.transcribe(
            audio_file,
            language="zh",
            beam_size=5,
            vad_filter=True
        )
        
        text = ""
        for segment in segments:
            text += segment.text.strip()
        
        if text:
            log_info(f"识别完成: {text}")
            return text
        else:
            log_error("未识别到文字")
            return None
    except Exception as e:
        log_error(f"识别异常: {e}")
        return None


def send_to_opencode(text):
    log_info(f"执行: {text}")
    try:
        requests.post(
            f"{OPENCODE_ACP_URL}/tui/append-prompt", json={"text": text}, timeout=10
        )
        requests.post(f"{OPENCODE_ACP_URL}/tui/submit-prompt", timeout=10)
        return True
    except Exception as e:
        log_error(f"连接失败: {e}")
        return False


def tts_cosyvoice(text, ref_audio=None, output="/tmp/jarvis_output.wav"):
    if ref_audio is None:
        ref_audio = DEFAULT_REF_AUDIO

    log_info("正在合成语音...")

    instruct = "You are a helpful assistant. 请用讲故事的语气朗读。<|endofprompt|>"

    cmd = f'''source ~/anaconda3/bin/activate cosyvoice && \
cd ~/CosyVoice && \
python3 -c "
import sys
sys.path.insert(0, 'third_party/Matcha-TTS')
from cosyvoice.cli.cosyvoice import AutoModel
import torchaudio
cosyvoice = AutoModel(model_dir='/opt/image/Fun-CosyVoice3-0.5B')
for j in cosyvoice.inference_instruct2('{text}', '{instruct}', '{ref_audio}', stream=False):
    torchaudio.save('{output}', j['tts_speech'], cosyvoice.sample_rate)
print('OK')
"'''

    try:
        subprocess.run(cmd, shell=True, timeout=120)
        return output
    except Exception as e:
        log_error(f"合成失败: {e}")
        return None


def play_audio(audio_file):
    if audio_file and os.path.exists(audio_file):
        subprocess.run(["aplay", audio_file])
    else:
        log_warn("没有音频")


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--text", help="直接发送文本")
    parser.add_argument("-l", "--list", action="store_true", help="列出音源")
    parser.add_argument("-r", "--ref", help="指定音源")
    args = parser.parse_args()

    if args.list:
        list_ref_audios()
    elif args.text:
        send_to_opencode(args.text)
    else:
        print("\n=== 贾维斯语音助手 ===")
        list_ref_audios()

        audio = record_audio(5)
        text = recognize_whisper(audio)

        if text:
            print(f"\n识别: {text}\n")
            send_to_opencode(text)
            print("\n请在 OpenCode 窗口查看结果")


if __name__ == "__main__":
    main()
