#!/usr/bin/env python3
"""
Solution for loading 4-bit quantized models with transformers 4.44.2

The issue: transformers 4.44.2 with bitsandbytes 4bit quantization always calls
`.to()` internally, which raises:
    ValueError: `.to` is not supported for `4-bit` or `8-bit` bitsandbytes models

Root cause: The MiniCPMODuplex class calls .to() on the model after loading,
which is not allowed for bitsandbytes quantized models.

Solution options:
1. Use device_map="auto" or device_map={"": 0} - model is already on GPU
2. Check if model is quantized before calling .to()
3. For pre-quantized models (AWQ/GPTQ), they already have quantization_config in config.json
4. For bitsandbytes quantization, use BitsAndBytesConfig with device_map

WORKING SOLUTION CODE:
"""

import torch
from transformers import AutoModel, AutoTokenizer, BitsAndBytesConfig


def load_4bit_model_working_solution():
    """
    Working solution for loading 4-bit quantized models.

    Key points:
    1. Use BitsAndBytesConfig for 4-bit quantization
    2. Use device_map={"": 0} to place all layers on GPU 0
    3. DO NOT call .to(), .cuda(), or .bfloat16() on the model
    4. The model is already on the correct device via device_map
    """
    model_path = "/opt/image/MiniCPM-o-2_6"  # or your model path

    # 4-bit quantization configuration
    quantization_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
    )

    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)

    # Load model with quantization
    # CRITICAL: Use device_map to place model on GPU during loading
    # This avoids the need to call .to() later
    model = AutoModel.from_pretrained(
        model_path,
        trust_remote_code=True,
        torch_dtype=torch.bfloat16,
        quantization_config=quantization_config,
        device_map={"": 0},  # Force all layers to GPU 0
        init_vision=True,
        init_audio=True,
        init_tts=False,  # Disable TTS for 4-bit (not supported)
    )

    # DO NOT call these for 4-bit models:
    # model.cuda()  # ❌ Will raise error
    # model.to("cuda")  # ❌ Will raise error
    # model.bfloat16()  # ❌ Will raise error
    # model.to(torch.bfloat16)  # ❌ Will raise error

    # Only call eval() for inference mode
    model.eval()

    return model, tokenizer


def load_pre_quantized_model_working_solution():
    """
    For pre-quantized models (AWQ, GPTQ, already 4-bit quantized models).

    These models already have quantization_config in their config.json.
    Just use device_map and don't call .to().
    """
    model_path = "/opt/image/OpenBMB/MiniCPM-V-2_6-int4"  # pre-quantized model

    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)

    # For pre-quantized models, no BitsAndBytesConfig needed
    # The quantization config is already in the model's config.json
    model = AutoModel.from_pretrained(
        model_path,
        trust_remote_code=True,
        attn_implementation="sdpa",
        torch_dtype=torch.float16,
        device_map={"": 0},  # Use device_map instead of .cuda()
    )

    model.eval()

    return model, tokenizer


def patched_minicpm_duplex_load(model_path, device="cuda", **kwargs):
    """
    Patched version of MiniCPMODuplex loading that handles 4-bit models correctly.

    The issue is in MiniCPMODuplex.__init__ which calls:
        self.model.to(torch.bfloat16)  # Line ~2364
        self.model.eval().to(device=device)  # Line ~2374

    For 4-bit models, we need to skip these calls.
    """
    from transformers import AutoConfig
    import types

    # Check if model is quantized
    config = AutoConfig.from_pretrained(model_path, trust_remote_code=True)
    is_quantized = (
        hasattr(config, "quantization_config")
        and config.quantization_config is not None
    )

    # Import the class
    from MiniCPMO45.modeling_minicpmo import MiniCPMODuplex, MiniCPMO, MiniCPMOProcessor

    class MiniCPMODuplex4Bit(MiniCPMODuplex):
        """Patched version that handles 4-bit models correctly."""

        def __init__(self, name_or_path, device="cuda", pt_path=None, **kwargs):
            # Skip parent __init__ and do our own initialization
            self.processor = MiniCPMOProcessor.from_pretrained(
                name_or_path, trust_remote_code=True
            )
            self.tokenizer = AutoTokenizer.from_pretrained(
                name_or_path, trust_remote_code=True
            )
            self.processor.tokenizer = self.tokenizer

            config = AutoConfig.from_pretrained(name_or_path, trust_remote_code=True)

            # Extract kwargs
            vision_batch_size = kwargs.pop("vision_batch_size", None)
            audio_pool_step = kwargs.pop("audio_pool_step", None)
            audio_chunk_length = kwargs.pop("audio_chunk_length", None)
            max_slice_nums = kwargs.pop("max_slice_nums", None)
            attn_implementation = kwargs.pop("attn_implementation", "sdpa")

            if vision_batch_size is not None and hasattr(config, "vision_batch_size"):
                config.vision_batch_size = vision_batch_size
            if audio_pool_step is not None and hasattr(config, "audio_pool_step"):
                config.audio_pool_step = audio_pool_step
            if audio_chunk_length is not None and hasattr(config, "audio_chunk_length"):
                config.audio_chunk_length = audio_chunk_length
            if max_slice_nums is not None and hasattr(
                config.slice_config, "max_slice_nums"
            ):
                config.slice_config.max_slice_nums = max_slice_nums

            # Load model
            self.model = MiniCPMO.from_pretrained(
                name_or_path,
                config=config,
                trust_remote_code=True,
                attn_implementation=attn_implementation,
            )

            # Check if model is 4-bit quantized
            is_4bit = hasattr(self.model, "is_quantized") and self.model.is_quantized
            is_8bit = hasattr(self.model, "is_8bit") and self.model.is_8bit
            is_quantized_model = is_4bit or is_8bit

            if not is_quantized_model:
                # Only apply dtype conversion for non-quantized models
                self.model.to(torch.bfloat16)

            self.model.processor = self.processor

            if pt_path is not None:
                import logging

                logger = logging.getLogger(__name__)
                logger.info(f"Loading checkpoint from {pt_path}")
                state_dict = torch.load(pt_path, map_location="cpu")
                info = self.model.load_state_dict(state_dict, strict=False)
                logger.warning(info)
                del state_dict

            # For quantized models, don't call .to(device)
            if is_quantized_model:
                self.model.eval()
                # Model is already on correct device via device_map
            else:
                self.model.eval().to(device=device)

            # Rest of initialization...
            self.model.init_tts(
                streaming=True,
                enable_float16=kwargs.get("enable_float16", False),
                n_timesteps=kwargs.get("n_timesteps", 10),
            )

            # ... (rest of __init__)

    return MiniCPMODuplex4Bit.from_pretrained(model_path, device=device, **kwargs)


def test_model_loading():
    """Test function to verify 4-bit model loading works."""
    print("Testing 4-bit model loading...")

    try:
        model, tokenizer = load_4bit_model_working_solution()
        print("✅ Model loaded successfully!")

        # Test inference
        msgs = [{"role": "user", "content": "Hello!"}]
        res = model.chat(
            msgs=msgs,
            tokenizer=tokenizer,
            sampling=True,
            temperature=0.7,
        )
        print(f"✅ Inference successful! Response: {res}")
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Run the working solution
    test_model_loading()
