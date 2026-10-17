"""
NarrativeLens AI - Hate Speech Classifier Evaluation Suite

Computes comprehensive evaluation metrics on held-out test data:
  - Accuracy, Macro-F1, Weighted-F1
  - Per-class Precision, Recall, and F1 scores
  - Confusion Matrix
  - Expected Calibration Error (ECE) for model confidence reliability
  - Detailed Sklearn Classification Report
  - Saves full JSON analysis
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
)
from transformers import AutoConfig, AutoModelForSequenceClassification, AutoTokenizer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("evaluate_model")

LABEL_LIST = ["normal", "offensive", "hate"]
LABEL2ID = {"normal": 0, "offensive": 1, "hate": 2}
ID2LABEL = {0: "normal", 1: "offensive", 2: "hate"}


def compute_ece(
    confidences: np.ndarray,
    predictions: np.ndarray,
    labels: np.ndarray,
    n_bins: int = 10,
) -> Dict[str, Any]:
    """
    Calculate Expected Calibration Error (ECE) across confidence bins.
    Measures how closely the predicted confidence matches empirical accuracy.
    """
    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    bin_details = []

    for i in range(n_bins):
        bin_lower = bin_boundaries[i]
        bin_upper = bin_boundaries[i + 1]

        if i == 0:
            in_bin = (confidences >= bin_lower) & (confidences <= bin_upper)
        else:
            in_bin = (confidences > bin_lower) & (confidences <= bin_upper)

        prop_in_bin = float(np.mean(in_bin))

        if prop_in_bin > 0:
            accuracy_in_bin = float(np.mean(predictions[in_bin] == labels[in_bin]))
            avg_confidence_in_bin = float(np.mean(confidences[in_bin]))
            gap = abs(avg_confidence_in_bin - accuracy_in_bin)
            ece += gap * prop_in_bin
            bin_details.append({
                "bin": f"[{bin_lower:.2f}, {bin_upper:.2f}]",
                "count": int(np.sum(in_bin)),
                "accuracy": round(accuracy_in_bin, 4),
                "confidence": round(avg_confidence_in_bin, 4),
                "gap": round(gap, 4),
            })

    return {
        "ece": round(float(ece), 4),
        "n_bins": n_bins,
        "bins": bin_details,
    }


def run_batch_inference(
    model: Any,
    tokenizer: Any,
    texts: List[str],
    device: str,
    batch_size: int = 32,
    max_length: int = 128,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Run forward pass over texts and return softmax probabilities and predicted indices.
    """
    all_probs = []
    model.eval()

    with torch.no_grad():
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i : i + batch_size]
            inputs = tokenizer(
                batch_texts,
                padding=True,
                truncation=True,
                max_length=max_length,
                return_tensors="pt",
            )
            inputs = {k: v.to(device) for k, v in inputs.items()}
            outputs = model(**inputs)
            probs = torch.nn.functional.softmax(outputs.logits, dim=-1).cpu().numpy()
            all_probs.append(probs)

    full_probs = np.vstack(all_probs)
    preds = np.argmax(full_probs, axis=1)
    return full_probs, preds


