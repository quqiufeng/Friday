"""
SenseVoice 语音识别客户端
"""

import httpx
import base64
from typing import Optional, Dict, Any


class SenseVoiceClient:
    """SenseVoice HTTP 客户端"""

    def __init__(self, base_url: str = "http://localhost:11435"):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=30.0)

    async def transcribe(
        self, audio_data: bytes, language: str = "auto", use_itn: bool = True
    ) -> Dict[str, Any]:
        """
        语音识别

        Args:
            audio_data: WAV 格式音频数据 (16kHz, 16bit, 单声道)
            language: 语言代码 (zh/en/ja/ko/yue/auto)
            use_itn: 是否使用逆文本归一化

        Returns:
            {"text": "识别结果", "language": "语言", "emotion": "情感"}
        """
        url = f"{self.base_url}/asr"

        # Base64 编码音频
        audio_b64 = base64.b64encode(audio_data).decode("utf-8")

        data = {
            "audio": audio_b64,
            "language": language,
            "use_itn": use_itn,
        }

        response = await self.client.post(url, json=data)
        response.raise_for_status()
        result = response.json()

        return {
            "text": result.get("text", ""),
            "language": result.get("language", "unknown"),
            "emotion": result.get("emotion", "unknown"),
            "event": result.get("event", "unknown"),
        }

    async def transcribe_file(self, file_path: str) -> Dict[str, Any]:
        """从文件识别语音"""
        with open(file_path, "rb") as f:
            audio_data = f.read()
        return await self.transcribe(audio_data)

    async def health_check(self) -> bool:
        """健康检查"""
        try:
            response = await self.client.get(f"{self.base_url}/health", timeout=5.0)
            return response.status_code == 200
        except:
            return False

    async def close(self):
        """关闭连接"""
        await self.client.aclose()
