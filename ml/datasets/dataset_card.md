# NarrativeLens AI - Hate Speech Dataset Card

## 1. Dataset Overview

* **Unified Taxonomy**: 3-Class Categorization
  * `normal`: Neutral, constructive, or benign discourse.
  * `offensive`: Profanity, insults, abrasive sentiment without targeting protected identity groups.
  * `hate`: Targeted abuse, slurs, dehumanization, or threats directed against protected demographic groups (race, religion, gender, sexual orientation, disability, nationality).
* **Target Model**: `FacebookAI/xlm-roberta-base` cross-lingual classifier.
* **Total Instances**: 20,173
* **Data Sources Represented**: measuring_hate_speech, curated

---

## 2. Splits and Class Distribution

| Split | Normal | Offensive | Hate | Total |
| :--- | :--- | :--- | :--- | :--- |
| **Train (80%)** | 5,386 | 5,376 | 5,376 | 16,138 |
| **Validation (10%)** | 673 | 672 | 672 | 2,017 |
| **Test (10%)** | 674 | 672 | 672 | 2,018 |
| **Combined** | **6,733** | **6,720** | **6,720** | **20,173** |

### Source Distribution:
- **measuring_hate_speech**: 19,998 examples (99.1%)
- **curated**: 175 examples (0.9%)

---

## 3. Data Processing & Methodology

1. **Taxonomy Alignment**:
   * Continuous scales (e.g. Berkeley Measuring Hate Speech continuous scores) were discretized:
     * Score > 0.5 &rarr; `hate`
     * -1.0 &le; Score &le; 0.5 &rarr; `offensive`
     * Score < -1.0 &rarr; `normal`
   * Discrete multi-annotator datasets (HateXplain) resolved using majority voting.
2. **Stratification**:
   * Stratified splitting (80% train, 10% validation, 10% test) guarantees equal class proportions across all three evaluation partitions.
3. **Multilingual & Code-Mixed Support**:
   * Curated and open-source multilingual corpora covering English, Hindi, and code-mixed Hinglish.

---

## 4. Ethical Considerations and Limitations

* **Demographic Sensitivity**: Hate speech datasets reflect the biases of the underlying annotator pools.
* **Intended Use**: For automated content moderation triage, research auditing, and counter-narrative generation support. Not for autonomous irreversible censorship without human-in-the-loop oversight.
* **Content Warning**: Contains toxic, profane, and abusive text required for robust classifier supervision.
