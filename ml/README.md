# NarrativeLens AI - Machine Learning Pipeline & Strategy

The `ml/` module houses all machine learning models, training scripts, dataset preprocessors, and evaluation protocols for **NarrativeLens AI**. NarrativeLens moves beyond simple keyword filtering by combining multilingual sequence classification, multimodal image-text reasoning, dense narrative clustering, and grounded counter-narrative generation.

---

## 1. Architectural Strategy & Model Suite

NarrativeLens utilizes a decoupled, modular multi-model architecture where specialized models perform complementary tasks:

```
[ Incoming Content: Text / Image / Meme ]
                   │
         ┌─────────┴─────────┐
         ▼                   ▼
 ┌───────────────┐   ┌───────────────────────────┐
 │ Vision Preproc│   │ Multilingual Tokenizer    │
 └───────┬───────┘   └─────────────┬─────────────┘
         │                         │
         ├─────────────────────────┼───────────────────────────┐
         ▼                         ▼                           ▼
┌───────────────────┐    ┌────────────────────┐     ┌─────────────────────┐
│ Multimodal Model  │    │  Cross-Lingual CLF │     │  Embedding Model    │
│ Qwen3-VL-4B       │    │  XLM-RoBERTa-base  │     │  BAAI/bge-m3        │
│ (Memes / Infogr.) │    │  (Toxic / Hate /   │     │  (1024d Dense Vect. │
│                   │    │   Offensive / Org) │     │   pgvector HNSW)    │
└────────┬──────────┘    └─────────┬──────────┘     └──────────┬──────────┘
         │                         │                           │
         └─────────────────────────┼───────────────────────────┘
                                   ▼
                   ┌───────────────────────────────┐
                   │ Aggregated Toxicity & Signals │
                   └───────────────┬───────────────┘
                                   ▼
                   ┌───────────────────────────────┐
                   │ RAG & Grounded Evidence Query │
                   └───────────────┬───────────────┘
                                   ▼
                   ┌───────────────────────────────┐
                   │ Counter-Narrative Generation  │
                   │ Qwen/Qwen3-4B                 │
                   └───────────────────────────────┘
```

### A. Multilingual Hate Speech Classifier (`FacebookAI/xlm-roberta-base`)
* **Role**: Primary sequence and token-level classification engine for textual content.
* **Capabilities**:
  * Cross-lingual zero-shot and few-shot transfer across 100+ languages (with focus on English, Hindi, Spanish, French, German, and code-mixed vernaculars).
  * Multi-label output taxonomy:
    * `benign`: Constructive, neutral, or non-hateful discourse.
    * `offensive`: Profanity or abrasive language without protected group targeting.
    * `hate_speech`: Slurs, dehumanization, threats directed at protected attributes (race, religion, gender, sexual orientation, disability, nationality).
    * `coordinated_disinformation`: Coordinated political, health, or conspiratorial narrative motifs.
* **Explainability**: Integrated gradient saliency and rationalization scores highlighting toxic spans.

### B. Dense Narrative Representation & Clustering (`BAAI/bge-m3`)
* **Role**: Extracting rich semantic representations for narrative tracking, semantic similarity, and retrieval.
* **Capabilities**:
  * Generates 1024-dimensional dense vectors supporting multi-lingual and cross-lingual semantic matching.
  * Ingests both short social posts and long-form articles (context window up to 8192 tokens).
  * Powers vector storage in PostgreSQL (`pgvector` using HNSW index) for rapid discovery of coordinated disinformation campaigns and emergent hate clusters.

### C. Multimodal Understanding (`Qwen/Qwen3-VL-4B-Instruct`)
* **Role**: Visual-textual analysis of social media memes, screenshots, and infographics.
* **Capabilities**:
  * Solves the multimodal hate speech challenge (e.g., benign text paired with a hateful image or vice versa).
  * Direct reasoning over visual metaphors, historical tropes, and symbols without mandatory two-step OCR failure points.
  * Optional fallback OCR module for lightweight text-in-image extraction.

### D. Grounded Counter-Narrative Generation (`Qwen/Qwen3-4B`)
* **Role**: Automated drafting of de-escalating, empathetic, and evidence-grounded counter-narratives for human moderators.
* **Capabilities**:
  * Retrieval-Augmented Generation (RAG) conditioning on authoritative fact-checks and neutral evidentiary sources.
  * Tone enforcement: Non-confrontational, empathetic, and fact-focused to de-polarize online discussions.
  * Guardrails to prevent hallucination, reciprocal toxicity, or patronizing rhetoric.

---

## 2. Directory Layout

```
ml/
├── datasets/            # Dataset acquisition scripts and schema mappers (.gitkeep)
│   ├── raw/             # Unprocessed external datasets (gitignored)
│   └── processed/       # Unified JSONL splits (train/val/test) (gitignored)
├── training/            # Fine-tuning pipelines, loss definitions, trainer loops (.gitkeep)
│   ├── train_classifier.py
│   └── finetune_lora.py
├── evaluation/          # Benchmark evaluation, bias audits, fairness metrics (.gitkeep)
│   ├── metrics.py
│   └── evaluate_crosslingual.py
├── experiments/         # Experiment tracking configs, hyperparameter logs (.gitkeep)
└── README.md            # This document
```

---

## 3. Dataset Integration & Preprocessing Strategy

NarrativeLens standardizes academic and open-source hate speech datasets into a unified schema:
* **HateXplain**: Multi-annotator rationales, target communities, and token-level highlights.
* **Facebook Hateful Memes Challenge**: Multimodal benign-conflict image-text pairs.
* **HASOC (Hate Speech and Offensive Content)**: Multi-lingual code-mixed benchmarks (Hindi-English, German, Marathi).
* **CONAN / Multilingual Counter-Narrative**: Pairs of hateful arguments and expert-verified counter-responses.

Each entry is mapped to the canonical `NarrativeSample` schema:
```json
{
  "id": "uuid-v4",
  "text": "Extracted or provided content...",
  "language": "en",
  "media_urls": [],
  "labels": {
    "is_hate": true,
    "is_offensive": true,
    "target_groups": ["religious_minority"],
    "narrative_motif": "conspiracy_replacement"
  },
  "rationales": [[12, 28]],
  "verified_counter_narrative": "Statistical evidence demonstrates that..."
}
```

---

## 4. Evaluation Protocol

Models are evaluated using rigorous academic benchmarks:
1. **Classification Performance**:
   * Macro-averaged F1 score across all target classes.
   * Precision-Recall AUC (PR-AUC) to address class imbalance.
2. **Fairness & Subgroup Bias (Borkan et al., 2019)**:
   * Subgroup AUC: Performance evaluated strictly on texts mentioning specific demographic identities.
   * Background Negative Subgroup AUC (BPSN) and Background Positive Subgroup AUC (BNSP) to prevent false-positive penalization of identity tokens (e.g. "gay", "Muslim", "trans").
3. **Cross-Lingual Zero-Shot Transfer**:
   * Evaluation on unseen languages to test multilingual generalization without target-language training data.
4. **Counter-Narrative Quality**:
   * Human & automated evaluation across Toxicity Delta (negative shift), Groundedness (factuality score), and Empathy/Constructiveness.

---

## 5. Serving & Resource Optimization

* **Lazy Loading**: Models are initialized in memory only upon invocation of their respective pipeline route.
* **Device Flexibility**: Automatic detection and offloading between `cuda`, `rocm`, `mps`, and `cpu`.
* **Quantization**: Support for 4-bit and 8-bit (BitsAndBytes / AWQ) weights for consumer-grade GPU deployment.
