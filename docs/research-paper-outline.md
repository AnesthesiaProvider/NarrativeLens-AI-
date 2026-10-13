# ACL Research Paper Outline: NarrativeLens AI

**Paper Working Title:**  
*NarrativeLens: A Multilingual, Multimodal Framework for Narrative-Aware Hate Speech Detection and Grounded Counter-Narrative Generation*

**Target Venue:** ACL / EMNLP / NAACL (Main Conference & Industry Track)  
**Authors:** Ansh S. et al.  
**Status:** In Preparation (Pre-experimental Protocol Phase)

---

## 1. Abstract
* **Background**: Existing hate speech detection pipelines predominantly operate on isolated sentences, relying on superficial lexical patterns that fail to identify subtle cross-lingual dog-whistles, multimodal memes, and coordinated narrative motifs. Furthermore, automated moderation systems rarely provide constructive mitigation pathways.
* **Proposal**: We present **NarrativeLens**, an integrated framework that: (1) performs multi-label cross-lingual toxicity detection using XLM-RoBERTa with token-level rationales; (2) captures high-dimensional semantic narrative manifolds using dense embeddings (`bge-m3`) with sub-millisecond vector clustering; (3) solves multimodal meme classification via unified vision-language modeling (`Qwen3-VL`); and (4) synthesizes grounded, empathetic counter-narratives using retrieval-augmented generation (`Qwen3-4B`).
* **Key Findings**: *[PENDING]* Extensive evaluation across 6 diverse languages and the Hateful Memes benchmark demonstrates that NarrativeLens outperforms conventional baselines in Macro-$F_1$ while reducing subgroup false positive bias and producing de-escalating counter-narratives preferred by human evaluators.

---

## 2. Introduction
* **2.1 The Crisis of Online Toxicity & Narrative Harm**: Progression from overt slurs to nuanced ideological tropes, memes, and disinformation-linked harassment campaigns.
* **2.2 The Tripartite Challenge**:
  1. *Linguistic & Cross-Lingual Nuance*: Code-switching, informal dialects, and regional context.
  2. *Multimodality*: Benign-conflict memes where hostility arises strictly from the semantic interaction of image and text.
  3. *Actionable Mitigation vs. Pure Censorship*: Moving beyond punitive deletion toward educational, de-escalating counter-speech.
* **2.3 Contributions of this Work**:
  * Unified hierarchical taxonomy spanning primary hate categories, protected targets, and narrative motifs.
  * End-to-end open architecture uniting cross-lingual classification, dense vector clustering, and multimodal vision-language understanding.
  * Retrieval-grounded counter-narrative synthesis benchmarked for toxicity reduction and factual alignment.
  * Comprehensive public reproducibility package including code, model cards, and governance protocols.

---

## 3. Related Work
* **3.1 Lexical & Transformer-Based Hate Speech Detection**: Waseem & Hovy (2016), Davidson et al. (2017), Mathew et al. (HateXplain, 2021).
* **3.2 Multilingual & Code-Mixed NLP**: Conneau et al. (XLM-R, 2020), HASOC shared tasks (Mandl et al., 2019-2023).
* **3.3 Multimodal Content Moderation**: Kiela et al. (Facebook Hateful Memes, 2020), Pramanick et al. (MOMENT, 2021).
* **3.4 Narrative & Disinformation Tracking**: Starbird et al. (2019), Da San Martino et al. (Propaganda detection, 2020).
* **3.5 Automated Counter-Narrative Generation**: Chung et al. (CONAN, 2019), Fanton et al. (2021), Bonaldi et al. (2022).

---

## 4. Problem Formulation & Narrative Taxonomy
* **4.1 Formal Task Definition**:
  * Input tuple $x = (t, v, l)$ where $t$ is text, $v$ is visual media (optional), and $l \in \mathcal{L}$ is language code.
  * Predict multi-tier labels $y = (y_{\text{cat}}, y_{\text{target}}, y_{\text{motif}}, y_{\text{aggression}})$.
  * Compute dense representation $\mathbf{z} \in \mathbb{R}^{1024}$ and cluster membership $c \in \mathcal{C}$.
  * Conditional generation of counter-narrative $g = f(x, c, \mathcal{E})$ grounded on verified evidence $\mathcal{E}$.
* **4.2 The NarrativeLens Hierarchical Taxonomy**:
  * Tier 1: Primary category (Benign, Offensive, Hate Speech).
  * Tier 2: Protected target attributes (Race, Religion, Gender/Sexual Orientation, Disability, Nationality).
  * Tier 3: Narrative motifs (Dehumanization, Demographic Replacement, Conspiratorial Cabal, Criminality/Violence Stereotypes).
  * Tier 4: Threat severity (Latent/Implicit, Explicit Disparagement, Incitement to Violence).

---

## 5. Dataset Construction & Annotation Protocol
* **5.1 Aggregated Benchmarks**: HateXplain (English), HASOC (Hindi, German, English), Facebook Hateful Memes (Multimodal), and CONAN (Counter-narrative).
* **5.2 Data Harmonization & Unified Schema**: Canonical `NarrativeSample` schema with normalized labels and token-level rationale spans.
* **5.3 Annotation & Quality Assurance**:
  * Multi-annotator setup with diverse demographic representation.
  * Inter-annotator agreement metrics: Fleiss' Kappa ($\kappa$) and Krippendorff's Alpha ($\alpha$).
  * Annotator well-being and psychological safety guardrails.

---

