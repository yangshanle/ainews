#!/usr/bin/env python3
"""build_site.py — Render Jinja2 templates to static HTML files."""

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
DOCS_DIR = BASE_DIR / "docs"
ARCHIVES_DIR = DOCS_DIR / "archives"
ASSETS_DIR = DOCS_DIR / "assets"

INPUT_FILE = BASE_DIR / "news_final.json"

CATEGORY_INFO = {
    "ai":     ("AI 新闻",     "🤖"),
    "tech":   ("科技动态",    "🖥️"),
    "general":("综合热点",    "🌍"),
}

WEEKDAY_CN = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]


def format_date(dt: datetime) -> tuple:
    """Return (date_cn, weekday_cn)."""
    date_cn = dt.strftime("%Y年%m月%d日")
    wd = WEEKDAY_CN[dt.weekday()]
    return date_cn, wd


def get_archives() -> list:
    """List existing archive files for sidebar."""
    if not ARCHIVES_DIR.exists():
        return []
    files = sorted(ARCHIVES_DIR.glob("*.html"), reverse=True)[:7]
    archives = []
    for f in files:
        label = f.stem  # YYYY-MM-DD
        try:
            dt = datetime.strptime(label, "%Y-%m-%d")
            label_cn = dt.strftime("%m月%d日")
        except:
            label_cn = label
        archives.append({"file": f.name, "label": label_cn})
    return archives


def main() -> None:
    print("🏗️  Building static site...")

    if not INPUT_FILE.exists():
        print("❌ news_final.json not found. Run fetch + summarize first.")
        return

    # Load data
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    articles = data.get("articles", [])
    fetched_at = data.get("fetched_at", "")

    if not articles:
        print("⚠️  No articles to build. Skipping.")
        return

    # Separate top story (first article) from the rest
    top_story = articles[0]
    remaining = articles[1:]

    # Group by category
    grouped = {cat_id: [] for cat_id in CATEGORY_INFO}

    for a in remaining:
        cat = a.get("category", "general")
        if cat in grouped:
            grouped[cat].append(a)
        else:
            grouped["general"].append(a)

    # Build category list for template
    categories = []
    stats = {"total": len(articles), "ai": 0, "tech": 0, "general": 0}
    for cat_id, (cat_name, icon) in CATEGORY_INFO.items():
        cat_articles = grouped.get(cat_id, [])
        stats[cat_id] = len(cat_articles)
        categories.append((cat_id, cat_name, icon, cat_articles))

    now = datetime.now(timezone.utc)
    date_cn, weekday_cn = format_date(now)
    archives = get_archives()

    # Setup Jinja2
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    env.globals["int"] = int  # Make int() available in templates

    # Render index.html
    index_tpl = env.get_template("index.html")
    index_html = index_tpl.render(
        date_cn=date_cn,
        weekday_cn=weekday_cn,
        top_story=top_story,
        categories=categories,
        stats=stats,
        archives=archives,
        fetched_at=fetched_at[:10] if fetched_at else "",
    )

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    with open(DOCS_DIR / "index.html", "w", encoding="utf-8") as f:
        f.write(index_html)
    print(f"  ✅ index.html generated ({len(articles)} articles)")

    # Render archive.html for today
    ARCHIVES_DIR.mkdir(parents=True, exist_ok=True)
    archive_tpl = env.get_template("archive.html")
    archive_file = now.strftime("%Y-%m-%d") + ".html"
    archive_html = archive_tpl.render(
        date_cn=date_cn,
        weekday_cn=weekday_cn,
        categories=categories,
        stats=stats,
        archives=[a for a in archives if a["file"] != archive_file],
    )
    with open(ARCHIVES_DIR / archive_file, "w", encoding="utf-8") as f:
        f.write(archive_html)
    print(f"  ✅ {archive_file} archived")

    # Ensure style.css exists
    css_src = ASSETS_DIR / "style.css"
    if not css_src.exists():
        print("  ⚠️  style.css not found in docs/assets/")

    print("🏁 Site build complete!")


if __name__ == "__main__":
    main()
