# NarrativeLens AI - Hate Speech Dataset Card

## 1. Dataset Overview

* **Unified Taxonomy**: 3-Class Categorization
  * `normal`: Neutral, constructive, or benign discourse.
  * `offensive`: Profanity, insults, abrasive sentiment without targeting protected identity groups.
  * `hate`: Targeted abuse, slurs, dehumanization, or threats directed against protected demographic groups (race, religion, gender, sexual orientation, disability, nationality).
* **Target Model**: `FacebookAI/xlm-roberta-base` cross-lingual sequence classifier.
* **Format**: Comma-Separated Values (`train.csv`, `val.csv`, `test.csv`) with columns `text`, `label`, `source`.

---

## 2. Integrated Data Sources

1. **`ucberkeley-dlab/measuring-hate-speech`** (~135k annotations):
   * Continuous hate speech scoring calibrated via Rasch measurement models.
   * Discretization: `score > 0.5` &rarr; `hate`, `-1.0 <= score <= 0.5` &rarr; `offensive`, `score < -1.0` &rarr; `normal`.
2. **`hatexplain`**:
   * Word/post token rationales with 3-class human annotator consensus.
   * Annotations resolved via majority voting across annotators.
3. **Multilingual Corpora (e.g., `Hate-speech-CNERG/deoffxlm-data`, HASOC)**:
   * Hindi, code-mixed Hinglish, and cross-lingual social media discourse.
4. **NarrativeLens Curated Seed**:
   * Multilingual and English verified references for reproducible smoke testing and baseline validation.

---

## 3. Data Processing & Methodology

* **Stratification**: 80% train, 10% validation, 10% test split preserves identical class distribution ratios across all evaluation sets.
* **Cleaning**: Null stripping, deduplication by text content, whitespace normalization.
* **Reproducibility**: All random operations fixed with `seed=42`.

---

## 4. Ethical Considerations and Limitations

* **Intended Use**: For automated content moderation triage, research auditing, and counter-narrative generation support. Not for autonomous irreversible censorship without human-in-the-loop oversight.
* **Content Warning**: Contains toxic, profane, and abusive text required for training robust classification heads.
