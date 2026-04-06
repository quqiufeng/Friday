"""oka - MiniCPM-o 核心模型实现

接口完全对齐 MiniCPMO45.modeling_minicpmo_unified.MiniCPMO
支持 GGUF (llama-cpp-python) 和 HuggingFace 格式
"""

import os
import json
import time
import threading
from typing import Dict, List, Optional, Union, Any, Tuple
from enum import Enum

import torch
import torch.nn.functional as F
import numpy as np


class ProcessorMode:
    CHAT = "chat"
    STREAMING = "streaming"
    DUPLEX = "duplex"


class MiniCPMOConfig:
    def __init__(
        self, model_path: str, mmproj_path: str = None, device: str = "cuda", **kwargs
    ):
        self._name_or_path = model_path
        self.model_path = model_path
        self.mmproj_path = mmproj_path
        self.device = device
        self._configs = {}

        config_file = (
            os.path.join(model_path, "config.json")
            if os.path.exists(model_path)
            else None
        )
        if config_file and os.path.exists(config_file):
            with open(config_file, "r") as f:
                self._configs = json.load(f)


class MiniCPMO:
    """MiniCPM-o 主模型类

    接口完全对齐 MiniCPMO45.modeling_minicpmo_unified.MiniCPMO
    """

    def __init__(self, config: MiniCPMOConfig):
        self.config = config
        self.device = config.device
        self.model_path = config.model_path

        if config.model_path.endswith(".gguf"):
            self._is_gguf = True
        else:
            self._is_gguf = False

        self.llm = None
        self.llm_cpp = None  # llama-cpp-python 实例
        self.vpm = None
        self.processor = None
        self.duplex = None
        self._tokenizer = None
        self._current_mode = None
        self._unified_initialized = False
        self._chat_vocoder = "token2wav"

    @classmethod
    def from_pretrained(
        cls,
        model_path: str,
        mmproj_path: str = None,
        trust_remote_code: bool = True,
        _attn_implementation: str = "auto",
        **kwargs,
    ):
        config = MiniCPMOConfig(
            model_path=model_path, mmproj_path=mmproj_path, **kwargs
        )
        model = cls(config)
        model._load_model()
        return model

    def _load_model(self):
        if self._is_gguf:
            self._load_gguf()
        else:
            self._load_hf()

    def _load_gguf(self):
        from llama_cpp import Llama

        self.llm_cpp = Llama(
            model_path=self.model_path,
            n_ctx=8192,
            n_gpu_layers=99,
            verbose=False,
            chat_template=None,
        )

        self._tokenizer = GGUFTokenizer(self.llm_cpp)
        self.llm = GGUFModelWrapper(self.llm_cpp)

    def _load_hf(self):
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.llm = AutoModelForCausalLM.from_pretrained(
            self.model_path,
            trust_remote_code=True,
            _attn_implementation=self.config._configs.get(
                "attn_implementation", "auto"
            ),
        )
        self.llm.bfloat16().eval()
        if self.device == "cuda":
            self.llm.cuda()

        self._tokenizer = AutoTokenizer.from_pretrained(
            self.model_path, trust_remote_code=True
        )

    @property
    def processor(self):
        return self._processor

    @processor.setter
    def processor(self, value):
        self._processor = value

    def init_unified(
        self,
        pt_path: str = None,
        preload_both_tts: bool = True,
        duplex_config: dict = None,
        device: str = "cuda",
        chat_vocoder: str = "token2wav",
    ):
        self._chat_vocoder = chat_vocoder

        if duplex_config is None:
            duplex_config = {
                "generate_audio": True,
                "ls_mode": "explicit",
                "max_new_speak_tokens_per_chunk": 20,
                "temperature": 0.7,
                "top_k": 20,
                "top_p": 0.8,
                "force_listen_count": 3,
            }

        self.duplex = DuplexCapability(model=self, device=device, **duplex_config)

        self._unified_initialized = True
        self.set_mode(ProcessorMode.STREAMING)

    def set_mode(self, mode):
        self._current_mode = mode
        self.reset_session(reset_token2wav_cache=True)

    def reset_session(self, reset_token2wav_cache: bool = True):
        if self.duplex:
            self.duplex.decoder.reset()

    def bfloat16(self):
        """Convert model to bfloat16"""
        if self._is_gguf:
            return self
        if hasattr(self.llm, "bfloat16"):
            self.llm = self.llm.bfloat16()
        return self

    def cuda(self):
        """Move model to CUDA"""
        if self._is_gguf:
            return self
        if hasattr(self.llm, "cuda"):
            self.llm = self.llm.cuda()
        return self

    def eval(self):
        """Set model to evaluation mode"""
        if self._is_gguf:
            return self
        if hasattr(self.llm, "eval"):
            self.llm.eval()
        return self

    def cuda(self):
        """Move model to CUDA"""
        if hasattr(self.llm, "cuda"):
            self.llm = self.llm.cuda()
        return self

    def eval(self):
        """Set model to evaluation mode"""
        if hasattr(self.llm, "eval"):
            self.llm.eval()
        return self

    def chat(
        self,
        msgs: List[Dict],
        tokenizer=None,
        max_new_tokens: int = 512,
        do_sample: bool = False,
        temperature: float = 0.7,
        top_p: float = 0.8,
        **kwargs,
    ) -> str:
        prompt = self._build_prompt(msgs)

        if self._is_gguf:
            output = self.llm_cpp.create_completion(
                prompt=prompt,
                max_tokens=max_new_tokens,
                temperature=temperature if do_sample else 0,
                stop=["<|im_end|>", "</s>", "<|endoftext|>"],
            )
            return output["choices"][0]["text"].strip()
        else:
            inputs = self._tokenizer(prompt, return_tensors="pt").to(self.device)
            with torch.no_grad():
                outputs = self.llm.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    do_sample=do_sample,
                    temperature=temperature,
                    top_p=top_p,
                )
            return self._tokenizer.decode(outputs[0], skip_special_tokens=True).strip()

    def _build_prompt(self, msgs: List[Dict]) -> str:
        prompt = ""
        for msg in msgs:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if isinstance(content, list):
                text_parts = [
                    c.get("text", "")
                    for c in content
                    if isinstance(c, dict) and c.get("type") == "text"
                ]
                content = " ".join(text_parts)
            prompt += f"<|im_start|>{role}\n{content}<|im_end|>\n"
        prompt += "<|im_start|>assistant\n"
        return prompt

    def streaming_prefill(self, **kwargs):
        if self.duplex is None:
            raise RuntimeError("请先调用 init_unified()")
        return self.duplex.streaming_prefill(**kwargs)

    def streaming_generate(self, **kwargs):
        if self.duplex is None:
            raise RuntimeError("请先调用 init_unified()")
        return self.duplex.streaming_generate(**kwargs)

    def duplex_prepare(self, **kwargs):
        if self.duplex is None:
            raise RuntimeError("请先调用 init_unified()")
        return self.duplex.prepare(**kwargs)

    def duplex_prefill(self, **kwargs):
        if self.duplex is None:
            raise RuntimeError("请先调用 init_unified()")
        return self.duplex.streaming_prefill(**kwargs)

    def duplex_generate(self, **kwargs):
        if self.duplex is None:
            raise RuntimeError("请先调用 init_unified()")
        return self.duplex.streaming_generate(**kwargs)

    def duplex_finalize(self):
        if self.duplex is None:
            raise RuntimeError("请先调用 init_unified()")
        self.duplex.finalize_unit()

    def duplex_set_break(self):
        if self.duplex is None:
            raise RuntimeError("请先调用 init_unified()")
        self.duplex.set_break_event()

    def duplex_clear_break(self):
        if self.duplex is None:
            raise RuntimeError("请先调用 init_unified()")
        self.duplex.clear_break_event()

    def duplex_stop(self):
        if self.duplex is None:
            raise RuntimeError("请先调用 init_unified()")
        self.duplex.set_session_stop()


