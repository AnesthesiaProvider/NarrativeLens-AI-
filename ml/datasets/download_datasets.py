"""
Script to download, preprocess, harmonize, and split hate speech datasets
for NarrativeLens AI.

Harmonizes diverse datasets into a unified 3-class taxonomy:
  0: normal
  1: offensive
  2: hate

Outputs:
  - ml/datasets/train.csv (80%)
  - ml/datasets/val.csv (10%)
  - ml/datasets/test.csv (10%)
  - ml/datasets/dataset_card.md
"""

from __future__ import annotations

import argparse
import logging
import os
import random
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("download_datasets")

# Unified taxonomy labels
LABELS = ["normal", "offensive", "hate"]


def set_seed(seed: int = 42) -> None:
    """Set random seed for reproducibility."""
    random.seed(seed)
    np.random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)


def create_fallback_dataset() -> pd.DataFrame:
    """
    Creates a robust, curated multilingual seed dataset used as fallback
    if Hugging Face datasets cannot be reached or are offline.
    Covers English, Hindi, code-mixed Hinglish, and other languages across all 3 classes.
    """
    logger.info("Generating curated baseline dataset...")
    samples = [
        # Normal - English
        ("The new community center will open tomorrow at 9 AM.", "normal", "curated"),
        ("I really enjoyed the workshop on natural language processing.", "normal", "curated"),
        ("Public transport delays are frustrating, but the staff were polite.", "normal", "curated"),
        ("The local council approved funding for renewable energy projects.", "normal", "curated"),
        ("Healthy debate is essential for democratic decision making.", "normal", "curated"),
        ("Science education helps students understand climate challenges.", "normal", "curated"),
        ("Volunteers planted over 500 trees in the city park today.", "normal", "curated"),
        ("The match ended in a draw after ninety intense minutes.", "normal", "curated"),
        ("Let's review the quarterly report and address the discrepancies.", "normal", "curated"),
        ("Art exhibitions encourage cultural dialogue across communities.", "normal", "curated"),
        ("We should support local small businesses during renovations.", "normal", "curated"),
        ("The software update resolved memory leak issues on Windows.", "normal", "curated"),
        ("Libraries offer quiet spaces and free resources for everyone.", "normal", "curated"),
        ("Good morning everyone, wishing you all a productive and happy week!", "normal", "curated"),
        ("The recipe calls for olive oil, garlic, tomatoes, and fresh basil.", "normal", "curated"),
        # Normal - Hindi / Hinglish
        ("आज मौसम बहुत सुहावना है और बारिश हो रही है।", "normal", "curated"),
        ("सभी नागरिकों को अपने मताधिकार का प्रयोग अवश्य करना चाहिए।", "normal", "curated"),
        ("Ham sab milkar project ko safal banayenge, team work zaroori hai.", "normal", "curated"),
        ("Bharat ke vibhinn rajyon mein alag alag sanskritiyan dekhne ko milti hain.", "normal", "curated"),
        ("Vidyarthiyon ne vigyan mela mein shandar pradarshan kiya.", "normal", "curated"),
        ("Shanti aur sadbhavna samaj ke vikas ke liye aavashyak hain.", "normal", "curated"),
        ("Subah ki sair swasthya ke liye labhdayak hoti hai.", "normal", "curated"),
        ("Kripya katar mein khade rahein aur apni bari ki pratiksha karein.", "normal", "curated"),

        # Offensive - English (Profanity, insult, aggressive without protected target)
        ("This is the most stupid and brainless movie I have ever watched.", "offensive", "curated"),
        ("Shut your mouth, you incompetent jerk, nobody asked for your opinion.", "offensive", "curated"),
        ("The ref was blind and totally corrupt, what a garbage refereeing performance.", "offensive", "curated"),
        ("Stop whining like an annoying idiot and do your damn job.", "offensive", "curated"),
        ("Your presentation was absolute crap and a waste of everyone's afternoon.", "offensive", "curated"),
        ("You are completely clueless and talk nonsense all day long.", "offensive", "curated"),
        ("Get the hell out of my face before I lose my temper.", "offensive", "curated"),
        ("What a pathetic excuse for a customer support team, utter clowns.", "offensive", "curated"),
        ("This arrogant jerk thinks he owns the entire company.", "offensive", "curated"),
        ("Screw this broken buggy mess of a game, totally ripped off.", "offensive", "curated"),
        ("You lazy slob, clean up your own mess instead of dumping it on others.", "offensive", "curated"),
        ("Only a complete moron would believe such ridiculous conspiracy gossip.", "offensive", "curated"),
        # Offensive - Hindi / Hinglish
        ("Kutte ki tarah bhonkna band kar aur dhang se baat kar.", "offensive", "curated"),
        ("Kitna besharam aur ghatiya aadmi hai, bilkul akal nahi hai.", "offensive", "curated"),
        ("Bekaar ka drama band karo aur chupchap kaam karo pagal kahin ka.", "offensive", "curated"),
        ("Dimag kharab mat karo mera, chup baitho warna theek nahi hoga.", "offensive", "curated"),
        ("Tumhara pura dimaag khali hai, bewakoof jaisi baatein karte ho.", "offensive", "curated"),
        ("Aisa bakwaas aur nikamma insaan maine apni zindagi mein nahi dekha.", "offensive", "curated"),

        # Hate - English (Slurs, dehumanization, threats against protected groups/identities)
        ("All immigrants are vermin infecting our country and must be forcibly removed.", "hate", "curated"),
        ("Those people are subhuman animals who have no place in civilized society.", "hate", "curated"),
        ("They should exterminate that entire religious group from the face of the earth.", "hate", "curated"),
        ("Every single one of them is a terrorist parasite living off our taxes.", "hate", "curated"),
        ("We need to purge these ethnic minorities before they destroy our race.", "hate", "curated"),
        ("Go back to your dirty homeland, your kind does not belong here.", "hate", "curated"),
        ("Women are biologically inferior creatures meant only to serve men.", "hate", "curated"),
        ("Those disabled freaks are a genetic burden and should not be allowed to exist.", "hate", "curated"),
        ("Death to all followers of that disgusting religion, burn down their temples.", "hate", "curated"),
        ("Kill them all in the streets, wipe them out without mercy.", "hate", "curated"),
        ("They are like cockroaches spreading disease in our sacred motherland.", "hate", "curated"),
        ("These foreigners are invading our borders, shoot them on sight.", "hate", "curated"),
        # Hate - Hindi / Hinglish
        ("In sab gaddaron aur mullo ko desh se bahar phenko ya jaan se maar do.", "hate", "curated"),
        ("Yeh jaati ke log keede-makode hain, inka poora vansh khatam kar dena chahiye.", "hate", "curated"),
        ("Un sab dharam ke logon ko zinda jala dena chahiye, yeh suar hain.", "hate", "curated"),
        ("Videshi ghuspaithiyon ko goli maar do, inko mitti mein mila do.", "hate", "curated"),
        ("Inko yahan rehne ka koi adhikar nahi, inka poora safaya hona chahiye.", "hate", "curated"),
        ("Yeh qaum dharti par bojh hai, inko marne ke liye chhod do.", "hate", "curated"),
    ]

    # Replicate with minor variations to ensure healthy distribution if standalone
    augmented = []
    for text, label, source in samples:
        augmented.append({"text": text, "label": label, "source": source})
        # Add slight casing / punctuation variation for robustness
        augmented.append({"text": text.lower(), "label": label, "source": source})
        augmented.append({"text": f"{text} #discussion", "label": label, "source": source})

    return pd.DataFrame(augmented)


