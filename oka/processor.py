"""oka - MiniCPM-o 统一处理器"""

from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class UnifiedProcessor:
    """统一处理器

    接口完全对齐 core.processors.unified.UnifiedProcessor
    """

    def __init__(
        self,
        model_path: str,
        pt_path: str = None,
        ref_audio_path: str = None,
        compile: bool = False,
        chat_vocoder: str = "token2wav",
        attn_implementation: str = "auto",
        duplex_config: dict = None,
        device: str = "cuda",
        preload_both_tts: bool = True,
        **kwargs,
    ):
        self.model_path = model_path
        self.pt_path = pt_path
        self.ref_audio_path = ref_audio_path
        self.compile = compile
        self.chat_vocoder = chat_vocoder
        self.attn_implementation = attn_implementation
        self.device = device

        # 加载模型
        from oka.minicpmo import MiniCPMO

        self.model = MiniCPMO.from_pretrained(
            model_path=model_path,
            trust_remote_code=True,
            _attn_implementation=attn_implementation,
        )

        # 初始化统一模式
        if duplex_config is None:
            duplex_config = {
                "generate_audio": True,
                "ls_mode": "explicit",
                "max_new_speak_tokens_per_chunk": 20,
            }

        self.model.init_unified(
            pt_path=pt_path,
            preload_both_tts=preload_both_tts,
            duplex_config=duplex_config,
            device=device,
            chat_vocoder=chat_vocoder,
        )

        logger.info(f"UnifiedProcessor initialized with model: {model_path}")

    def set_chat_mode(self):
        """设置聊天模式"""
        from oka.minicpmo import ProcessorMode

        self.model.set_mode(ProcessorMode.CHAT)
        return self

    def set_streaming_mode(self):
        """设置流式模式"""
        from oka.minicpmo import ProcessorMode

        self.model.set_mode(ProcessorMode.STREAMING)
        return self

    def set_duplex_mode(self):
        """设置双工模式"""
        from oka.minicpmo import ProcessorMode

        self.model.set_mode(ProcessorMode.DUPLEX)
        return self
