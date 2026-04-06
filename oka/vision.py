"""oka - 视觉编码器模块"""

import torch
import torch.nn as nn
from typing import Optional


class SiglipVisionTransformer(nn.Module):
    """Siglip 视觉Transformer

    用于 MiniCPM-o 的视觉编码
    """

    def __init__(self, config):
        super().__init__()
        self.config = config
        # TODO: 实现完整的视觉编码器
        self.embeddings = None
        self.encoder = None

    @classmethod
    def from_gguf(cls, mmproj_path: str):
        """从 GGUF 文件加载视觉编码器"""
        # TODO: 实现 GGUF 加载
        config = {}
        model = cls(config)
        return model

    @classmethod
    def from_pretrained(cls, model_path: str, **kwargs):
        """从 HuggingFace 格式加载"""
        from transformers import AutoModel

        model = AutoModel.from_pretrained(model_path, trust_remote_code=True, **kwargs)
        # 包装成 SiglipVisionTransformer 接口
        wrapper = cls(model.config)
        wrapper.model = model
        return wrapper

    def forward(self, pixel_values):
        """前向传播"""
        if hasattr(self, "model"):
            return self.model(pixel_values)
        raise NotImplementedError("Vision model not initialized")

    def bfloat16(self):
        """转 bfloat16"""
        if hasattr(self, "model"):
            self.model = self.model.bfloat16()
        return self

    def cuda(self):
        """移至 CUDA"""
        if hasattr(self, "model"):
            self.model = self.model.cuda()
        return self