def fetch_measuring_hate_speech(max_samples: Optional[int] = None) -> Optional[pd.DataFrame]:
    """
    Download and preprocess ucberkeley-dlab/measuring-hate-speech from Hugging Face.
    Taxonomy mapping based on hate_speech_score:
      - score > 0.5: hate
      - -1.0 <= score <= 0.5: offensive
      - score < -1.0: normal
    """
    logger.info("Attempting to load 'ucberkeley-dlab/measuring-hate-speech'...")
    try:
        from datasets import load_dataset

        ds = load_dataset("ucberkeley-dlab/measuring-hate-speech", split="train")
        df = ds.to_pandas()
        logger.info(f"Loaded measuring-hate-speech raw: {len(df)} rows.")

        if "text" not in df.columns:
            logger.warning("measuring-hate-speech does not have 'text' column.")
            return None

        # Filter valid rows
        df = df.dropna(subset=["text"])
        df = df[df["text"].str.strip().str.len() > 3]

        # Use hate_speech_score continuous metric
        if "hate_speech_score" in df.columns:
            def map_score_to_label(score: float) -> str:
                if score > 0.5:
                    return "hate"
                elif score >= -1.0:
                    return "offensive"
                return "normal"

            df["label"] = df["hate_speech_score"].apply(map_score_to_label)
        elif "hatespeech" in df.columns:
            # discrete annotation fallback (0: none, 1: offensive, 2: hate)
            mapping = {0: "normal", 1: "offensive", 2: "hate"}
            df["label"] = df["hatespeech"].map(mapping).fillna("normal")
        else:
            logger.warning("Could not find hate speech scoring column in measuring-hate-speech.")
            return None

        df["source"] = "measuring_hate_speech"
        processed = df[["text", "label", "source"]].drop_duplicates(subset=["text"])

        if max_samples and len(processed) > max_samples:
            # Sample proportionately
            sampled_dfs = []
            per_class = max_samples // 3
            for lbl in LABELS:
                sub = processed[processed["label"] == lbl]
                n = min(len(sub), per_class)
                sampled_dfs.append(sub.sample(n=n, random_state=42))
            processed = pd.concat(sampled_dfs).sample(frac=1.0, random_state=42)

        logger.info(f"Prepared measuring-hate-speech: {len(processed)} rows.")
        return processed

    except Exception as exc:
        logger.warning(f"Failed to load 'ucberkeley-dlab/measuring-hate-speech': {exc}")
        return None


