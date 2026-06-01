#!/usr/bin/env python3
"""fetch_news.py — Fetch RSS/JSON feeds, deduplicate, output news_raw.json"""

import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import feedparser
import requests
import yaml

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config" / "sources.yml"
RAW_OUTPUT = BASE_DIR / "news_raw.json"
SEEN_FILE = BASE_DIR / ".seen_urls.json"

REQUEST_TIMEOUT = 15  # seconds per feed
MAX_ARTICLES_PER_FEED = 30
SUMMARY_MAX_LENGTH = 300

# HTML tag stripping pattern
HTML_TAG_RE = re.compile(r"<[^>]+>")

def load_sources():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not data or "sources" not in data:
        print("  ⚠️  sources.yml is empty or missing 'sources' key")
        return []
    return data["sources"]

def load_seen_urls():
    if SEEN_FILE.exists():
        try:
            with open(SEEN_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except (json.JSONDecodeError, OSError) as e:
            print(f"  ⚠️  Corrupt .seen_urls.json, starting fresh: {e}")
            return set()
    return set()

def save_seen_urls(urls: set):
    try:
        with open(SEEN_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(urls), f, ensure_ascii=False)
    except OSError as e:
        print(f"  ⚠️  Failed to save .seen_urls.json: {e}")

def fetch_rss(source: dict) -> list:
    """Fetch a single RSS feed and return articles."""
    articles = []
    try:
        resp = requests.get(source["url"], timeout=REQUEST_TIMEOUT, headers={
            "User-Agent": "AI-News-Daily/1.0"
        })
        resp.raise_for_status()
    except Exception as e:
        print(f"  ⚠️  Failed to fetch {source['name']}: {e}")
        return []

    if source.get("type") == "json":
        # JSON API (e.g. HN Algolia)
        try:
            data = resp.json()
            for hit in data.get("hits", []):
                link = hit.get("url") or hit.get("story_url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
                title = hit.get("title", "")
                if title and link:
                    articles.append({
                        "title": title.strip(),
                        "link": link,
                        "summary": (hit.get("story_text") or "")[:SUMMARY_MAX_LENGTH],
                        "published": hit.get("created_at", ""),
                        "source": source["name"],
                        "category": source["category"],
                    })
        except Exception as e:
            print(f"  ⚠️  JSON parse error for {source['name']}: {e}")
    else:
        # RSS/Atom feed
        feed = feedparser.parse(resp.content)
        for entry in feed.entries[:MAX_ARTICLES_PER_FEED]:
            link = entry.get("link", "")
            title = entry.get("title", "")
            if not title or not link:
                continue
            pub = entry.get("published_parsed") or entry.get("updated_parsed")
            pub_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", pub) if pub else ""
            summary = (entry.get("summary") or entry.get("description") or "")[:SUMMARY_MAX_LENGTH]
            # Strip HTML tags from summary
            summary = HTML_TAG_RE.sub(" ", summary).strip()
            articles.append({
                "title": title.strip(),
                "link": link,
                "summary": summary.strip(),
                "published": pub_str,
                "source": source["name"],
                "category": source["category"],
            })

    return articles

def url_hash(url: str) -> str:
    return hashlib.md5(url.encode("utf-8")).hexdigest()

def main():
    print("📡 Fetching news from all sources...")
    sources = load_sources()
    seen = load_seen_urls()
    all_articles = []
    new_urls = set()

    for src in sources:
        print(f"  → {src['name']} ({src['category']})")
        articles = fetch_rss(src)
        for a in articles:
            h = url_hash(a["link"])
            if h not in seen:
                new_urls.add(h)
                all_articles.append(a)

    print(f"\n📊 Total fresh articles: {len(all_articles)}")

    # Sort by published time (newest first), unknown time fallback to end
    def sort_key(a):
        return a.get("published", "")

    all_articles.sort(key=sort_key, reverse=True)

    # Save output
    data = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "total": len(all_articles),
        "articles": all_articles,
    }
    with open(RAW_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # Update seen URLs (merge old + new)
    seen.update(new_urls)
    save_seen_urls(seen)

    print(f"✅ news_raw.json saved with {len(all_articles)} articles")

if __name__ == "__main__":
    main()
