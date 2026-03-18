#!/usr/bin/env python3
"""
MiniCPM-o Worker (LLama.cpp 代理模式)
支持视频帧和音频流 - 实现贾维斯效果
"""

import json, time, logging, base64, io
from typing import List, Dict, Optional
import uvicorn, httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import asyncio

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger()

LLAMA_URL = "http://localhost:11434"
MODEL_NAME = "Model-7.6B-Q4_K_M.gguf"

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
client = None
conversation_history = []


def get_client():
    global client
    if client is None:
        client = httpx.AsyncClient(timeout=120.0)
    return client


@app.on_event("startup")
async def startup():
    logger.info(f"Worker started: {LLAMA_URL}")


@app.on_event("shutdown")
async def shutdown():
    global client
    if client:
        await client.aclose()


@app.get("/health")
async def health():
    return {"status": "idle", "model": MODEL_NAME}


@app.get("/status")
async def status():
    return {"status": "idle", "total_requests": 0}


def build_messages_with_media(
    messages: List[Dict],
    frame_b64: Optional[str] = None,
    audio_text: Optional[str] = None,
):
    """构建支持多模态的消息格式"""
    msgs = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("text", m.get("content", ""))

        if role == "user" and frame_b64:
            content = [
                {"type": "text", "text": content},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{frame_b64}"},
                },
            ]
        msgs.append({"role": role, "content": content})
    return msgs


def build_payload_stream(
    messages: List[Dict],
    max_tokens: int = 512,
    temperature: float = 0.7,
    frame_b64: str = None,
):
    """构建流式请求"""
    msgs = build_messages_with_media(messages, frame_b64)
    return {
        "model": MODEL_NAME,
        "messages": msgs,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": True,
    }


async def handle_duplex(ws: WebSocket, session_id: str = None):
    """处理全双工实时交互 (视频+音频)"""
    await ws.accept()
    logger.info(f"Duplex WS connected, session: {session_id}")

    global conversation_history
    conversation_history = []

    try:
        while True:
            try:
                data = await asyncio.wait_for(ws.receive_text(), timeout=60)
            except asyncio.TimeoutError:
                continue

            msg = json.loads(data)
            msg_type = msg.get("type", "")

            if msg_type == "start":
                await ws.send_text(json.dumps({"type": "ready"}))
                logger.info("Session started")

            elif msg_type == "audio_chunk":
                audio_b64 = msg.get("audio_base64", "")
                frame_b64_list = msg.get("frame_base64_list", [])
                frame_b64 = frame_b64_list[0] if frame_b64_list else None

                audio_text = ""
                if audio_b64:
                    audio_text = "[用户语音输入]"

                user_msg = {
                    "role": "user",
                    "content": audio_text or msg.get("text", ""),
                }

                if not conversation_history:
                    conversation_history.append(
                        {
                            "role": "system",
                            "content": "你是一个智能助手，像钢铁侠的贾维斯一样回答问题。简短、直接、幽默。",
                        }
                    )
                conversation_history.append(user_msg)

                payload = build_payload_stream(
                    conversation_history,
                    max_tokens=256,
                    temperature=0.7,
                    frame_b64=frame_b64,
                )

                await ws.send_text(
                    json.dumps({"type": "prefill_done", "input_tokens": 100})
                )

                c = get_client()
                response_text = ""
                tokens = 0

                try:
                    async with c.stream(
                        "POST", f"{LLAMA_URL}/v1/chat/completions", json=payload
                    ) as resp:
                        async for line in resp.aiter_lines():
                            if line.startswith("data: "):
                                d = line[6:]
                                if d == "[DONE]":
                                    break
                                try:
                                    chunk = json.loads(d)
                                    delta = (
                                        chunk.get("choices", [{}])[0]
                                        .get("delta", {})
                                        .get("content", "")
                                    )
                                    if delta:
                                        response_text += delta
                                        tokens += 1
                                        await ws.send_text(
                                            json.dumps(
                                                {"type": "chunk", "text_delta": delta}
                                            )
                                        )
                                except:
                                    pass
                except Exception as e:
                    logger.error(f"LLama error: {e}")
                    await ws.send_text(json.dumps({"type": "error", "error": str(e)}))
                    continue

                if response_text:
                    conversation_history.append(
                        {"role": "assistant", "content": response_text}
                    )

                await ws.send_text(
                    json.dumps(
                        {
                            "type": "done",
                            "text": response_text,
                            "generated_tokens": tokens,
                            "input_tokens": 100,
                        }
                    )
                )
                logger.info(f"Duplex done: {len(response_text)} chars, {tokens} tokens")

            elif msg_type == "text":
                user_msg = {"role": "user", "content": msg.get("text", "")}

                if not conversation_history:
                    conversation_history.append(
                        {
                            "role": "system",
                            "content": "你是一个智能助手，像钢铁侠的贾维斯一样回答问题。简短、直接、幽默。",
                        }
                    )
                conversation_history.append(user_msg)

                payload = build_payload_stream(conversation_history, max_tokens=512)

                c = get_client()
                response_text = ""
                tokens = 0

                try:
                    async with c.stream(
                        "POST", f"{LLAMA_URL}/v1/chat/completions", json=payload
                    ) as resp:
                        async for line in resp.aiter_lines():
                            if line.startswith("data: "):
                                d = line[6:]
                                if d == "[DONE]":
                                    break
                                try:
                                    chunk = json.loads(d)
                                    delta = (
                                        chunk.get("choices", [{}])[0]
                                        .get("delta", {})
                                        .get("content", "")
                                    )
                                    if delta:
                                        response_text += delta
                                        tokens += 1
                                        await ws.send_text(
                                            json.dumps(
                                                {"type": "chunk", "text_delta": delta}
                                            )
                                        )
                                except:
                                    pass
                except Exception as e:
                    await ws.send_text(json.dumps({"type": "error", "error": str(e)}))
                    continue

                if response_text:
                    conversation_history.append(
                        {"role": "assistant", "content": response_text}
                    )

                await ws.send_text(
                    json.dumps(
                        {
                            "type": "done",
                            "text": response_text,
                            "generated_tokens": tokens,
                        }
                    )
                )

            elif msg_type == "reset":
                conversation_history = []
                await ws.send_text(
                    json.dumps({"type": "ready", "message": "Session reset"})
                )

    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"Error: {e}")
        try:
            await ws.send_text(json.dumps({"type": "error", "error": str(e)}))
        except:
            pass
    finally:
        await ws.close()


