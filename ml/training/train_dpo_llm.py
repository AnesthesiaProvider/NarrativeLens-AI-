"""Direct Preference Optimization (DPO) Training Pipeline.

Implements reward optimization for hate speech detection and contextual explanation
using Hugging Face TRL (Transformer Reinforcement Learning) and PEFT (QLoRA).

Mathematical Objective:
    L_DPO(theta; pi_ref) = -E_{(x, y_w, y_l)} [ log sigma( beta * log(pi_theta(y_w|x) / pi_ref(y_w|x))
                                                        - beta * log(pi_theta(y_l|x) / pi_ref(y_l|x)) ) ]

Optimized for NVIDIA RTX 4050 (6GB VRAM) using:
  - 4-bit Quantization (BitsAndBytes NF4)
  - LoRA rank adaptation (r=8, alpha=16)
  - Gradient accumulation and FP16 mixed precision
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
import sys
from typing import Dict, List

import torch
from datasets import load_dataset
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
)
from trl import DPOConfig, DPOTrainer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("train_dpo_llm")


def format_dpo_sample(sample: Dict[str, str]) -> Dict[str, str]:
    """Ensure standard prompt, chosen, rejected fields."""
    return {
        "prompt": sample["prompt"],
        "chosen": sample["chosen"],
        "rejected": sample["rejected"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run DPO fine-tuning on local safety preference pairs.")
    parser.add_argument("--base_model", type=str, default="Qwen/Qwen2.5-3B-Instruct", help="Base causal LLM")
    parser.add_argument("--train_file", type=str, default="ml/datasets/dpo_preference_train.jsonl")
    parser.add_argument("--val_file", type=str, default="ml/datasets/dpo_preference_val.jsonl")
    parser.add_argument("--output_dir", type=str, default="ml/checkpoints/reward-optimized-llm")
    parser.add_argument("--epochs", type=int, default=2)
    parser.add_argument("--batch_size", type=int, default=1)
    parser.add_argument("--grad_accum", type=int, default=4)
    parser.add_argument("--learning_rate", type=float, default=5e-5)
    parser.add_argument("--beta", type=float, default=0.1, help="DPO implicit reward temperature")
    args = parser.parse_args()

    output_path = Path(args.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 60)
    logger.info("NARRATIVELENS AI - DIRECT PREFERENCE OPTIMIZATION (DPO)")
    logger.info("=" * 60)
    logger.info(f"Base LLM           : {args.base_model}")
    logger.info(f"DPO Beta           : {args.beta}")
    logger.info(f"Effective Batch    : {args.batch_size * args.grad_accum}")
    logger.info(f"Output Directory   : {output_path.resolve()}")
    logger.info("=" * 60)

    # 1. Load preference dataset
    logger.info("Loading preference dataset from disk...")
    train_ds = load_dataset("json", data_files=args.train_file, split="train")
    val_ds = load_dataset("json", data_files=args.val_file, split="train")

    logger.info(f"Loaded {len(train_ds)} training pairs, {len(val_ds)} validation pairs.")

    # 2. Tokenizer
    logger.info(f"Loading tokenizer for {args.base_model}...")
    tokenizer = AutoTokenizer.from_pretrained(args.base_model)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # 3. 4-bit Quantization Configuration (QLoRA)
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    )

    # 4. Load Base Model in 4-bit
    logger.info("Loading model weights in 4-bit precision for RTX 4050 VRAM optimization...")
    model = AutoModelForCausalLM.from_pretrained(
        args.base_model,
        quantization_config=bnb_config,
        device_map="auto",
        torch_dtype=torch.float16,
    )
    model = prepare_model_for_kbit_training(model)

    # 5. LoRA Configuration
    peft_config = LoraConfig(
        r=8,
        lora_alpha=16,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    )

    # 6. DPO Configuration
    dpo_args = DPOConfig(
        output_dir=str(output_path),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.learning_rate,
        beta=args.beta,
        logging_steps=1,
        eval_strategy="epoch",
        save_strategy="epoch",
        fp16=True,
        report_to="none",
        max_length=512,
        max_prompt_length=256,
        remove_unused_columns=False,
    )

    # 7. Initialize DPOTrainer
    logger.info("Initializing DPOTrainer...")
    trainer = DPOTrainer(
        model=model,
        ref_model=None,  # Implicit reference model handled by TRL when using PEFT
        args=dpo_args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        processing_class=tokenizer,
        peft_config=peft_config,
    )

    # 8. Run DPO training
    logger.info("Starting DPO training optimization loop...")
    trainer.train()

    # 9. Save adapted policy
    logger.info(f"Saving reward-optimized adapter to {output_path}...")
    trainer.save_model(str(output_path))
    tokenizer.save_pretrained(str(output_path))

    logger.info("=" * 60)
    logger.info("DIRECT PREFERENCE OPTIMIZATION COMPLETE")
    logger.info(f"Reward-optimized policy weights saved to: {output_path.resolve()}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
