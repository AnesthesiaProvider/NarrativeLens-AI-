"""
NarrativeLens AI - Hate Speech Classifier Training Pipeline
Fine-tunes XLM-RoBERTa (FacebookAI/xlm-roberta-base) for 3-class hate speech classification.

Classes:
  0: normal
  1: offensive
  2: hate

Optimized for NVIDIA RTX 4050 (6GB VRAM) using:
  - FP16 mixed precision
  - Gradient accumulation
  - PyTorch CUDA memory management
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import random
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import torch
import yaml
from datasets import Dataset
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_recall_fscore_support
from transformers import (
    AutoConfig,
    AutoModelForSequenceClassification,
    AutoTokenizer,
    DataCollatorWithPadding,
    EarlyStoppingCallback,
    Trainer,
    TrainerCallback,
    TrainingArguments,
    set_seed as hf_set_seed,
)

from ml.training.focal_loss import FocalLoss

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("train_classifier")

LABEL_LIST = ["normal", "offensive", "hate"]
LABEL2ID = {"normal": 0, "offensive": 1, "hate": 2}
ID2LABEL = {0: "normal", 1: "offensive", 2: "hate"}


def set_all_seeds(seed: int = 42) -> None:
    """Set seeds across Python, NumPy, PyTorch, and Transformers for reproducibility."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    hf_set_seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)


