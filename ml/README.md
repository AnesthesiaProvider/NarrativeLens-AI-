# NarrativeLens AI - Machine Learning Pipeline & Training Guide

This directory contains the complete end-to-end machine learning pipeline for **NarrativeLens AI**, centered around fine-tuning **`FacebookAI/xlm-roberta-base`** for 3-class cross-lingual hate speech classification, token attribution explainability with **Captum Integrated Gradients**, and automated evaluation with calibration metrics.

---

## 1. Pipeline Overview

The pipeline standardizes diverse data into a unified 3-class taxonomy:
* **`normal` (0)**: Constructive, neutral, or non-hateful discourse.
* **`offensive` (1)**: Profanity, coarse insults, or abrasive language without protected group targeting.
* **`hate` (2)**: Targeted abuse, slurs, dehumanization, or threats directed at protected demographic attributes (religion, race, ethnicity, gender, sexual orientation, disability).

```
[ Hugging Face Datasets & Curated Data ]
                    │
                    ▼
       ml/datasets/download_datasets.py
                    │
                    ├── ml/datasets/train.csv (80%)
                    ├── ml/datasets/val.csv   (10%)
                    ├── ml/datasets/test.csv  (10%)
                    └── ml/datasets/dataset_card.md
                    │
                    ▼
       ml/training/train_classifier.py
                    │
                    ├── Best Checkpoint (XLM-RoBERTa + Head)
                    ├── training_metrics.json (loss curves)
                    ├── confusion_matrix.json
                    └── eval_results.json
                    │
                    ▼
       ml/evaluation/evaluate_model.py
                    │
                    └── Comprehensive Report + ECE Calibration
                    │
                    ▼
       backend/app/ml/model_manager.py
    (Loaded via CLASSIFIER_CHECKPOINT_PATH with
     Captum LayerIntegratedGradients Token Attribution)
```

---

## 2. Hardware Requirements & Specifications

The pipeline is pre-configured and tested for standard consumer and workstation GPUs:

* **Target Hardware**: NVIDIA GeForce RTX 4050 (6GB VRAM) / RTX 3060 / RTX 4060 or higher.
* **System RAM**: 16GB RAM minimum.
* **OS / Environment**: Windows 11 / Linux with Python 3.10 - 3.13.
* **PyTorch**: PyTorch 2.6.0+cu124 (or CUDA 12.x enabled).
* **VRAM Optimization**:
  * Sequence Length: `128`
  * Per-device Batch Size: `16`
  * Gradient Accumulation Steps: `2` (effective batch size: `32`)
  * Mixed Precision: `FP16` enabled
  * Peak VRAM consumption: **~3.8 GB - 4.5 GB** (well within 6GB limit).

### Expected Training Time

| Dataset Size | Epochs | RTX 4050 (6GB) | CPU Only |
| :--- | :--- | :--- | :--- |
| **Smoke Test (500 samples)** | 1 epoch | ~45 seconds | ~4 minutes |
| **Curated Baseline (~1,500 samples)** | 3 epochs | ~3-4 minutes | ~20 minutes |
| **Full Combined Dataset (~40k samples)**| 3 epochs | ~35-50 minutes | Several hours |

---

## 3. Step-by-Step Training Instructions

### Step 1: Install Dependencies

Ensure your Python environment contains all necessary packages:

```powershell
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
pip install transformers datasets accelerate captum scikit-learn pandas pyyaml tqdm
```

Verify your environment:
```powershell
python -c "import torch, transformers, datasets, captum; print('CUDA Available:', torch.cuda.is_available())"
```

---

### Step 2: Download & Prepare Datasets

Run `download_datasets.py` to acquire datasets from Hugging Face (`ucberkeley-dlab/measuring-hate-speech`, `hatexplain`, and multilingual sources), harmonize the labels, and split into train, validation, and test sets:

```powershell
# Standard download and preparation
python ml/datasets/download_datasets.py

# Optional: Fast download with sample cap per source
python ml/datasets/download_datasets.py --max_samples 5000
```

This generates:
* `ml/datasets/train.csv` (80% stratified split)
* `ml/datasets/val.csv` (10% stratified split)
* `ml/datasets/test.csv` (10% stratified split)
* `ml/datasets/dataset_card.md` (data provenance and distribution report)

---

### Step 3: Train the Model

Launch `train_classifier.py` using default parameters or custom hyperparameter overrides:

