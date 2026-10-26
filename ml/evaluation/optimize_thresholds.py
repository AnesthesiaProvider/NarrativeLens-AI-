"""Optimal Decision Threshold Tuner for Hate Speech Classification.

Finds the optimal per-class probability scaling thresholds (tau_normal, tau_offensive, tau_hate)
using Nelder-Mead simplex optimization on validation set logits.

Standard argmax(probabilities) assumes equal costs and uniform calibration.
By dividing probabilities by class-specific thresholds:
    y_pred = argmax_c ( P(c) / tau_c )
we penalize false offensive predictions and directly maximize Macro-F1.

Outputs:
    ml/checkpoints/xlm-roberta-hate-speech/calibrated_thresholds.json
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from sklearn.metrics import f1_score, precision_recall_fscore_support
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("optimize_thresholds")

LABEL2ID = {"normal": 0, "offensive": 1, "hate": 2}
ID2LABEL = {0: "normal", 1: "offensive", 2: "hate"}


def predict_probabilities(
    model: AutoModelForSequenceClassification,
    tokenizer: AutoTokenizer,
    texts: List[str],
    batch_size: int = 32,
    device: str = "cuda",
) -> np.ndarray:
    """Compute softmax probability distributions for a list of texts."""
    model.eval()
    all_probs = []

    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i : i + batch_size]
        inputs = tokenizer(
            batch_texts,
            padding=True,
            truncation=True,
            max_length=128,
            return_tensors="pt",
        )
        inputs = {k: v.to(device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = model(**inputs)
            probs = torch.softmax(outputs.logits, dim=-1).cpu().numpy()
            all_probs.append(probs)

    return np.concatenate(all_probs, axis=0)


def evaluate_with_thresholds(probs: np.ndarray, thresholds: np.ndarray) -> np.ndarray:
    """Scale probabilities by thresholds and take argmax."""
    scaled = probs / (thresholds + 1e-9)
    return np.argmax(scaled, axis=1)


def objective(thresholds: np.ndarray, probs: np.ndarray, true_labels: np.ndarray) -> float:
    """Negative Macro-F1 objective function for minimization."""
    preds = evaluate_with_thresholds(probs, thresholds)
    score = f1_score(true_labels, preds, average="macro", zero_division=0)
    return -score


def main() -> None:
    checkpoint_dir = Path("ml/checkpoints/xlm-roberta-hate-speech")
    val_path = Path("ml/datasets/val.csv")
    test_path = Path("ml/datasets/test.csv")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"Loading checkpoint from {checkpoint_dir} on {device}...")

    tokenizer = AutoTokenizer.from_pretrained(str(checkpoint_dir))
    model = AutoModelForSequenceClassification.from_pretrained(str(checkpoint_dir)).to(device)

    # 1. Load validation set
    logger.info(f"Loading validation data from {val_path}...")
    val_df = pd.read_csv(val_path)
    val_texts = val_df["text"].astype(str).tolist()
    val_labels = val_df["label"].map(LABEL2ID).to_numpy()

    logger.info("Computing validation probability distributions...")
    val_probs = predict_probabilities(model, tokenizer, val_texts, device=device)

    # 2. Baseline performance (uniform thresholds [1.0, 1.0, 1.0])
    base_preds = np.argmax(val_probs, axis=1)
    base_f1 = f1_score(val_labels, base_preds, average="macro")
    logger.info(f"Baseline Validation Macro-F1 (uniform argmax): {base_f1:.4f}")

    # 3. Optimize thresholds using Nelder-Mead
    logger.info("Optimizing threshold vector [tau_normal, tau_offensive, tau_hate]...")
    initial_thresholds = np.array([1.0, 1.0, 1.0])
    bounds = [(0.2, 2.5), (0.2, 2.5), (0.2, 2.5)]

    res = minimize(
        objective,
        initial_thresholds,
        args=(val_probs, val_labels),
        method="Nelder-Mead",
        options={"maxiter": 300, "disp": False},
    )

    opt_thresholds = res.x / np.sum(res.x)  # normalize
    opt_val_preds = evaluate_with_thresholds(val_probs, opt_thresholds)
    opt_val_f1 = f1_score(val_labels, opt_val_preds, average="macro")
    logger.info(f"Optimized Validation Macro-F1: {opt_val_f1:.4f} (Delta: +{(opt_val_f1 - base_f1)*100:.2f}%)")
    logger.info(f"Optimal Thresholds: normal={opt_thresholds[0]:.4f}, offensive={opt_thresholds[1]:.4f}, hate={opt_thresholds[2]:.4f}")

    # 4. Evaluate on held-out test set
    logger.info(f"Evaluating optimal thresholds on held-out test set ({test_path})...")
    test_df = pd.read_csv(test_path)
    test_texts = test_df["text"].astype(str).tolist()
    test_labels = test_df["label"].map(LABEL2ID).to_numpy()

    test_probs = predict_probabilities(model, tokenizer, test_texts, device=device)

    test_base_preds = np.argmax(test_probs, axis=1)
    test_base_f1 = f1_score(test_labels, test_base_preds, average="macro")

    test_opt_preds = evaluate_with_thresholds(test_probs, opt_thresholds)
    test_opt_f1 = f1_score(test_labels, test_opt_preds, average="macro")

    p, r, f1, _ = precision_recall_fscore_support(test_labels, test_opt_preds, average=None, zero_division=0)

    logger.info("=" * 60)
    logger.info("TEST SET EVALUATION RESULTS:")
    logger.info(f"Baseline Test Macro-F1 : {test_base_f1:.4f}")
    logger.info(f"Optimized Test Macro-F1: {test_opt_f1:.4f} (Delta: +{(test_opt_f1 - test_base_f1)*100:.2f}%)")
    logger.info(f"Per-Class F1 - Normal: {f1[0]:.4f}, Offensive: {f1[1]:.4f}, Hate: {f1[2]:.4f}")
    logger.info("=" * 60)

    # 5. Save thresholds to JSON
    output_file = checkpoint_dir / "calibrated_thresholds.json"
    threshold_data = {
        "optimal_thresholds": {
            "normal": round(float(opt_thresholds[0]), 4),
            "offensive": round(float(opt_thresholds[1]), 4),
            "hate": round(float(opt_thresholds[2]), 4),
        },
        "validation_macro_f1": round(float(opt_val_f1), 4),
        "test_macro_f1": round(float(opt_opt_f1 := test_opt_f1), 4),
        "f1_improvement": round(float((test_opt_f1 - test_base_f1) * 100), 2),
        "per_class_f1": {
            "normal": round(float(f1[0]), 4),
            "offensive": round(float(f1[1]), 4),
            "hate": round(float(f1[2]), 4),
        },
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(threshold_data, f, indent=2)

    logger.info(f"Calibrated threshold profile saved to {output_file}")


if __name__ == "__main__":
    main()
