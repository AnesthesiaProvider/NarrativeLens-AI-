# NarrativeLens AI - Research Methodology & System Limitations

## 1. Problem Formulation & Definitions

Hate speech detection on digital platforms has traditionally suffered from two major flaws: **lexical over-reliance** (flagging benign reclaimed language or profanity without hostility) and **context blindness** (failing to detect implicit dog-whistles, coordinated disinformation narratives, and multimodal memes).

NarrativeLens AI addresses this by framing content safety as a **narrative-aware, multimodal, and cross-lingual classification and intervention task**.

### 1.1. Core Definitions
* **Hate Speech**: Any communication that disparages, dehumanizes, incites violence against, or promotes hatred toward an individual or group based on protected attributes: race, ethnicity, religion, disability, age, nationality, sexual orientation, or gender identity (United Nations Strategy and Plan of Action on Hate Speech).
* **Offensive Language**: Vulgar, profane, or aggressive language that does not target a protected identity group or incite discrimination/violence.
* **Toxic Narrative / Narrative Motif**: A recurring discursive frame, trope, or conspiracy theory (e.g., demographic replacement, scapegoating for economic distress, biological contamination tropes) deployed across multiple posts to legitimize discrimination.
* **Counter-Narrative**: A constructive, non-violent, factually grounded response designed to de-escalate hostility, debunk false premises, and restore empathetic discourse without reciprocal toxicity.

---

## 2. Multi-Tiered Annotation & Classification Taxonomy

To prevent oversimplified binary outputs, NarrativeLens models classify inputs across a hierarchical multi-tier taxonomy:

```
[ Input Content ]
       │
       ├── Tier 1: Primary Category
       │     ├── Benign / Neutral
       │     ├── Offensive (Non-targeted profanity)
       │     └── Hate Speech (Targeted discriminatory animus)
       │
       ├── Tier 2: Protected Target Groups (Multi-label)
       │     ├── Race / Ethnicity
       │     ├── Religion / Faith Community
       │     ├── Gender Identity / Sexual Orientation
       │     ├── Disability / Health Status
       │     └── Nationality / Migration Status
       │
       ├── Tier 3: Narrative Motif / Conspiracy Classification
       │     ├── Dehumanization & Vermin Metaphors
       │     ├── Demographic Replacement / Invasion Tropes
       │     ├── Conspiracy / Secret Cabal Orchestration
       │     ├── Criminality & Hyper-Violence Stereotypes
       │     └── Moral Corruption & Contagion Tropes
       │
       └── Tier 4: Aggression & Threat Assessment
             ├── Latent / Implicit (Dog-whistles, sarcasm, coded memes)
             ├── Explicit Disparagement (Slurs, overt bigotry)
             └── Incitement to Physical Violence / Imminent Danger
```

---

## 3. Machine Learning Methodology

### 3.1. Multilingual Token & Sequence Modeling
* **Backbone**: `FacebookAI/xlm-roberta-base`, pre-trained on 2.5TB of CommonCrawl data in 100 languages.
* **Loss Function**: Weighted Focal Loss to address extreme class imbalance:
  $$\mathcal{L}_{focal} = -\alpha_t (1 - p_t)^\gamma \log(p_t)$$
  where $\gamma = 2.0$ down-weights easily classified benign instances and prioritizes hard borderline cases.
* **Token-Level Attribution**: Integrated Gradients are calculated with respect to token embeddings to yield explicit rationales, indicating exactly which spans caused the classification trigger.

### 3.2. Dense Semantic Clustering & Narrative Tracking
* **Embedding Model**: `BAAI/bge-m3` maps inputs to $\mathbb{R}^{1024}$.
* **Clustering Algorithm**: Incremental density-based clustering (HDBSCAN on vector projections) and cosine distance search via `pgvector` HNSW index:
  $$d_{\cos}(\mathbf{u}, \mathbf{v}) = 1 - \frac{\mathbf{u} \cdot \mathbf{v}}{\|\mathbf{u}\|_2 \|\mathbf{v}\|_2}$$