class FocalLossTrainer(Trainer):
    """Custom Trainer subclass using Class-Weighted Focal Loss instead of standard Cross-Entropy."""

    def __init__(self, *args, focal_gamma: float = 2.0, class_weights: Optional[torch.Tensor] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.focal_loss_fn = FocalLoss(gamma=focal_gamma, weight=class_weights)

    def compute_loss(self, model, inputs, return_outputs=False, num_items_in_batch=None):
        labels = inputs.pop("labels")
        outputs = model(**inputs)
        logits = outputs.logits
        loss = self.focal_loss_fn(logits, labels)
        return (loss, outputs) if return_outputs else loss


class MetricsLoggingCallback(TrainerCallback):
    """Callback to log metrics and loss progression cleanly during training."""

    def __init__(self) -> None:
        self.training_logs: List[Dict[str, Any]] = []

    def on_log(self, args: Any, state: Any, control: Any, logs: Optional[Dict[str, Any]] = None, **kwargs: Any) -> None:
        if logs:
            self.training_logs.append(dict(logs))
            if "loss" in logs:
                step = state.global_step
                logger.info(f"Step {step} | Loss: {logs['loss']:.4f}")
            if "eval_loss" in logs:
                logger.info(
                    f"Epoch {logs.get('epoch', 0):.1f} Eval | "
                    f"Loss: {logs['eval_loss']:.4f} | "
                    f"Macro F1: {logs.get('eval_macro_f1', 0.0):.4f} | "
                    f"Accuracy: {logs.get('eval_accuracy', 0.0):.4f}"
                )


def compute_metrics(eval_pred: Any) -> Dict[str, float]:
    """Compute classification metrics for evaluation."""
    predictions, labels = eval_pred
    preds = np.argmax(predictions, axis=1)

    acc = float(accuracy_score(labels, preds))
    macro_f1 = float(f1_score(labels, preds, average="macro", zero_division=0))
    weighted_f1 = float(f1_score(labels, preds, average="weighted", zero_division=0))

    precision, recall, f1, _ = precision_recall_fscore_support(
        labels, preds, average=None, labels=[0, 1, 2], zero_division=0
    )

    return {
        "accuracy": round(acc, 4),
        "macro_f1": round(macro_f1, 4),
        "weighted_f1": round(weighted_f1, 4),
        "normal_precision": round(float(precision[0]), 4),
        "normal_recall": round(float(recall[0]), 4),
        "normal_f1": round(float(f1[0]), 4),
        "offensive_precision": round(float(precision[1]), 4),
        "offensive_recall": round(float(recall[1]), 4),
        "offensive_f1": round(float(f1[1]), 4),
        "hate_precision": round(float(precision[2]), 4),
        "hate_recall": round(float(recall[2]), 4),
        "hate_f1": round(float(f1[2]), 4),
    }


def load_dataset_split(
    file_path: Path, max_samples: Optional[int] = None
) -> pd.DataFrame:
    """Load and validate dataset split CSV."""
    if not file_path.exists():
        raise FileNotFoundError(
            f"Dataset file not found: {file_path}. "
            "Please run 'python ml/datasets/download_datasets.py' first."
        )

    df = pd.read_csv(file_path)
    if "text" not in df.columns or "label" not in df.columns:
        raise ValueError(f"Dataset at {file_path} must contain 'text' and 'label' columns.")

    df = df.dropna(subset=["text", "label"])
    df["text"] = df["text"].astype(str).str.strip()
    df = df[df["text"].str.len() > 0]

    # Map labels to integer IDs
    if df["label"].dtype == object or isinstance(df["label"].iloc[0], str):
        df["label"] = df["label"].map(LABEL2ID)

    df = df.dropna(subset=["label"])
    df["label"] = df["label"].astype(int)

    if max_samples and len(df) > max_samples:
        df = df.sample(n=max_samples, random_state=42)

    return df


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train XLM-RoBERTa Hate Speech Classifier.")
    parser.add_argument("--config", type=str, default="ml/training/train_config.yaml", help="Path to YAML training configuration")
    parser.add_argument("--model_name", type=str, default="FacebookAI/xlm-roberta-base", help="Hugging Face base model name or path")
    parser.add_argument("--epochs", type=int, default=3, help="Number of training epochs")
    parser.add_argument("--batch_size", type=int, default=16, help="Per-device train and eval batch size")
    parser.add_argument("--learning_rate", type=float, default=2e-5, help="Peak learning rate for AdamW")
    parser.add_argument("--max_length", type=int, default=128, help="Maximum token sequence length")
    parser.add_argument("--warmup_ratio", type=float, default=0.1, help="Linear warmup ratio")
    parser.add_argument("--weight_decay", type=float, default=0.01, help="Weight decay for regularization")
    parser.add_argument("--output_dir", type=str, default="ml/checkpoints/xlm-roberta-hate-speech", help="Directory to save checkpoints")
    parser.add_argument("--device", type=str, default="auto", help="Compute device ('cuda', 'cpu', or 'auto')")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--gradient_accumulation_steps", type=int, default=2, help="Steps for gradient accumulation")
    parser.add_argument("--fp16", action="store_true", default=True, help="Enable FP16 mixed precision training")
    parser.add_argument("--no_fp16", action="store_false", dest="fp16", help="Disable FP16 mixed precision")
    parser.add_argument("--max_train_samples", type=int, default=None, help="Optional max training samples for quick smoke testing")
    parser.add_argument("--max_eval_samples", type=int, default=None, help="Optional max validation samples")
    parser.add_argument("--save_total_limit", type=int, default=3, help="Max checkpoints to keep")
    parser.add_argument("--train_path", type=str, default="ml/datasets/train.csv", help="Path to training CSV")
    parser.add_argument("--val_path", type=str, default="ml/datasets/val.csv", help="Path to validation CSV")
    parser.add_argument("--test_path", type=str, default="ml/datasets/test.csv", help="Path to test CSV")

    args = parser.parse_args()

    # Load YAML overrides if config file exists
    if args.config and Path(args.config).exists():
        try:
            with open(args.config, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f)
            if cfg:
                model_cfg = cfg.get("model", {})
                train_cfg = cfg.get("training", {})
                data_cfg = cfg.get("data", {})
                out_cfg = cfg.get("output", {})

                if "name" in model_cfg:
                    args.model_name = model_cfg["name"]
                if "max_length" in model_cfg:
                    args.max_length = model_cfg["max_length"]

                if "epochs" in train_cfg:
                    args.epochs = train_cfg["epochs"]
                if "batch_size" in train_cfg:
                    args.batch_size = train_cfg["batch_size"]
                if "learning_rate" in train_cfg:
                    args.learning_rate = float(train_cfg["learning_rate"])
                if "warmup_ratio" in train_cfg:
                    args.warmup_ratio = float(train_cfg["warmup_ratio"])
                if "weight_decay" in train_cfg:
                    args.weight_decay = float(train_cfg["weight_decay"])
                if "gradient_accumulation_steps" in train_cfg:
                    args.gradient_accumulation_steps = train_cfg["gradient_accumulation_steps"]
                if "fp16" in train_cfg:
                    args.fp16 = bool(train_cfg["fp16"])
                if "seed" in train_cfg:
                    args.seed = train_cfg["seed"]

                if "train_path" in data_cfg:
                    args.train_path = data_cfg["train_path"]
                if "val_path" in data_cfg:
                    args.val_path = data_cfg["val_path"]
                if "test_path" in data_cfg:
                    args.test_path = data_cfg["test_path"]

                if "dir" in out_cfg:
                    args.output_dir = out_cfg["dir"]
                if "save_total_limit" in out_cfg:
                    args.save_total_limit = out_cfg["save_total_limit"]
                logger.info(f"Loaded config parameters from {args.config}")
        except Exception as exc:
            logger.warning(f"Could not parse config file {args.config}: {exc}")

    return args


def main() -> None:
    args = parse_arguments()
    set_all_seeds(args.seed)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Resolve device and mixed precision
    cuda_available = torch.cuda.is_available()
    use_fp16 = args.fp16 and cuda_available

    logger.info("=" * 60)
    logger.info("NARRATIVELENS AI - TRAINING PIPELINE")
    logger.info("=" * 60)
    logger.info(f"Base Model              : {args.model_name}")
    logger.info(f"CUDA Available          : {cuda_available}")
    if cuda_available:
        logger.info(f"GPU Device              : {torch.cuda.get_device_name(0)}")
        logger.info(f"Total VRAM              : {torch.cuda.get_device_properties(0).total_memory / (1024**3):.2f} GB")
    logger.info(f"Mixed Precision (FP16)  : {use_fp16}")
    logger.info(f"Batch Size              : {args.batch_size} (Grad Accum: {args.gradient_accumulation_steps})")
    logger.info(f"Effective Batch Size    : {args.batch_size * args.gradient_accumulation_steps}")
    logger.info(f"Epochs                  : {args.epochs}")
    logger.info(f"Learning Rate           : {args.learning_rate}")
    logger.info(f"Max Sequence Length     : {args.max_length}")
    logger.info(f"Output Directory        : {output_dir.resolve()}")
    logger.info("=" * 60)

    # 1. Load Data Splits
    logger.info("Loading training, validation, and testing datasets...")
    train_df = load_dataset_split(Path(args.train_path), max_samples=args.max_train_samples)
    val_df = load_dataset_split(Path(args.val_path), max_samples=args.max_eval_samples)
    test_df = load_dataset_split(Path(args.test_path), max_samples=args.max_eval_samples)

    logger.info(f"Train samples: {len(train_df)} | Class counts: {train_df['label'].value_counts().to_dict()}")
    logger.info(f"Val samples  : {len(val_df)} | Class counts: {val_df['label'].value_counts().to_dict()}")
    logger.info(f"Test samples : {len(test_df)} | Class counts: {test_df['label'].value_counts().to_dict()}")

    # 2. Load Tokenizer & Model
    logger.info(f"Loading tokenizer for '{args.model_name}'...")
    tokenizer = AutoTokenizer.from_pretrained(args.model_name)

    logger.info(f"Loading sequence classification model for '{args.model_name}' (3 classes)...")
    config = AutoConfig.from_pretrained(
        args.model_name,
        num_labels=3,
        id2label=ID2LABEL,
        label2id=LABEL2ID,
        problem_type="single_label_classification",
    )
    model = AutoModelForSequenceClassification.from_pretrained(
        args.model_name,
        config=config,
    )

    # 3. Tokenize Datasets
    def tokenize_batch(examples: Dict[str, List[Any]]) -> Dict[str, Any]:
        return tokenizer(
            examples["text"],
            max_length=args.max_length,
            truncation=True,
            padding=False,
        )

    logger.info("Tokenizing splits...")
    hf_train = Dataset.from_pandas(train_df[["text", "label"]])
    hf_val = Dataset.from_pandas(val_df[["text", "label"]])
    hf_test = Dataset.from_pandas(test_df[["text", "label"]])

    train_tokenized = hf_train.map(tokenize_batch, batched=True, remove_columns=["text"])
    val_tokenized = hf_val.map(tokenize_batch, batched=True, remove_columns=["text"])
    test_tokenized = hf_test.map(tokenize_batch, batched=True, remove_columns=["text"])

    data_collator = DataCollatorWithPadding(tokenizer=tokenizer)

    # 4. Training Arguments
    training_kwargs: Dict[str, Any] = {
        "output_dir": str(output_dir),
        "num_train_epochs": args.epochs,
        "per_device_train_batch_size": args.batch_size,
        "per_device_eval_batch_size": args.batch_size,
        "learning_rate": args.learning_rate,
        "warmup_ratio": args.warmup_ratio,
        "weight_decay": args.weight_decay,
        "gradient_accumulation_steps": args.gradient_accumulation_steps,
        "fp16": use_fp16,
        "seed": args.seed,
        "save_total_limit": args.save_total_limit,
        "load_best_model_at_end": True,
        "metric_for_best_model": "macro_f1",
        "greater_is_better": True,
        "logging_steps": 10,
        "report_to": "none",
    }

    try:
        training_args = TrainingArguments(eval_strategy="epoch", save_strategy="epoch", **training_kwargs)
    except TypeError:
        training_args = TrainingArguments(evaluation_strategy="epoch", save_strategy="epoch", **training_kwargs)

    metrics_cb = MetricsLoggingCallback()
    early_stop_cb = EarlyStoppingCallback(early_stopping_patience=2)

    # 4b. Compute inverse frequency class weights to balance gradient signals
    train_labels = train_df["label"].tolist()
    class_counts = np.bincount(train_labels, minlength=3)
    total_samples = len(train_labels)
    # Balanced weights: total / (num_classes * count)
    weights = total_samples / (3.0 * class_counts)
    class_weights_tensor = torch.tensor(weights, dtype=torch.float32)
    logger.info(f"Computed Focal Loss class weights: normal={weights[0]:.3f}, offensive={weights[1]:.3f}, hate={weights[2]:.3f}")

    # 5. Trainer Setup with Focal Loss
    trainer = FocalLossTrainer(
        model=model,
        args=training_args,
        train_dataset=train_tokenized,
        eval_dataset=val_tokenized,
        processing_class=tokenizer,
        data_collator=data_collator,
        compute_metrics=compute_metrics,
        callbacks=[metrics_cb, early_stop_cb],
        focal_gamma=2.0,
        class_weights=class_weights_tensor,
    )

    # 6. Execute Training
    logger.info("Starting training loop...")
    train_result = trainer.train()

    logger.info("Training complete. Saving best model and tokenizer...")
    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))

    # Save training metrics history
    training_metrics_path = output_dir / "training_metrics.json"
    with open(training_metrics_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "train_runtime_seconds": round(train_result.metrics.get("train_runtime", 0.0), 2),
                "train_samples_per_second": round(train_result.metrics.get("train_samples_per_second", 0.0), 2),
                "total_steps": train_result.global_step,
                "history": metrics_cb.training_logs,
            },
            f,
            indent=2,
        )
    logger.info(f"Saved training history to {training_metrics_path}")

    # 7. Validation Evaluation
    logger.info("Running evaluation on validation set...")
    val_metrics = trainer.evaluate(eval_dataset=val_tokenized, metric_key_prefix="val")
    logger.info(f"Validation Metrics: {val_metrics}")

    # 8. Test Set Evaluation & Confusion Matrix
    logger.info("Evaluating on held-out test set...")
    test_predictions = trainer.predict(test_tokenized, metric_key_prefix="test")
    test_metrics = test_predictions.metrics
    logger.info(f"Test Metrics: {test_metrics}")

    # Compute and save confusion matrix
    preds = np.argmax(test_predictions.predictions, axis=1)
    true_labels = test_tokenized["label"]
    cm = confusion_matrix(true_labels, preds, labels=[0, 1, 2]).tolist()

    cm_data = {
        "labels": LABEL_LIST,
        "matrix": cm,
        "description": "Rows represent Ground Truth, Columns represent Model Predictions",
    }
    cm_path = output_dir / "confusion_matrix.json"
    with open(cm_path, "w", encoding="utf-8") as f:
        json.dump(cm_data, f, indent=2)
    logger.info(f"Saved confusion matrix to {cm_path}")

    # Save complete evaluation metrics
    eval_results_path = output_dir / "eval_results.json"
    with open(eval_results_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "model_name": args.model_name,
                "validation": val_metrics,
                "test": test_metrics,
                "confusion_matrix": cm_data,
            },
            f,
            indent=2,
        )
    logger.info(f"Saved all evaluation results to {eval_results_path}")

    print("\n" + "=" * 60)
    print("TRAINING & EVALUATION COMPLETE")
    print("=" * 60)
    print(f"Best Model Checkpoint: {output_dir.resolve()}")
    print(f"Test Macro F1        : {test_metrics.get('test_macro_f1', 0.0):.4f}")
    print(f"Test Accuracy        : {test_metrics.get('test_accuracy', 0.0):.4f}")
    print(f"Confusion Matrix     : {cm}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