## 6. System Architecture & Model Pipeline
* **6.1 Text Classification Backbone**: Fine-tuning `XLM-RoBERTa-base` with weighted Focal Loss and Integrated Gradients token attribution.
* **6.2 Dense Narrative Embeddings & Vector Index**: `BAAI/bge-m3` paired with PostgreSQL `pgvector` (HNSW indexing with cosine metric).
* **6.3 Multimodal Vision-Language Reasoning**: `Qwen/Qwen3-VL-4B-Instruct` zero-shot and instruction-tuned for multimodal meme and infographic analysis.
* **6.4 Grounded Counter-Narrative Generation**: `Qwen/Qwen3-4B` with prompt-conditioned safety boundaries and RAG retrieval over verified fact-checking corpuses.

---

## 7. Experimental Setup & Benchmarks
* **7.1 Baseline Systems**:
  * Lexical/n-gram + Logistic Regression.
  * Monolingual BERT / RoBERTa baselines.
  * Multimodal CLIP + Linear probe.
  * Unconstrained LLM zero-shot prompting (Llama-3-8B, Mistral-7B).
* **7.2 Evaluation Metrics**:
  * Macro-averaged Precision, Recall, and $F_1$.
  * Area Under the Precision-Recall Curve (PR-AUC).
  * Fairness & Subgroup Bias: Subgroup AUC, BPSN AUC, BNSP AUC (Borkan et al., 2019).
  * Counter-Narrative Quality: Toxicity Delta ($\Delta_{\text{tox}}$), NLI Entailment Groundedness, Perplexity, and Human Preference Rate.
* **7.3 Implementation & Training Details**: Hardware specifications, optimizer (AdamW), learning rate schedules, batch sizes, and quantization configurations.

---

## 8. Results & Quantitative Analysis
* **8.1 Cross-Lingual Hate Speech Detection**:
  * *[RESULTS PENDING - Experiments in progress]*
  * Target Table 1: Macro-$F_1$ and PR-AUC across English, Hindi, German, Spanish, French, and code-mixed subsets vs. baseline architectures.
* **8.2 Multimodal Meme Classification**:
  * *[RESULTS PENDING - Evaluation on Facebook Hateful Memes test set]*
  * Target Table 2: Accuracy and AUROC comparing unimodal text, unimodal image, CLIP dual-encoder, and Qwen3-VL-4B.
* **8.3 Bias and Subgroup Fairness Audits**:
  * *[RESULTS PENDING - BPSN/BNSP evaluations on identity term lexicons]*
  * Target Table 3: Demonstration of false positive suppression when benign protected identity terms are mentioned.

---

## 9. Qualitative Case Studies & Narrative Clustering
* **9.1 Case Study: Emergence of Demographic Replacement Tropes**:
  * *[RESULTS PENDING - Visualizing cluster graph evolution across temporal feeds]*
* **9.2 Multimodal Meme Reasoning Analysis**:
  * *[RESULTS PENDING - Examination of subtle visual metaphors and benign-conflict memes successfully identified by vision-language reasoning]*
* **9.3 Token-Level Attribution Visualization**:
  * *[RESULTS PENDING - Saliency maps demonstrating exact toxic span highlights vs false-positive context]*

---

## 10. Counter-Narrative Generation & Human Evaluation
* **10.1 Automated Generation Metrics**:
  * *[RESULTS PENDING - Toxicity reduction, BLEURT/ROUGE against gold counter-narratives, and factual entailment scores]*
* **10.2 Human Evaluation Protocol**:
  * Blind evaluation by trained content safety reviewers across three axes:
    1. Constructiveness & Empathy (1–5 scale).
    2. Factual Accuracy & Persuasiveness (1–5 scale).
    3. Safety & Lack of Reciprocal Toxicity (Pass/Fail).
  * *[RESULTS PENDING - Win-rate comparisons between ungrounded LLMs and NarrativeLens RAG-grounded counter-narratives]*

---

## 11. Error Analysis & Limitations
* **11.1 Sarcasm and Reclaimed Slurs**: Failure modes where ingroup community solidarity was flagged or high-irony satire was misidentified.
* **11.2 Code-Mixing & Orthographic Jargon**: Degradation patterns observed in non-standard phonetic spellings and Romanized vernaculars.
* **11.3 Hallucination in Long-Tail Counter-Narratives**: Borderline instances where retrieval gaps yielded generic rather than evidence-specific rebuttals.
* **11.4 Human-in-the-Loop Imperative**: Justification for treating NarrativeLens as an advisory decision-support system rather than a fully autonomous censor.

---

## 12. Ethics Statement & Broader Impact
* **12.1 Content Warning & Annotator Welfare**: Transparent disclosure of toxic content handling and mental health support protocols.
* **12.2 Dual-Use & Non-Weaponization Safeguards**: Measures taken to ensure generative pipelines cannot be inverted for automated harassment or targeted hate speech creation.
* **12.3 Freedom of Expression & Bias Mitigation**: Balancing harms of hate speech against risks of over-censoring political dissent and minority voices.

---

## 13. Conclusion & Future Work
* **13.1 Summary of Findings**: Summary of how multimodal reasoning, narrative clustering, and grounded counter-speech establish a new paradigm in computational safety.
* **13.2 Future Research Directions**:
  * Extension to real-time audio/video streaming moderation.
  * Graph neural network modeling of social propagation dynamics.
  * Interactive multi-turn counter-dialogue agents for community-based restorative moderation.

---

## References
*(Comprehensive bibliography of ~60 citations formatted in ACL style)*

## Appendix
* **A. Hyperparameter Configurations & Training Curves**
* **B. Annotation Guidelines & Taxonomy Rubrics**
* **C. Prompt Templates for Counter-Narrative Synthesis**
* **D. Data Governance and PII Redaction Implementation Details**