def fetch_hatexplain(max_samples: Optional[int] = None) -> Optional[pd.DataFrame]:
    """
    Download and preprocess HateXplain dataset from Hugging Face.
    Taxonomy mapping:
      0: hate speech -> hate
      1: normal -> normal
      2: offensive -> offensive
    """
    logger.info("Attempting to load 'hatexplain' from Hugging Face...")
    try:
        from datasets import load_dataset

        ds = load_dataset("hatexplain")
        records = []

        mapping = {0: "hate", 1: "normal", 2: "offensive"}

        for split_name in ["train", "validation", "test"]:
            if split_name not in ds:
                continue
            for item in ds[split_name]:
                post_tokens = item.get("post_tokens", [])
                text = " ".join(post_tokens).strip()
                if not text:
                    continue

                annotators = item.get("annotators", [])
                labels = [a.get("label") for a in annotators if "label" in a]
                if not labels:
                    continue

                # Majority vote
                vote = Counter(labels).most_common(1)[0][0]
                mapped_label = mapping.get(vote, "normal")
                records.append({
                    "text": text,
                    "label": mapped_label,
                    "source": "hatexplain",
                })

        if not records:
            return None

        df = pd.DataFrame(records).drop_duplicates(subset=["text"])
        logger.info(f"Loaded HateXplain: {len(df)} rows.")

        if max_samples and len(df) > max_samples:
            df = df.sample(n=max_samples, random_state=42)

        return df

    except Exception as exc:
        logger.warning(f"Failed to load 'hatexplain': {exc}")
        return None


