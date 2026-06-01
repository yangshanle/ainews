#!/usr/bin/env python3
"""summarize.py — Call DeepSeek API to generate Chinese summaries for each article."""

import json
import os
import re
import time
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_INPUT = BASE_DIR / "news_raw.json"
FINAL_OUTPUT = BASE_DIR / "news_final.json"

# DeepSeek API config via 中转站
DEEPSEEK_API_URL = os.environ.get("DEEPSEEK_API_URL", "https://api.deepseek.com/v1/chat/completions")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

BATCH_SIZE = 5
MAX_RETRIES = 2


def summarize_batch(articles: list) -> list:
    """Send a batch of articles to DeepSeek and get summaries back."""
    if not DEEPSEEK_API_KEY:
        print("  ⚠️  No DEEPSEEK_API_KEY set, skipping summaries")
        for a in articles:
            a["ai_summary"] = ""
        return articles

    # Build the prompt
    lines = []
    for i, a in enumerate(articles):
        title = a["title"][:150]
        summary = (a["summary"] or "(no summary)")[:200]
        lines.append(f"{i+1}. Title: {title}\n   Excerpt: {summary}")

    prompt = f"""You are a Chinese news summarizer. For each news article below, write a ONE-SENTENCE Chinese summary (≤25 Chinese characters) that captures the core event. Return ONLY valid JSON array of strings, no other text.

Articles:
{"\n".join(lines)}
"""

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 500,
    }

    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.post(DEEPSEEK_API_URL, json=payload, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"].strip()

            # Strip markdown code fences (```json ... ```) then parse JSON
            content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip())
            summaries = json.loads(content)
            if not isinstance(summaries, list) or len(summaries) != len(articles):
                raise ValueError(f"Expected {len(articles)} summaries, got {len(summaries) if isinstance(summaries, list) else 0}")

            for a, s in zip(articles, summaries):
                a["ai_summary"] = s.strip()[:25]  # Enforce ≤25 chars
            return articles

        except Exception as e:
            print(f"  ⚠️  Attempt {attempt + 1} failed: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(2)

    # All retries failed — leave summaries empty
    for a in articles:
        a["ai_summary"] = ""
    return articles


def main() -> None:
    print("Generating AI summaries...")

    if not RAW_INPUT.exists():
        print("news_raw.json not found. Run fetch_news.py first.")
        return

    with open(RAW_INPUT, "r", encoding="utf-8") as f:
        data = json.load(f)

    articles = data.get("articles", [])
    if not articles:
        print("  ⚠️  No articles found in news_raw.json.")
        return
    print(f"  Total articles to summarize: {len(articles)}")

    # Process in batches
    summarized = []
    for i in range(0, len(articles), BATCH_SIZE):
        batch = articles[i : i + BATCH_SIZE]
        print(f"  Batch {i//BATCH_SIZE + 1}/{(len(articles) + BATCH_SIZE - 1)//BATCH_SIZE} ({len(batch)} articles)")
        batch = summarize_batch(batch)
        summarized.extend(batch)
        if i + BATCH_SIZE < len(articles):
            time.sleep(0.5)  # Rate limiting

    data["articles"] = summarized
    with open(FINAL_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    with_summary = sum(1 for a in summarized if a.get("ai_summary"))
    print(f"news_final.json saved. {with_summary}/{len(summarized)} articles have AI summaries.")


if __name__ == "__main__":
    main()
