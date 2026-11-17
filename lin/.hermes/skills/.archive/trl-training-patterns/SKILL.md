---
name: trl-training-patterns
description: TRL (Transformer Reinforcement Learning) training patterns — SFTTrainer, SFTConfig, parameter gotchas, AMD/NVIDIA/CPU auto-detection, and LoRA setup for modern TRL 1.7+
---

# TRL Training Patterns

Parameter gotchas and patterns for TRL 1.7+ (transformers 5.x). Applies to any fine-tuning task using `SFTTrainer`, not just RSI.

## SFTTrainer vs Trainer

In TRL 1.7+, use `SFTConfig` (not `TrainingArguments`) and `SFTTrainer` (not bare `Trainer`):

```python
from trl import SFTTrainer, SFTConfig
from peft import LoraConfig, get_peft_model

config = SFTConfig(
    output_dir="adapters/",
    num_train_epochs=3,
    per_device_train_batch_size=1,
    gradient_accumulation_steps=4,
    learning_rate=0.0002,         # NOT 2e-4 (YAML string bug!)
    eval_strategy="steps",        # NOT evaluation_strategy
    eval_steps=10,
    save_strategy="steps",
    save_steps=20,                # must be multiple of eval_steps
    max_length=2048,              # NOT max_seq_length
    bf16=use_gpu,
    fp16=False,
    warmup_steps=N,               # NOT warmup_ratio (deprecated in v5.2)
)

trainer = SFTTrainer(
    model=model,
    processing_class=tokenizer,   # NOT tokenizer=
    args=config,
    train_dataset=train,
    eval_dataset=eval,
)
```

## Parameter Renames (TRL 1.7+ / Transformers 5.x)

| Old Name | New Name | When |
|----------|----------|------|
| `tokenizer=` | `processing_class=` | SFTTrainer init |
| `evaluation_strategy=` | `eval_strategy=` | Any config |
| `TrainingArguments` | `SFTConfig` | When using SFTTrainer |
| `max_seq_length=` | `max_length=` | SFTConfig |
| `warmup_ratio=` | `warmup_steps=` | Deprecated v5.2 |
| `no_cuda=` | Remove — set `CUDA_VISIBLE_DEVICES=""` env var | Removed from TrainingArgs |
| `torch_dtype=` | `dtype=` | Deprecated (use kwargs) |
| `packing=` in TrainingArgs | Not a TrainingArgs param | Remove from config |

## GPU Detection Pattern

```python
import torch, os

# Detect AMD vs NVIDIA
is_amd = torch.version.hip is not None
use_gpu = torch.cuda.is_available()

if is_amd:
    os.environ.setdefault("HSA_OVERRIDE_GFX_VERSION", "8.0.3")  # RX 580 Polaris
    os.environ.setdefault("PYTORCH_ROCM_ARCH", "gfx803")

if use_gpu:
    try:
        torch.zeros(1).cuda()
        gpu_name = torch.cuda.get_device_name(0)
    except:
        use_gpu = False  # GPU detected but unusable (e.g. MX150 sm_61)
```

## Model Loading by GPU Type

```python
if use_gpu and is_amd:
    # AMD — no quantization (enough VRAM), fp16 direct
    model = AutoModelForCausalLM.from_pretrained(..., device_map="auto", torch_dtype=torch.float16)
elif use_gpu and not is_amd:
    # NVIDIA — 4-bit QLoRA (bitsandbytes)
    from transformers import BitsAndBytesConfig
    from peft import prepare_model_for_kbit_training
    bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", ...)
    model = AutoModelForCausalLM.from_pretrained(..., quantization_config=bnb, device_map="auto")
    model = prepare_model_for_kbit_training(model)
else:
    # CPU — fp32, no quantization
    model = AutoModelForCausalLM.from_pretrained(..., device_map="cpu", torch_dtype=torch.float32)
```

## Load Best Model Validation

`load_best_model_at_end=True` requires `save_steps` to be a round multiple of `eval_steps`:

```python
total_steps = train_steps_per_epoch * num_epochs
eval_every = max(1, total_steps // 6)
save_every = eval_every * 2  # must be multiple of eval_every
```

## YAML Numeric Values

PyYAML parses `2e-4` as a **string**, not a float. Always use explicit decimal:

```yaml
# WRONG — parses as string "2e-4"
learning_rate: 2e-4

# RIGHT — parses as float 0.0002
learning_rate: 0.0002
```

Same applies to any scientific notation in YAML configs.

## Optimizer Selection

| GPU type | Optimizer | Reason |
|----------|-----------|--------|
| NVIDIA | `adamw_8bit` | Works with bitsandbytes |
| AMD / CPU | `adamw_torch` | No bitsandbytes on non-NVIDIA |