```powershell
# Standard training (using train_config.yaml defaults)
python ml/training/train_classifier.py

# Quick verification / smoke test
python ml/training/train_classifier.py --epochs 1 --max_train_samples 200 --max_eval_samples 50

# Custom hyperparameters via CLI
python ml/training/train_classifier.py `
  --model_name FacebookAI/xlm-roberta-base `
  --epochs 3 `
  --batch_size 16 `
  --gradient_accumulation_steps 2 `
  --learning_rate 2e-5 `
  --max_length 128 `
  --output_dir ml/checkpoints/xlm-roberta-hate-speech `
  --fp16
```

#### What Happens During Training:
1. Loads stratified datasets and tokenizes using `XLM-RoBERTa` vocabulary.
2. Initializes `AutoModelForSequenceClassification` with a 3-class classification head (`normal`, `offensive`, `hate`).
3. Uses Hugging Face `Trainer` with FP16, AdamW optimizer, linear warmup, and weight decay.
4. Evaluates validation macro-F1 at the end of each epoch.
5. Saves the best model checkpoint based on validation macro-F1 (`EarlyStoppingCallback` patience=2).
6. Evaluates test set and outputs:
   * `ml/checkpoints/xlm-roberta-hate-speech/` (model weights, tokenizer, config)
   * `training_metrics.json`
   * `eval_results.json`
   * `confusion_matrix.json`

---

### Step 4: Evaluate the Model

Run the standalone evaluation script on test data:

```powershell
# Evaluate the trained checkpoint
python ml/evaluation/evaluate_model.py `
  --checkpoint_path ml/checkpoints/xlm-roberta-hate-speech `
  --test_path ml/datasets/test.csv `
  --output_file ml/evaluation/evaluation_report.json

# Compare with base model zero-shot
python ml/evaluation/evaluate_model.py `
  --model_name FacebookAI/xlm-roberta-base `
  --test_path ml/datasets/test.csv
```

The evaluation suite calculates:
* Overall Accuracy, Macro-F1, and Weighted-F1
* Per-class Precision, Recall, and F1 (for `normal`, `offensive`, `hate`)
* Confusion Matrix
* **Expected Calibration Error (ECE)** across 10 confidence bins
* Detailed classification report

---

### Step 5: Point the Backend to the Checkpoint

Once trained, connect the FastAPI backend to your fine-tuned model checkpoint:

1. In your `.env` file or environment variables, set:
```bash
CLASSIFIER_CHECKPOINT_PATH=ml/checkpoints/xlm-roberta-hate-speech
```

2. When the backend starts:
   * `backend/app/ml/model_manager.py` checks `CLASSIFIER_CHECKPOINT_PATH`.
   * It loads the fine-tuned checkpoint into GPU memory with 3-class label mapping.
   * Calls to `predict_hate_speech(text, explain=True)` execute real **Captum LayerIntegratedGradients** token-level attributions.
   * If the checkpoint is missing, it falls back to the base model or clearly labeled heuristic triage.

---

## 4. Configuration File (`train_config.yaml`)

Configuration can be customized in `ml/training/train_config.yaml`:

```yaml
model:
  name: FacebookAI/xlm-roberta-base
  num_labels: 3
  max_length: 128

training:
  epochs: 3
  batch_size: 16
  learning_rate: 2e-5
  warmup_ratio: 0.1
  weight_decay: 0.01
  gradient_accumulation_steps: 2
  fp16: true
  seed: 42
  early_stopping_patience: 2

data:
  train_path: ml/datasets/train.csv
  val_path: ml/datasets/val.csv
  test_path: ml/datasets/test.csv
  text_column: text
  label_column: label

output:
  dir: ml/checkpoints/xlm-roberta-hate-speech
  save_total_limit: 3
```

---

## 5. Troubleshooting & FAQ

### Issue: CUDA Out of Memory (OOM) on 6GB GPU
* **Solution**: Reduce batch size to `8` and increase gradient accumulation steps to `4`:
  ```powershell
  python ml/training/train_classifier.py --batch_size 8 --gradient_accumulation_steps 4
  ```
* Ensure no background browser hardware acceleration or games are holding GPU VRAM.

### Issue: Hugging Face Rate Limit or Offline Mode
* `download_datasets.py` includes curated multilingual fallback seeds across all 3 classes so that data preparation will never crash even in restricted network environments.

### Issue: Captum Not Available
* `backend/app/ml/model_manager.py` automatically falls back to an exact PyTorch input-embedding gradient saliency calculation ($\|\nabla_{E} \mathcal{L}\|_{2}$) if Captum is absent.
