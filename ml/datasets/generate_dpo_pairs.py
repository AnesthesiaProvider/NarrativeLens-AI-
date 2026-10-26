"""DPO Preference Dataset Generator.

Extracts feedback records from the Human Feedback database (and supplements with
gold-standard expert preference instances) to generate pairwise training records
for Direct Preference Optimization (DPO).

Each instance contains:
  - prompt: Structured evaluation context (Context + Text + Preliminary Model Output)
  - chosen: De-escalating, accurate verdict with explicit target group and grounded rationale
  - rejected: Misclassified, uncalibrated, or hallucinated response

Output:
  - ml/datasets/dpo_preference_train.jsonl
  - ml/datasets/dpo_preference_val.jsonl
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
import sqlite3
from typing import Any, Dict, List
import random

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("generate_dpo_pairs")

SEED_DPO_PAIRS = [
    {
        "prompt": (
            "You are an expert NLP safety analyst evaluating user comments for online safety.\n"
            "Context: \"Community Discussion on Immigration Reform\"\n"
            "User Comment: \"These filthy immigrants are vermin infecting our country and must be exterminated.\"\n"
            "Initial Classifier: Hate Speech (Confidence: 0.91)"
        ),
        "chosen": (
            "{\n"
            "  \"verdict\": \"Hate Speech\",\n"
            "  \"targeted_group\": \"Nationality/Immigration (Immigrants)\",\n"
            "  \"explanation\": \"The comment employs dehumanizing biological metaphors ('vermin', 'infecting') paired with explicit calls to lethal violence ('must be exterminated'). This directly constitutes incitement to violence against a protected demographic group.\"\n"
            "}"
        ),
        "rejected": (
            "{\n"
            "  \"verdict\": \"Offensive\",\n"
            "  \"targeted_group\": \"None\",\n"
            "  \"explanation\": \"The user is expressing strong disagreement with immigration policy using harsh vocabulary and vulgar language.\"\n"
            "}"
        ),
    },
    {
        "prompt": (
            "You are an expert NLP safety analyst evaluating user comments for online safety.\n"
            "Context: \"Gaming Livestream Chat\"\n"
            "User Comment: \"Shut up you stupid idiot and stop crying like a baby, do your job.\"\n"
            "Initial Classifier: Offensive (Confidence: 0.52)"
        ),
        "chosen": (
            "{\n"
            "  \"verdict\": \"Offensive\",\n"
            "  \"targeted_group\": \"None\",\n"
            "  \"explanation\": \"The comment contains aggressive personal insults ('stupid idiot', 'crying like a baby') but does not target any protected demographic group or incite physical violence. It violates civility standards but is not hate speech.\"\n"
            "}"
        ),
        "rejected": (
            "{\n"
            "  \"verdict\": \"Hate Speech\",\n"
            "  \"targeted_group\": \"Children\",\n"
            "  \"explanation\": \"Calling someone a crying baby constitutes severe identity harassment and discriminatory hate speech against youth.\"\n"
            "}"
        ),
    },
    {
        "prompt": (
            "You are an expert NLP safety analyst evaluating user comments for online safety.\n"
            "Context: \"History Documentary Excerpt\"\n"
            "User Comment: \"Lucifer was the Latin name for the morning star, personified as a celestial deity in Roman mythology.\"\n"
            "Initial Classifier: Neutral (Confidence: 0.81)"
        ),
        "chosen": (
            "{\n"
            "  \"verdict\": \"Neutral\",\n"
            "  \"targeted_group\": \"None\",\n"
            "  \"explanation\": \"This is an objective historical and mythological reference explaining etymology and Roman folklore. It contains zero hostility, profanity, or group denigration.\"\n"
            "}"
        ),
        "rejected": (
            "{\n"
            "  \"verdict\": \"Hate Speech\",\n"
            "  \"targeted_group\": \"Religion\",\n"
            "  \"explanation\": \"Mentioning Lucifer is inherently blasphemous and incites religious extremism against Christian believers.\"\n"
            "}"
        ),
    },
    {
        "prompt": (
            "You are an expert NLP safety analyst evaluating user comments for online safety.\n"
            "Context: \"Tech Industry News Article\"\n"
            "User Comment: \"Women are biologically inferior at coding and should stick to cleaning the house instead of taking engineering jobs.\"\n"
            "Initial Classifier: Hate Speech (Confidence: 0.88)"
        ),
        "chosen": (
            "{\n"
            "  \"verdict\": \"Hate Speech\",\n"
            "  \"targeted_group\": \"Gender (Women)\",\n"
            "  \"explanation\": \"The comment advances biological determinism and misogynistic exclusion, asserting that an entire gender is inherently inferior and should be denied professional participation. This constitutes discriminatory hate speech.\"\n"
            "}"
        ),
        "rejected": (
            "{\n"
            "  \"verdict\": \"Neutral\",\n"
            "  \"targeted_group\": \"None\",\n"
            "  \"explanation\": \"The user is offering personal occupational preferences and traditional family role opinions in a tech career discussion.\"\n"
            "}"
        ),
    },
    {
        "prompt": (
            "You are an expert NLP safety analyst evaluating user comments for online safety.\n"
            "Context: \"Political Rally Forum\"\n"
            "User Comment: \"In sab deshdrohiyo aur mullo ko desh se bahar phenko, inka poora safaya karo.\"\n"
            "Initial Classifier: Hate Speech (Confidence: 0.94)"
        ),
        "chosen": (
            "{\n"
            "  \"verdict\": \"Hate Speech\",\n"
            "  \"targeted_group\": \"Religion (Muslim)\",\n"
            "  \"explanation\": \"Uses communal slurs and dogwhistles in Hindi/Hinglish paired with calls for forced deportation and ethnic cleansing ('poora safaya karo'). This is direct incitement to religious persecution.\"\n"
            "}"
        ),
        "rejected": (
            "{\n"
            "  \"verdict\": \"Offensive\",\n"
            "  \"targeted_group\": \"None\",\n"
            "  \"explanation\": \"The commenter is passionately debating national security policies in a non-English language.\"\n"
            "}"
        ),
    },
]


def load_database_feedback(db_path: Path) -> List[Dict[str, Any]]:
    """Extract human review records from SQLite if available."""
    if not db_path.exists():
        return []

    extracted = []
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='human_feedbacks'")
        if not cursor.fetchone():
            return []

        # Join human_feedbacks -> classification_results -> documents to fetch text content
        query = (
            "SELECT d.content, c.predicted_label, h.corrected_label, h.explanation "
            "FROM human_feedbacks h "
            "LEFT JOIN classification_results c ON h.classification_id = c.id "
            "LEFT JOIN documents d ON c.document_id = d.id "
            "WHERE h.corrected_label IS NOT NULL AND d.content IS NOT NULL"
        )
        rows = cursor.execute(query).fetchall()

        for text, orig, corr, notes in rows:
            if not text or not corr:
                continue

            prompt = (
                f"You are an expert NLP safety analyst evaluating user comments for online safety.\n"
                f"Context: \"Platform Content Audit\"\n"
                f"User Comment: \"{text}\"\n"
                f"Initial Classifier: {orig}"
            )

            chosen = (
                "{\n"
                f'  "verdict": "{corr}",\n'
                f'  "targeted_group": "Identified by human moderator",\n'
                f'  "explanation": "Human analyst correction: {notes or "Validated ground truth label."}"\n'
                "}"
            )

            rejected = (
                "{\n"
                f'  "verdict": "{orig}",\n'
                '  "targeted_group": "None",\n'
                f'  "explanation": "Uncalibrated classifier assignment."\n'
                "}"
            )

            extracted.append({"prompt": prompt, "chosen": chosen, "rejected": rejected})
    except Exception as exc:
        logger.warning(f"Could not extract feedback from DB: {exc}")

    return extracted


def main() -> None:
    output_dir = Path("ml/datasets")
    output_dir.mkdir(parents=True, exist_ok=True)
    db_path = Path("backend/narrativelens.db")

    all_pairs = list(SEED_DPO_PAIRS)

    # Replicate and synthesize variations to form a robust calibration dataset
    for item in SEED_DPO_PAIRS:
        all_pairs.append({
            "prompt": item["prompt"] + "\nTask: Prioritize protecting vulnerable groups while avoiding censorship of factual discussions.",
            "chosen": item["chosen"],
            "rejected": item["rejected"],
        })

    # Add database feedback if present
    db_pairs = load_database_feedback(db_path)
    all_pairs.extend(db_pairs)

    random.seed(42)
    random.shuffle(all_pairs)

    split_idx = max(1, int(len(all_pairs) * 0.8))
    train_pairs = all_pairs[:split_idx]
    val_pairs = all_pairs[split_idx:]

    train_file = output_dir / "dpo_preference_train.jsonl"
    val_file = output_dir / "dpo_preference_val.jsonl"

    with open(train_file, "w", encoding="utf-8") as f:
        for p in train_pairs:
            f.write(json.dumps(p) + "\n")

    with open(val_file, "w", encoding="utf-8") as f:
        for p in val_pairs:
            f.write(json.dumps(p) + "\n")

    logger.info(f"Generated {len(train_pairs)} DPO training pairs in {train_file}")
    logger.info(f"Generated {len(val_pairs)} DPO validation pairs in {val_file}")


if __name__ == "__main__":
    main()
