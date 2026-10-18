#!/usr/bin/env python3
"""CLI tool to scrape YouTube titles and comments (or web articles) and detect hate speech,
returning a comprehensive 'Need to Know' advisory and toxicity breakdown."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

# Enable UTF-8 console output for Windows terminals
if sys.stdout:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr:
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Ensure backend modules can be imported
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from dotenv import load_dotenv

# Load environment files
load_dotenv(Path(__file__).resolve().parent.parent / "backend" / ".env")
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from app.services.comment_hate_detector_service import comment_hate_detector_service


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scrape YouTube video titles and comments to detect hate speech and build safety advisories."
    )
    parser.add_argument(
        "--target",
        "-t",
        type=str,
        required=True,
        help="YouTube URL, Video ID, or search topic keyword (e.g. 'https://www.youtube.com/watch?v=...').",
    )
    parser.add_argument(
        "--max-comments",
        "-m",
        type=int,
        default=30,
        help="Maximum number of top comments to analyze (default: 30).",
    )
    parser.add_argument(
        "--json-out",
        "-j",
        type=str,
        default="",
        help="Optional file path to save raw JSON analysis output.",
    )

    args = parser.parse_args()

    print("\n" + "=" * 70)
    print(" 🔍 NarrativeLens AI — YouTube & Comment Hate Speech Detector")
    print("=" * 70)
    print(f"Target: {args.target}")
    print(f"Max comments: {args.max_comments}")
    print("Scraping and analyzing title & user discussions...\n")

    try:
        results = await comment_hate_detector_service.analyze_target(
            target=args.target, max_comments=args.max_comments
        )
    except Exception as exc:
        print(f"❌ Error analyzing target: {exc}", file=sys.stderr)
        sys.exit(1)

    meta = results["metadata"]
    title_eval = results["title_analysis"]
    metrics = results["metrics"]
    advisory = results["advisory"]

    print("-" * 70)
    print(" 📹 TARGET INFORMATION")
    print("-" * 70)
    print(f" Title:        {meta.get('title', 'N/A')}")
    print(f" Channel:      {meta.get('channel', 'N/A')}")
    print(f" URL:          {meta.get('url', 'N/A')}")
    if meta.get("view_count"):
        print(f" Stats:        {meta.get('view_count'):,} views | {meta.get('like_count'):,} likes")

    print("\n" + "-" * 70)
    print(" 🏷️  TITLE HATE SPEECH VERDICT")
    print("-" * 70)
    title_status = "🚨 HATE SPEECH" if title_eval["is_hate"] else ("⚠️ OFFENSIVE" if title_eval["is_offensive"] else "✅ NEUTRAL")
    print(f" Classification: {title_status} ({title_eval['label']})")
    print(f" Confidence:     {title_eval['confidence']*100:.2f}%")

    print("\n" + "-" * 70)
    print(" 📊 COMMUNITY DISCUSSION METRICS")
    print("-" * 70)
    print(f" Comments Scanned:     {metrics['total_scanned']}")
    print(f" Hate Speech Count:    {metrics['hate_count']} ({metrics['hate_rate']*100:.1f}%)")
    print(f" Offensive Count:      {metrics['offensive_count']}")
    print(f" Total Toxicity Rate:  {metrics['toxicity_rate']*100:.1f}%")
    print(f" Civil/Neutral Count:  {metrics['neutral_count']}")

    print("\n" + "=" * 70)
    print(f" 🛡️  WHAT SOMEONE NEEDS TO KNOW (Safety Advisory: {advisory['risk_label']})")
    print("=" * 70)
    for bullet in advisory["what_you_need_to_know"]:
        print(f"  • {bullet}")

    flagged = results["flagged_comments"]
    if flagged:
        print("\n" + "-" * 70)
        print(f" 🚩 FLAGGED TOXIC & HATE COMMENTS ({len(flagged)} detected)")
        print("-" * 70)
        for i, c in enumerate(flagged[:10], start=1):
            badge = "🚨 [HATE]" if c["is_hate"] else "⚠️ [OFFENSIVE]"
            print(f" {i}. {badge} @{c['author']} ({c['like_count']} likes | {c['confidence']*100:.1f}% conf):")
            print(f"    \"{c['text'].strip()}\"")
            if c["explanation_tokens"]:
                tok_str = ", ".join([f"{t['token']} ({t['score']})" for t in c["explanation_tokens"]])
                print(f"    Keywords: {tok_str}")
            print()
    else:
        print("\n ✅ No toxic or hateful comments detected in this sample.")

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"💾 Full results saved to: {args.json_out}")

    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