async def handle_chat(ws: WebSocket, session_id: str = None):
    """处理普通聊天"""
    await ws.accept()
    logger.info(f"Chat WS connected")

    global conversation_history
    conversation_history = []

    try:
        data = await ws.receive_text()
        msg = json.loads(data)

        messages = msg.get("messages", [])
        gen = msg.get("generation", {})
        max_tokens = gen.get("max_new_tokens", 512)
        temperature = gen.get("temperature", 0.7)
        frame_b64 = msg.get("frame_base64_list", [None])[0]

        if not messages:
            messages = [{"role": "user", "content": msg.get("text", "")}]

        payload = build_payload_stream(messages, max_tokens, temperature, frame_b64)

        await ws.send_text(json.dumps({"type": "prefill_done", "input_tokens": 100}))

        c = get_client()
        text = ""
        tokens = 0

        async with c.stream(
            "POST", f"{LLAMA_URL}/v1/chat/completions", json=payload
        ) as resp:
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    d = line[6:]
                    if d == "[DONE]":
                        break
                    try:
                        chunk = json.loads(d)
                        delta = (
                            chunk.get("choices", [{}])[0]
                            .get("delta", {})
                            .get("content", "")
                        )
                        if delta:
                            text += delta
                            tokens += 1
                            await ws.send_text(
                                json.dumps({"type": "chunk", "text_delta": delta})
                            )
                    except:
                        pass

        await ws.send_text(
            json.dumps(
                {
                    "type": "done",
                    "text": text,
                    "generated_tokens": tokens,
                    "input_tokens": 100,
                }
            )
        )
        logger.info(f"Chat done: {len(text)} chars")

    except Exception as e:
        logger.error(f"Error: {e}")
        try:
            await ws.send_text(json.dumps({"type": "error", "error": str(e)}))
        except:
            pass
    finally:
        await ws.close()


@app.websocket("/ws/chat")
async def ws_chat(ws: WebSocket):
    await handle_chat(ws)


@app.websocket("/ws/half_duplex/{session_id}")
async def ws_half_duplex(ws: WebSocket, session_id: str):
    await handle_duplex(ws, session_id)


@app.websocket("/ws/duplex/{session_id}")
async def ws_duplex(ws: WebSocket, session_id: str):
    await handle_duplex(ws, session_id)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=22400)
    parser.add_argument("--llama-url", type=str, default="http://localhost:11434")
    args = parser.parse_args()
    LLAMA_URL = args.llama_url
    uvicorn.run(app, host="0.0.0.0", port=args.port, log_level="info")