def evaluate(
    model_path_or_name: str,
    test_path: str,
    output_file: Optional[str] = None,
    batch_size: int = 32,
    max_length: int = 128,
    device_name: str = "auto",
) -> Dict[str, Any]:
    """
    Evaluate checkpoint or base model on the specified test dataset.
    """
    if device_name == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    else:
        device = device_name

    logger.info(f"Loading evaluation dataset from: {test_path}")
    if not os.path.exists(test_path):
        raise FileNotFoundError(f"Test dataset not found at {test_path}")

    df = pd.read_csv(test_path)
    if "text" not in df.columns or "label" not in df.columns:
        raise ValueError(f"Dataset must contain 'text' and 'label' columns.")

    df = df.dropna(subset=["text", "label"])
    df["text"] = df["text"].astype(str).str.strip()

    # Map labels to numeric if strings
    if df["label"].dtype == object or isinstance(df["label"].iloc[0], str):
        df["label"] = df["label"].map(LABEL2ID)

    df = df.dropna(subset=["label"])
    df["label"] = df["label"].astype(int)

    true_labels = df["label"].to_numpy()
    texts = df["text"].tolist()

    logger.info(f"Loaded {len(texts)} test examples.")
    logger.info(f"Loading model and tokenizer from: {model_path_or_name} on {device}...")

    tokenizer = AutoTokenizer.from_pretrained(model_path_or_name)
    try:
        model = AutoModelForSequenceClassification.from_pretrained(model_path_or_name)
    except Exception:
        config = AutoConfig.from_pretrained(
            model_path_or_name,
            num_labels=3,
            id2label=ID2LABEL,
            label2id=LABEL2ID,
        )
        model = AutoModelForSequenceClassification.from_pretrained(
            model_path_or_name,
            config=config,
        )

    model.to(device)

    # Inference
    logger.info("Computing predictions...")
    probs, preds = run_batch_inference(
        model=model,
        tokenizer=tokenizer,
        texts=texts,
        device=device,
        batch_size=batch_size,
        max_length=max_length,
    )

    confidences = np.max(probs, axis=1)

    # Core Metrics
    acc = float(accuracy_score(true_labels, preds))
    macro_f1 = float(f1_score(true_labels, preds, average="macro", zero_division=0))
    weighted_f1 = float(f1_score(true_labels, preds, average="weighted", zero_division=0))

    precision, recall, f1, support = precision_recall_fscore_support(
        true_labels, preds, average=None, labels=[0, 1, 2], zero_division=0
    )

    # Calibration (ECE)
    ece_data = compute_ece(confidences, preds, true_labels, n_bins=10)

    # Confusion Matrix
    cm = confusion_matrix(true_labels, preds, labels=[0, 1, 2]).tolist()

    # Classification Report
    clf_report_dict = classification_report(
        true_labels,
        preds,
        target_names=LABEL_LIST,
        output_dict=True,
        zero_division=0,
    )
    clf_report_text = classification_report(
        true_labels,
        preds,
        target_names=LABEL_LIST,
        digits=4,
        zero_division=0,
    )

    results: Dict[str, Any] = {
        "model": model_path_or_name,
        "test_dataset": test_path,
        "sample_count": len(texts),
        "device": device,
        "summary": {
            "accuracy": round(acc, 4),
            "macro_f1": round(macro_f1, 4),
            "weighted_f1": round(weighted_f1, 4),
            "ece": ece_data["ece"],
        },
        "per_class": {
            LABEL_LIST[i]: {
                "precision": round(float(precision[i]), 4),
                "recall": round(float(recall[i]), 4),
                "f1": round(float(f1[i]), 4),
                "support": int(support[i]),
            }
            for i in range(3)
        },
        "confusion_matrix": {
            "labels": LABEL_LIST,
            "matrix": cm,
            "description": "Rows: True Class, Columns: Predicted Class",
        },
        "confidence_calibration": ece_data,
        "classification_report": clf_report_dict,
    }

    # Print summary to stdout
    print("\n" + "=" * 65)
    print("NARRATIVELENS AI - EVALUATION RESULTS")
    print("=" * 65)
    print(f"Model Evaluated : {model_path_or_name}")
    print(f"Test Samples    : {len(texts):,}")
    print(f"Accuracy        : {acc:.4f}")
    print(f"Macro F1        : {macro_f1:.4f}")
    print(f"Weighted F1     : {weighted_f1:.4f}")
    print(f"ECE (Calib.)    : {ece_data['ece']:.4f}")
    print("-" * 65)
    print("CLASSIFICATION REPORT:")
    print(clf_report_text)
    print("-" * 65)
    print(f"CONFUSION MATRIX (0: normal, 1: offensive, 2: hate):")
    for r_idx, row in enumerate(cm):
        print(f"  {LABEL_LIST[r_idx]:10s} -> {row}")
    print("=" * 65 + "\n")

    if output_file:
        out_p = Path(output_file)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        with open(out_p, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        logger.info(f"Evaluation report successfully saved to {out_p.resolve()}")

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate hate speech model checkpoint.")
    parser.add_argument(
        "--checkpoint_path",
        type=str,
        default=None,
        help="Path to trained model checkpoint directory",
    )
    parser.add_argument(
        "--model_name",
        type=str,
        default=None,
        help="Hugging Face model ID if evaluating a pretrained baseline directly",
    )
    parser.add_argument(
        "--test_path",
        type=str,
        default="ml/datasets/test.csv",
        help="Path to test set CSV file (default: ml/datasets/test.csv)",
    )
    parser.add_argument(
        "--output_file",
        type=str,
        default="ml/evaluation/evaluation_report.json",
        help="Path to output JSON evaluation report",
    )
    parser.add_argument(
        "--batch_size",
        type=int,
        default=32,
        help="Batch size for inference (default: 32)",
    )
    parser.add_argument(
        "--max_length",
        type=int,
        default=128,
        help="Max sequence length (default: 128)",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="auto",
        help="Compute device ('cuda', 'cpu', or 'auto')",
    )

    args = parser.parse_args()

    # Determine model source
    target_model = args.checkpoint_path or args.model_name
    if not target_model:
        # Check standard default checkpoint location
        default_ckpt = "ml/checkpoints/xlm-roberta-hate-speech"
        if os.path.exists(default_ckpt):
            target_model = default_ckpt
            logger.info(f"No model path passed. Using default checkpoint at {default_ckpt}")
        else:
            target_model = "FacebookAI/xlm-roberta-base"
            logger.info(f"No checkpoint found. Using base model {target_model}")

    evaluate(
        model_path_or_name=target_model,
        test_path=args.test_path,
        output_file=args.output_file,
        batch_size=args.batch_size,
        max_length=args.max_length,
        device_name=args.device,
    )


if __name__ == "__main__":
    main()
