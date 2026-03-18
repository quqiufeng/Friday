#!/usr/bin/env python3
"""
贾维斯语音助手
语音输入 → SenseVoice识别 → OpenCode执行 → CosyVoice语音回复
"""

import os
import sys
import json
import subprocess
import requests
from pathlib import Path

OPENCODE_ACP_URL = "http://localhost:4096"
SENSE_VOICE_BIN = "/home/dministrator/SenseVoice.cpp/bin/sense-voice-main"
SENSE_VOICE_MODEL = (
    "/home/dministrator/SenseVoice.cpp/models/sense-voice-small-q6_k.gguf"
)
COSYVOICE_DIR = "/home/dministrator/CosyVoice"
DEFAULT_REF_AUDIO = "/opt/MiniCPM/assets/ref_audio/ref_minicpm_signature.wav"

GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"


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


def recognize_sensevoice(audio_file):
    log_info("正在识别...")
    cmd = f'{SENSE_VOICE_BIN} -m {SENSE_VOICE_MODEL} -oj "{audio_file}"'
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=60
        )
        if result.returncode == 0 and result.stdout:
            # 解析 JSON 输出
            for line in result.stdout.strip().split("\n"):
                if line.startswith("{"):
                    data = json.loads(line)
                    text = data.get("text", "").strip()
                    if text:
                        return text
            return result.stdout.strip()
        log_error(f"识别失败: {result.stderr}")
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
        text = recognize_sensevoice(audio)

        if text:
            print(f"\n识别: {text}\n")
            send_to_opencode(text)
            print("\n请在 OpenCode 窗口查看结果")


if __name__ == "__main__":
    main()
