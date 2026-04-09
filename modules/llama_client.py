"""
llama.cpp HTTP 客户端
用于与 MiniCPM-V-2_6 模型通信
"""

import httpx
import base64
import json
from typing import Optional, Dict, Any, AsyncGenerator


class LlamaClient:
    """llama-server HTTP 客户端"""

    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=300.0)

    async def chat(
        self,
        messages: list,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        stream: bool = False,
    ) -> Dict[str, Any]:
        """
        文本对话

        Args:
            messages: 消息列表 [{"role": "user", "content": "..."}]
            temperature: 温度参数
            max_tokens: 最大生成token数
            stream: 是否流式返回
        """
        url = f"{self.base_url}/completion"

        # 构建 prompt
        prompt = self._build_prompt(messages)

        data = {
            "prompt": prompt,
            "temperature": temperature,
            "n_predict": max_tokens,
            "stream": stream,
            "stop": ["<|im_end|>", "<|endoftext|>"],
        }

        if stream:
            return self._chat_stream(url, data)

        response = await self.client.post(url, json=data)
        response.raise_for_status()
        result = response.json()

        return {
            "text": result.get("content", "").strip(),
            "tokens": result.get("tokens_evaluated", 0),
        }

    async def vision_chat(
        self,
        image_base64: str,
        text: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> Dict[str, Any]:
        """
        视觉对话 (图片理解)

        Args:
            image_base64: base64编码的图片
            text: 用户问题
            temperature: 温度参数
            max_tokens: 最大生成token数
        """
        url = f"{self.base_url}/completion"

        # MiniCPM-V 使用特殊格式
        prompt = f"<image>{image_base64}</image>\n{text}"

        data = {
            "prompt": prompt,
            "temperature": temperature,
            "n_predict": max_tokens,
            "stream": False,
            "stop": ["<|im_end|>", "<|endoftext|>"],
        }

        response = await self.client.post(url, json=data)
        response.raise_for_status()
        result = response.json()

        return {
            "text": result.get("content", "").strip(),
            "tokens": result.get("tokens_evaluated", 0),
        }

    async def _chat_stream(self, url: str, data: dict) -> AsyncGenerator[str, None]:
        """流式对话"""
        async with self.client.stream("POST", url, json=data) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    try:
                        chunk = json.loads(line[6:])
                        if "content" in chunk:
                            yield chunk["content"]
                    except json.JSONDecodeError:
                        continue

    def _build_prompt(self, messages: list) -> str:
        """构建对话 prompt"""
        prompt_parts = []

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")

            if role == "system":
                prompt_parts.append(f"<|im_start|>system\n{content}<|im_end|>")
            elif role == "user":
                prompt_parts.append(f"<|im_start|>user\n{content}<|im_end|>")
            elif role == "assistant":
                prompt_parts.append(f"<|im_start|>assistant\n{content}<|im_end|>")

        # 添加 assistant 前缀
        prompt_parts.append("<|im_start|>assistant\n")

        return "\n".join(prompt_parts)

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
