"""oka - MiniCPM-o GGUF 推理引擎

接口完全对齐 MiniCPMO45.modeling_minicpmo_unified
"""

__version__ = "0.1.0"

from oka.minicpmo import (
    MiniCPMO,
    DuplexCapability,
    StreamDecoder,
    ProcessorMode,
    TTSSamplingParams,
)
from oka.processor import UnifiedProcessor

__all__ = [
    "MiniCPMO",
    "DuplexCapability",
    "StreamDecoder",
    "ProcessorMode",
    "TTSSamplingParams",
    "UnifiedProcessor",
]
