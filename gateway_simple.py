"""
Friday AI 助手 - Gateway 服务
集成: MiniCPM-V-2_6 + SenseVoice + CosyVoice
"""

import os
import sys
import json
import base64
import asyncio
from typing import Optional
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# 添加模块路径
sys.path.insert(0, os.path.dirname(__file__))
from modules.llama_client import LlamaClient
from modules.sensevoice_client import SenseVoiceClient
from modules.cosyvoice_client import CosyVoiceClient

# ============ 全局客户端 ============
llama_client: Optional[LlamaClient] = None
sensevoice_client: Optional[SenseVoiceClient] = None
cosyvoice_client: Optional[CosyVoiceClient] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global llama_client, sensevoice_client, cosyvoice_client

    # 初始化客户端
    llama_client = LlamaClient("http://localhost:11434")
    sensevoice_client = SenseVoiceClient("http://localhost:11435")
    cosyvoice_client = CosyVoiceClient("http://localhost:11436")

    print("✅ Gateway 客户端初始化完成")
    print("  - MiniCPM-V-2_6: http://localhost:11434")
    print("  - SenseVoice: http://localhost:11435")
    print("  - CosyVoice: http://localhost:11436")

    yield

    # 清理
    if llama_client:
        await llama_client.close()
    if sensevoice_client:
        await sensevoice_client.close()
    if cosyvoice_client:
        await cosyvoice_client.close()
    print("🛑 Gateway 已关闭")


app = FastAPI(
    title="Friday AI 助手",
    description="多模态 AI 助手 Gateway (MiniCPM-V + SenseVoice + CosyVoice)",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


# ============ REST API ============


@app.get("/")
async def index():
    """主页"""
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("<h1>Friday AI 助手</h1><p>WebUI 加载中...</p>")


@app.get("/health")
async def health():
    """健康检查"""
    return {
        "status": "healthy",
        "services": {
            "llama": await llama_client.health_check() if llama_client else False,
            "sensevoice": await sensevoice_client.health_check()
            if sensevoice_client
            else False,
            "cosyvoice": await cosyvoice_client.health_check()
            if cosyvoice_client
            else False,
        },
    }


@app.post("/api/chat")
async def chat(request: dict):
    """文本对话"""
    messages = request.get("messages", [])
    temperature = request.get("temperature", 0.7)

    result = await llama_client.chat(
        messages=messages,
        temperature=temperature,
    )

    return result


@app.post("/api/vision")
async def vision(request: dict):
    """图片理解"""
    image_base64 = request.get("image", "")
    text = request.get("text", "描述这张图片")
    temperature = request.get("temperature", 0.7)

    result = await llama_client.vision_chat(
        image_base64=image_base64,
        text=text,
        temperature=temperature,
    )

    return result


@app.post("/api/asr")
async def asr(file: UploadFile = File(...)):
    """语音识别"""
    audio_data = await file.read()

    result = await sensevoice_client.transcribe(audio_data)

    return result


@app.post("/api/tts")
async def tts(request: dict):
    """语音合成"""
    text = request.get("text", "")
    voice = request.get("voice", "default")

    audio_data = await cosyvoice_client.synthesize(text, voice=voice)

    # Base64 编码返回
    audio_b64 = base64.b64encode(audio_data).decode("utf-8")

    return {
        "audio": audio_b64,
        "format": "wav",
    }


# ============ WebSocket ============


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket 实时对话"""
    await websocket.accept()
    print("🔌 WebSocket 连接已建立")

    try:
        while True:
            # 接收消息
            message = await websocket.receive_json()
            msg_type = message.get("type")

            if msg_type == "text":
                # 文本对话
                text = message.get("text", "")
                messages = [{"role": "user", "content": text}]

                result = await llama_client.chat(messages)
                response_text = result.get("text", "")

                # 发送文本回复
                await websocket.send_json(
                    {
                        "type": "text_response",
                        "text": response_text,
                    }
                )

                # 合成语音并发送
                try:
                    audio_data = await cosyvoice_client.synthesize(response_text)
                    audio_b64 = base64.b64encode(audio_data).decode("utf-8")

                    await websocket.send_json(
                        {
                            "type": "audio_response",
                            "audio": audio_b64,
                        }
                    )
                except Exception as e:
                    print(f"TTS 错误: {e}")

            elif msg_type == "audio":
                # 语音输入
                audio_b64 = message.get("data", "")
                audio_data = base64.b64decode(audio_b64)

                # 语音识别
                asr_result = await sensevoice_client.transcribe(audio_data)
                recognized_text = asr_result.get("text", "")

                # 发送识别结果
                await websocket.send_json(
                    {
                        "type": "asr_result",
                        "text": recognized_text,
                    }
                )

                # AI 对话
                messages = [{"role": "user", "content": recognized_text}]
                result = await llama_client.chat(messages)
                response_text = result.get("text", "")

                # 发送文本回复
                await websocket.send_json(
                    {
                        "type": "text_response",
                        "text": response_text,
                    }
                )

                # 合成语音
                try:
                    audio_data = await cosyvoice_client.synthesize(response_text)
                    audio_b64 = base64.b64encode(audio_data).decode("utf-8")

                    await websocket.send_json(
                        {
                            "type": "audio_response",
                            "audio": audio_b64,
                        }
                    )
                except Exception as e:
                    print(f"TTS 错误: {e}")

            elif msg_type == "image":
                # 图片理解
                image_b64 = message.get("data", "")
                text = message.get("text", "描述这张图片")

                result = await llama_client.vision_chat(image_b64, text)
                response_text = result.get("text", "")

                await websocket.send_json(
                    {
                        "type": "text_response",
                        "text": response_text,
                    }
                )

                # 合成语音
                try:
                    audio_data = await cosyvoice_client.synthesize(response_text)
                    audio_b64 = base64.b64encode(audio_data).decode("utf-8")

                    await websocket.send_json(
                        {
                            "type": "audio_response",
                            "audio": audio_b64,
                        }
                    )
                except Exception as e:
                    print(f"TTS 错误: {e}")

    except WebSocketDisconnect:
        print("🔌 WebSocket 连接已断开")
    except Exception as e:
        print(f"WebSocket 错误: {e}")
        await websocket.close()


# ============ 入口 ============

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10024)