* **Narrative Lineage**: When new posts arrive with $d_{\cos} < 0.15$ to existing cluster centroids, they are linked to the ongoing narrative thread, allowing tracking of viral hate campaigns across multilingual variations.

### 3.3. Multimodal Reasoning (Vision-Language Fusion)
* **Challenge**: Hateful memes combine superficially benign images with text that together produce hateful meaning, or combine hateful visual symbols with innocuous text.
* **Architecture**: Direct visual reasoning via `Qwen/Qwen3-VL-4B-Instruct`. Instead of running isolated OCR $\to$ text classification (which misses visual metaphors, altered flags, and caricatures), the vision-language backbone attends jointly over visual patches and subword tokens.

### 3.4. Grounded Counter-Narrative Generation
* **Inference Pipeline**:
  1. Retrieve verified factual evidence and counter-arguments matching the identified `Narrative Motif`.
  2. Feed toxic claim, target identity, and retrieved factual snippets into `Qwen/Qwen3-4B`.
  3. Condition prompt with strict behavioral constraints:
     * Non-confrontational, empathetic framing.
     * Concrete statistical or institutional facts with attribution.
     * Absolute prohibition of insulting the speaker.
  4. Post-generation safety filter validates that the generated draft exhibits zero toxicity.

---

## 4. Evaluation Protocol

1. **Classification Metrics**:
   * Macro $F_1$, Precision, and Recall across all classes.
   * PR-AUC (Precision-Recall Area Under Curve).
2. **Unintended Bias Audits (Borkan et al., 2019)**:
   * **Subgroup AUC**: Measures classification performance solely within texts containing specific identity terms.
   * **BPSN AUC (Background Positive, Subgroup Negative)**: Identifies false positive rates where benign mentions of identity terms are mistakenly classified as toxic.
   * **BNSP AUC (Background Negative, Subgroup Positive)**: Identifies false negative rates where hateful posts targeting specific groups are missed.
3. **Cross-Lingual Generalization**: Zero-shot cross-lingual evaluation on languages not present during supervised fine-tuning.
4. **Counter-Narrative Assessment**:
   * **Toxicity Delta ($\Delta_{tox}$)**: Reduction in toxicity score relative to original prompt.
   * **Factual Groundedness**: NLI-based entailment score against retrieved evidence passages.
   * **Readability & Fluency**: Perplexity and standard Flesch-Kincaid grade level metrics.

---

## 5. Limitations & Boundary Conditions

Despite state-of-the-art methodology, users and researchers must account for intrinsic limitations:

1. **Sarcasm, Irony, and Subtext**: Linguistic irony and hyper-local cultural references can lead to misclassification. Sarcastic condemnations of hate speech may trigger false positives if context is truncated.
2. **Reclaimed Language**: Marginalized communities frequently reclaim historically derogatory terms. Automated models cannot consistently distinguish ingroup reclamation from outgroup harassment without social network author graph context.
3. **Adversarial Evasion**: Malicious actors use evolving obfuscation tactics:
   * Leetspeak and phonetic substitutions (e.g., using numbers or symbols for vowels).
   * Zero-width Unicode insertion between letters.
   * Metaphorical dog-whistles that masquerade as everyday idioms.
4. **Code-Mixed and Low-Resource Dialects**: While XLM-RoBERTa handles 100 languages, performance on informal code-mixed vernaculars (e.g., Hinglish, Arabizi, Taglish) exhibits higher variance than standard formal text.
5. **Generative Hallucination**: Large language models may occasionally introduce unverified historical or numerical claims in counter-narratives if evidence retrieval fails to return definitive sources.
6. **No Automation of Final Judgments**: NarrativeLens is explicitly designed as a **moderator-assist tool**. Final takedown or account restriction actions must include human-in-the-loop review.