def fetch_multilingual_datasets(max_samples: Optional[int] = None) -> Optional[pd.DataFrame]:
    """
    Attempt to load multilingual/Hindi hate speech data (e.g. Hate-speech-CNERG/deoffxlm-data or similar).
    """
    candidates = [
        ("Hate-speech-CNERG/deoffxlm-data", None),
        ("ai4bharat/indic-glue", "hasoc.hi"),
    ]

    for dataset_id, sub_config in candidates:
        try:
            logger.info(f"Attempting multilingual dataset '{dataset_id}'...")
            from datasets import load_dataset

            kwargs = {"split": "train"}
            if sub_config:
                kwargs["name"] = sub_config

            ds = load_dataset(dataset_id, **kwargs)
            df = ds.to_pandas()
            text_col = next((c for c in ["text", "sentence", "post", "tweet"] if c in df.columns), None)
            label_col = next((c for c in ["label", "hate", "task_1", "class"] if c in df.columns), None)

            if text_col and label_col:
                df = df[[text_col, label_col]].dropna()
                df = df.rename(columns={text_col: "text", label_col: "raw_label"})

                # Standardize binary / 3-class into our taxonomy
                def map_multi_label(v: object) -> str:
                    s = str(v).lower()
                    if s in ["1", "hate", "hof", "hateful"]:
                        return "hate"
                    elif s in ["off", "offensive", "profane"]:
                        return "offensive"
                    return "normal"

                df["label"] = df["raw_label"].apply(map_multi_label)
                df["source"] = dataset_id.split("/")[-1]
                processed = df[["text", "label", "source"]].drop_duplicates(subset=["text"])
                logger.info(f"Loaded {len(processed)} samples from {dataset_id}.")
                return processed
        except Exception as exc:
            logger.info(f"Could not load {dataset_id}: {exc}")

    return None