class GGUFModelWrapper:
    """llama-cpp-python 模型包装器，模拟 transformers 接口"""

    def __init__(self, llm):
        self.llm = llm
        self.config = type("obj", (object,), {"hidden_size": 3584})()
        self.device = "cuda"

    def __call__(self, **kwargs):
        return self.llm(**kwargs)

    def generate(self, **kwargs):
        return self.llm.create_completion(**kwargs)

    def eval(self, **kwargs):
        """GGUF 模型不需要 eval"""
        return self

    def bfloat16(self):
        return self

    def cuda(self):
        return self


class GGUFTokenizer:
    """llama-cpp-python tokenizer 包装器"""

    def __init__(self, llm):
        self.llm = llm
        self.eos_token_id = 151645
        self.unk_token_id = 128244

    def __call__(self, text, **kwargs):
        return self.encode(text, **kwargs)

    def encode(self, text, **kwargs):
        return self.llm.tokenize(text.encode(), special=True)

    def decode(self, token_ids, **kwargs):
        return self.llm.detokenize(token_ids).decode()

    def convert_tokens_to_ids(self, token: str):
        tokens = self.llm.tokenize(token.encode(), special=True)
        return tokens[0] if tokens else self.unk_token_id


class StreamDecoder:
    """流式解码器

    接口完全对齐 MiniCPMO45.utils.StreamDecoder
    """

    def __init__(
        self,
        llm,
        tokenizer,
        special_token_ids=None,
        forbidden_token_ids=None,
        device="cuda",
    ):
        self.m = llm
        self.tokenizer = tokenizer
        self.device = device

        self.listen_id = getattr(tokenizer, "eos_token_id", 151645)
        self.chunk_eos_id = self._get_token_id("<|chunk_eos|>")
        self.chunk_tts_eos_id = self._get_token_id("<|chunk_tts_eos|>")
        self.turn_eos_id = self._get_token_id("<|turn_eos|>")
        self.speak_id = self._get_token_id("<|speak|>")
        self.listen_id = self._get_token_id("<|listen|>")
        self.tts_pad_id = self._get_token_id("<|tts_pad|>")
        self.unit_eos_id = self._get_token_id("</unit>")

        self.forbidden_token_ids = (
            list(forbidden_token_ids) if forbidden_token_ids else []
        )
        if self.chunk_eos_id:
            self.forbidden_token_ids.append(self.chunk_eos_id)

        self.cache = None
        self.generated_tokens = []
        self.generated_special_tokens = []
        self.reset()

        self._window_config = None
        self._window_enabled = True

    def _get_token_id(self, token: str) -> int:
        if hasattr(self.tokenizer, "convert_tokens_to_ids"):
            return self.tokenizer.convert_tokens_to_ids(token)
        return 0

    def reset(self):
        self.cache = None
        self.generated_tokens = []
        self.generated_special_tokens = []

    def get_cache_length(self) -> int:
        if self.cache is None:
            return 0
        if isinstance(self.cache, (list, tuple)):
            return self.cache[0][0].shape[2] if len(self.cache) > 0 else 0
        return 0

    def feed(self, embeds: torch.Tensor, return_logits: bool = False):
        L = embeds.size(0)
        past_len = self.get_cache_length()
        pos_ids = torch.arange(past_len, past_len + L, device=self.device).unsqueeze(0)

        if hasattr(self.m, "llm"):
            out = self.m.llm(
                inputs_embeds=embeds.unsqueeze(0),
                position_ids=pos_ids,
                past_key_values=self.cache,
                return_dict=True,
                output_hidden_states=True,
            )
        else:
            out = self.m(
                inputs_embeds=embeds.unsqueeze(0),
                position_ids=pos_ids,
                past_key_values=self.cache,
                return_dict=True,
                output_hidden_states=True,
            )

        self.cache = out.past_key_values

        if return_logits:
            if hasattr(self.m, "lm_head"):
                logits = self.m.lm_head(out.hidden_states[-1])[:, -1]
            else:
                logits = out.logits[:, -1]
            return logits, out.hidden_states[-1]

    def decode(
        self,
        logits,
        mode: str = "sampling",
        temperature: float = 0.7,
        top_k: int = 20,
        top_p: float = 0.8,
        listen_prob_scale: float = 1.0,
        text_repetition_penalty: float = 1.05,
        text_repetition_window_size: int = 512,
        length_penalty: float = 1.1,
        **kwargs,
    ):
        logits = logits.clone()

        eos_id = self.chunk_eos_id

        if mode == "greedy":
            sampled_token = torch.argmax(logits[0]).item()
        else:
            original_probs = F.softmax(logits[0], dim=-1)
            sampled_token = torch.multinomial(original_probs, num_samples=1).item()

        if sampled_token == eos_id:
            return torch.tensor([eos_id], device=logits.device)

        if self.forbidden_token_ids:
            logits[:, self.forbidden_token_ids] = float("-inf")

        if text_repetition_penalty != 1.0 and len(self.generated_tokens) > 0:
            recent = self.generated_tokens[-text_repetition_window_size:]
            for tok_id in set(recent):
                if tok_id not in self.forbidden_token_ids:
                    logits[:, tok_id] /= text_repetition_penalty

        logits[:, self.listen_id] *= listen_prob_scale

        if mode == "greedy":
            next_token_id = torch.argmax(logits[0]).item()
        else:
            probs = F.softmax(logits[0] / temperature, dim=-1)
            if top_k > 0:
                top_k_vals, top_k_indices = torch.topk(probs, top_k)
                probs = torch.zeros_like(probs)
                probs[top_k_indices] = top_k_vals
                probs /= probs.sum()
            if top_p < 1.0:
                sorted_probs, sorted_indices = torch.sort(probs, descending=True)
                cumsum = torch.cumsum(sorted_probs, dim=-1)
                mask = cumsum > top_p
                mask[1:] = mask[:-1].clone()
                mask[0] = False
                probs[sorted_indices[mask]] = 0
                probs /= probs.sum()
            next_token_id = torch.multinomial(probs, num_samples=1).item()

        self.generated_tokens.append(next_token_id)
        return torch.tensor([next_token_id], device=logits.device)

    def embed_token(self, token_id: int) -> torch.Tensor:
        if hasattr(self.m, "model") and hasattr(self.m.model, "embed_tokens"):
            return self.m.model.embed_tokens(
                torch.tensor([token_id], device=self.device)
            )
        if (
            hasattr(self.m, "llm")
            and hasattr(self.m.llm, "model")
            and hasattr(self.m.llm.model, "embed_tokens")
        ):
            return self.m.llm.model.embed_tokens(
                torch.tensor([token_id], device=self.device)
            )
        raise NotImplementedError("embed_token not supported for this model type")

    def set_window_config(self, config):
        self._window_config = config

    def set_window_enabled(self, enabled: bool):
        self._window_enabled = enabled


