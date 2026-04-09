"""
CosyVoice 语音合成客户端
"""

import httpx
import base64
from typing import Optional, Dict, Any, Union


class CosyVoiceClient:
    """CosyVoice HTTP 客户端"""

    def __init__(self, base_url: str = "http://localhost:11436"):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=60.0)

    async def synthesize(
        self, text: str, voice: str = "default", speed: float = 1.0
    ) -> bytes:
        """
        语音合成

        Args:
            text: 要合成的文本
            voice: 音色 (default/中文女/中文男/英文女/英文男)
            speed: 语速 (0.5-2.0)

        Returns:
            WAV 格式音频数据
        """
        url = f"{self.base_url}/tts"

        data = {
            "text": text,
            "voice": voice,
            "speed": speed,
        }

        response = await self.client.post(url, json=data)
        response.raise_for_status()
        result = response.json()

        # Base64 解码音频
        audio_b64 = result.get("audio", "")
        return base64.b64decode(audio_b64)

    async def synthesize_stream(
        self, text: str, voice: str = "default", speed: float = 1.0
    ):
        """
        流式语音合成 (用于长文本)

        Args:
            text: 要合成的文本
            voice: 音色
            speed: 语速

        Yields:
            音频数据块 (bytes)
        """
        url = f"{self.base_url}/tts_stream"

        data = {
            "text": text,
            "voice": voice,
            "speed": speed,
        }

        async with self.client.stream("POST", url, json=data) as response:
            response.raise_for_status()
            async for chunk in response.aiter_bytes():
                yield chunk

    async def clone_voice(
        self, text: str, reference_audio: bytes, speed: float = 1.0
    ) -> bytes:
        """
        声音克隆 (3秒极速克隆)

        Args:
            text: 要合成的文本
            reference_audio: 参考音频 (WAV, 3-10秒)
            speed: 语速

        Returns:
            WAV 格式音频数据
        """
        url = f"{self.base_url}/tts_clone"

        # Base64 编码参考音频
        ref_b64 = base64.b64encode(reference_audio).decode("utf-8")

        data = {
            "text": text,
            "reference_audio": ref_b64,
            "speed": speed,
        }

        response = await self.client.post(url, json=data)
        response.raise_for_status()
        result = response.json()

        audio_b64 = result.get("audio", "")
        return base64.b64decode(audio_b64)

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