def generate_dataset_card(
    output_path: Path,
    total_samples: int,
    train_counts: Dict[str, int],
    val_counts: Dict[str, int],
    test_counts: Dict[str, int],
    source_counts: Dict[str, int],
) -> None:
    """Generate Markdown dataset card documenting provenance, taxonomy, and metrics."""
    content = f"""# NarrativeLens AI - Hate Speech Dataset Card

## 1. Dataset Overview

* **Unified Taxonomy**: 3-Class Categorization
  * `normal`: Neutral, constructive, or benign discourse.
  * `offensive`: Profanity, insults, abrasive sentiment without targeting protected identity groups.
  * `hate`: Targeted abuse, slurs, dehumanization, or threats directed against protected demographic groups (race, religion, gender, sexual orientation, disability, nationality).
* **Target Model**: `FacebookAI/xlm-roberta-base` cross-lingual classifier.
* **Total Instances**: {total_samples:,}
* **Data Sources Represented**: {", ".join(source_counts.keys())}

---

## 2. Splits and Class Distribution

| Split | Normal | Offensive | Hate | Total |
| :--- | :--- | :--- | :--- | :--- |
| **Train (80%)** | {train_counts.get('normal', 0):,} | {train_counts.get('offensive', 0):,} | {train_counts.get('hate', 0):,} | {sum(train_counts.values()):,} |
| **Validation (10%)** | {val_counts.get('normal', 0):,} | {val_counts.get('offensive', 0):,} | {val_counts.get('hate', 0):,} | {sum(val_counts.values()):,} |
| **Test (10%)** | {test_counts.get('normal', 0):,} | {test_counts.get('offensive', 0):,} | {test_counts.get('hate', 0):,} | {sum(test_counts.values()):,} |
| **Combined** | **{train_counts.get('normal', 0) + val_counts.get('normal', 0) + test_counts.get('normal', 0):,}** | **{train_counts.get('offensive', 0) + val_counts.get('offensive', 0) + test_counts.get('offensive', 0):,}** | **{train_counts.get('hate', 0) + val_counts.get('hate', 0) + test_counts.get('hate', 0):,}** | **{total_samples:,}** |

### Source Distribution:
{chr(10).join([f"- **{src}**: {cnt:,} examples ({cnt/total_samples*100:.1f}%)" for src, cnt in source_counts.items()])}

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
"""
    output_path.write_text(content, encoding="utf-8")
    logger.info(f"Dataset card successfully saved to {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download and prepare hate speech datasets.")
    parser.add_argument(
        "--output_dir",
        type=str,
        default="ml/datasets",
        help="Directory to store train.csv, val.csv, test.csv, and dataset_card.md",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)",
    )
    parser.add_argument(
        "--max_samples",
        type=int,
        default=None,
        help="Optional maximum number of samples to include per source for quick iteration",
    )
    parser.add_argument(
        "--no_hatexplain",
        action="store_true",
        help="Skip downloading HateXplain dataset",
    )
    parser.add_argument(
        "--no_multilingual",
        action="store_true",
        help="Skip downloading multilingual datasets",
    )

    args = parser.parse_args()
    set_seed(args.seed)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    collected_dfs: List[pd.DataFrame] = []

    # 1. Primary: Measuring Hate Speech
    mhs_df = fetch_measuring_hate_speech(max_samples=args.max_samples)
    if mhs_df is not None and len(mhs_df) > 0:
        collected_dfs.append(mhs_df)

    # 2. HateXplain
    if not args.no_hatexplain:
        hx_df = fetch_hatexplain(max_samples=args.max_samples)
        if hx_df is not None and len(hx_df) > 0:
            collected_dfs.append(hx_df)

    # 3. Multilingual / Hindi
    if not args.no_multilingual:
        multi_df = fetch_multilingual_datasets(max_samples=args.max_samples)
        if multi_df is not None and len(multi_df) > 0:
            collected_dfs.append(multi_df)

    # 4. Fallback / Seed enrichment to guarantee dataset completeness and multilingual balance
    curated_df = create_fallback_dataset()
    collected_dfs.append(curated_df)

    # Merge all datasets
    full_df = pd.concat(collected_dfs, ignore_index=True)
    full_df = full_df.dropna(subset=["text", "label"])
    full_df["text"] = full_df["text"].astype(str).str.strip()
    full_df = full_df[full_df["text"].str.len() > 3]
    full_df = full_df.drop_duplicates(subset=["text"])

    # Ensure all labels belong to LABELS
    full_df = full_df[full_df["label"].isin(LABELS)]

    logger.info(f"Total unified dataset size: {len(full_df)} samples.")
    source_counts = full_df["source"].value_counts().to_dict()

    # Stratified Train/Val/Test Split (80/10/10)
    train_df, temp_df = train_test_split(
        full_df,
        test_size=0.20,
        random_state=args.seed,
        stratify=full_df["label"],
    )

    val_df, test_df = train_test_split(
        temp_df,
        test_size=0.50,
        random_state=args.seed,
        stratify=temp_df["label"],
    )

    # Save to CSV
    train_path = output_dir / "train.csv"
    val_path = output_dir / "val.csv"
    test_path = output_dir / "test.csv"

    train_df.to_csv(train_path, index=False, encoding="utf-8")
    val_df.to_csv(val_path, index=False, encoding="utf-8")
    test_df.to_csv(test_path, index=False, encoding="utf-8")

    train_counts = train_df["label"].value_counts().to_dict()
    val_counts = val_df["label"].value_counts().to_dict()
    test_counts = test_df["label"].value_counts().to_dict()

    print("\n" + "=" * 60)
    print("DATASET PREPARATION COMPLETED SUCCESSFULLY")
    print("=" * 60)
    print(f"Total Samples: {len(full_df):,}")
    print(f"Train Split  : {len(train_df):,} (80%) -> {train_counts}")
    print(f"Val Split    : {len(val_df):,} (10%) -> {val_counts}")
    print(f"Test Split   : {len(test_df):,} (10%) -> {test_counts}")
    print(f"Sources      : {source_counts}")
    print(f"Files saved to: {output_dir.resolve()}")
    print("=" * 60 + "\n")

    # Generate Dataset Card
    card_path = output_dir / "dataset_card.md"
    generate_dataset_card(
        card_path,
        total_samples=len(full_df),
        train_counts=train_counts,
        val_counts=val_counts,
        test_counts=test_counts,
        source_counts=source_counts,
    )


if __name__ == "__main__":
    main()