class DuplexCapability:
    """双工能力组件

    接口完全对齐 MiniCPMO45.modeling_minicpmo_unified.DuplexCapability
    """

    def __init__(
        self,
        model: MiniCPMO,
        device: str = "cuda",
        generate_audio: bool = True,
        ls_mode: str = "explicit",
        max_new_speak_tokens_per_chunk: int = 20,
        temperature: float = 0.7,
        top_k: int = 20,
        top_p: float = 0.8,
        force_listen_count: int = 3,
        **kwargs,
    ):
        self.model = model
        self.device = device
        self.generate_audio = generate_audio
        self.ls_mode = ls_mode
        self.max_new_speak_tokens_per_chunk = max_new_speak_tokens_per_chunk
        self.temperature = temperature
        self.top_k = top_k
        self.top_p = top_p
        self.force_listen_count = force_listen_count

        self.break_event = threading.Event()
        self.session_stop_event = threading.Event()
        self._streaming_generate_count = 0
        self.current_turn_ended = False
        self.pending_logits = None

        self.decoder = StreamDecoder(
            llm=model.llm, tokenizer=model._tokenizer, device=device
        )

        self._unit_history = []
        self.listen_token_id = self.decoder.listen_id
        self.speak_token_id = self.decoder.speak_id
        self.chunk_eos_id = self.decoder.chunk_eos_id
        self.turn_eos_id = self.decoder.turn_eos_id

    def prepare(self, **kwargs):
        self._streaming_generate_count = 0
        self.break_event.clear()
        self.session_stop_event.clear()
        self.current_turn_ended = False
        self.pending_logits = None
        self.decoder.reset()
        self._unit_history = []

    def streaming_prefill(self, **kwargs):
        audio_waveform = kwargs.get("audio_waveform")
        frame_list = kwargs.get("frame_list")
        text_list = kwargs.get("text_list")
        is_last_chunk = kwargs.get("is_last_chunk", True)

        if (
            audio_waveform is not None
            or frame_list is not None
            or text_list is not None
        ):
            embeds = self._process_input(audio_waveform, frame_list, text_list)
            if embeds is not None:
                logits, hidden = self.decoder.feed(embeds, return_logits=True)
                self.pending_logits = logits

        return {"success": True, "input_tokens": 0}

    def _process_input(self, audio_waveform, frame_list, text_list):
        if text_list:
            text = " ".join(text_list) if isinstance(text_list, list) else text_list
            token_ids = self.model._tokenizer.encode(
                f"<|im_start|>user\n{text}<|im_end|>", special=True
            )
            return self.decoder.embed_token(
                torch.tensor(token_ids, device=self.device)[0]
            )
        return None

    def streaming_generate(
        self,
        decode_mode: str = "sampling",
        temperature: float = None,
        top_k: int = None,
        top_p: float = None,
        listen_prob_scale: float = 1.0,
        force_listen_override: bool = False,
        max_new_speak_tokens_per_chunk: int = None,
        **kwargs,
    ):
        if self.is_session_stop_set():
            return self._make_result(end_of_turn=True)

        if not hasattr(self, "pending_logits") or self.pending_logits is None:
            return self._make_result()

        logits = self.pending_logits
        self.pending_logits = None

        max_tokens = (
            max_new_speak_tokens_per_chunk or self.max_new_speak_tokens_per_chunk
        )
        temperature = temperature or self.temperature
        top_k = top_k or self.top_k
        top_p = top_p or self.top_p

        force_listen = (
            self._streaming_generate_count < self.force_listen_count
            or force_listen_override
        )
        self._streaming_generate_count += 1

        if force_listen_override and not self.current_turn_ended:
            self.decoder.generated_tokens.append(self.turn_eos_id)
            self.current_turn_ended = True

        total_text = []
        is_listen = True

        for _ in range(max_tokens):
            if force_listen:
                next_id = torch.tensor([self.listen_token_id], device=self.device)
            else:
                next_id = self.decoder.decode(
                    logits=logits,
                    mode=decode_mode,
                    temperature=temperature,
                    top_k=top_k,
                    top_p=top_p,
                    listen_prob_scale=listen_prob_scale,
                )

            token_id = next_id.item()
            self.decoder.generated_tokens.append(token_id)

            if token_id == self.chunk_eos_id:
                break

            if token_id == self.listen_token_id:
                is_listen = True
                break

            if token_id == self.speak_token_id:
                is_listen = False
                continue

            if token_id not in [
                self.decoder.listen_id,
                self.decoder.speak_id,
                self.decoder.chunk_eos_id,
                self.decoder.turn_eos_id,
                self.decoder.tts_pad_id,
            ]:
                text = self.model._tokenizer.decode([token_id])
                total_text.append(text)

                embed = self.decoder.embed_token(token_id)
                logits, _ = self.decoder.feed(embed, return_logits=True)

        self.current_turn_ended = token_id == self.turn_eos_id

        return {
            "is_listen": is_listen,
            "text": "".join(total_text),
            "audio": None,
            "end_of_turn": self.current_turn_ended,
        }

    def _make_result(self, end_of_turn: bool = False):
        return {
            "is_listen": True,
            "text": "",
            "audio": None,
            "end_of_turn": end_of_turn,
        }

    def finalize_unit(self):
        unit_len = len(self.decoder.generated_tokens)
        self._unit_history.append(
            {
                "generated_tokens": list(self.decoder.generated_tokens),
                "length": unit_len,
            }
        )

    def set_break_event(self):
        self.break_event.set()

    def clear_break_event(self):
        self.break_event.clear()

    def set_session_stop(self):
        self.session_stop_event.set()

    def is_session_stop_set(self) -> bool:
        return self.session_stop_event.is_set()

    def is_break_set(self) -> bool:
        return self.break_event.is_set()


class TTSSamplingParams:
    """TTS 采样参数"""

    top_p: float = 0.85
    min_p: float = 0.01
    top_k: int = 25
    repetition_penalty: float = 1.05
    temperature: float = 0.8
    win_size: int = 16
    tau_r: float = 0.1
