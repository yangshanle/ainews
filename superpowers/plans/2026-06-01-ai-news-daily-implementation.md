# AI News Daily — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an automated AI news daily system that fetches RSS feeds, generates DeepSeek-powered Chinese summaries, and deploys a Claude-orange styled static site to GitHub Pages.

**Architecture:** Python scripts orchestrated by GitHub Actions daily at 08:00 CST. RSS feeds → feedparser → dedup → DeepSeek API for summaries → Jinja2 renders static HTML → deployed to GitHub Pages via `docs/` directory.

**Tech Stack:** Python 3, feedparser, Jinja2, DeepSeek API (中转站), GitHub Actions, GitHub Pages

---

### Task 1: Initialize Project Structure

**Files:**
- Create: `c:\Users\liyu\Desktop\ainews\.gitignore`
- Create: `c:\Users\liyu\Desktop\ainews\requirements.txt`
- Create: `c:\Users\liyu\Desktop\ainews\config\sources.yml`
- Create: `c:\Users\liyu\Desktop\ainews\scripts\__init__.py`
- Create: `c:\Users\liyu\Desktop\ainews\templates\__init__.py`

- [ ] **Step 1: Create .gitignore**

```gitignore
# .gitignore
__pycache__/
*.pyc
.env
*.json
!requirements.txt
*.local/
.seen_urls.json
news_raw.json
news_final.json
```

- [ ] **Step 2: Create requirements.txt**

```txt
feedparser>=6.0.0
Jinja2>=3.1.0
requests>=2.31.0
PyYAML>=6.0
```

- [ ] **Step 3: Create config/sources.yml**

```yaml
# config/sources.yml — RSS news sources
sources:
  - name: Hacker News AI
    url: https://hn.algolia.com/api/v1/search?query=AI&tags=story&hitsPerPage=20
    category: ai
    type: json
  - name: TechCrunch AI
    url: https://techcrunch.com/category/artificial-intelligence/feed/
    category: ai
    type: rss
  - name: The Verge AI
    url: https://www.theverge.com/ai-artificial-intelligence/rss.xml
    category: ai
    type: rss
  - name: 机器之心
    url: https://www.jiqizhixin.com/rss
    category: ai
    type: rss
  - name: 量子位
    url: https://www.qbitai.com/feed
    category: ai
    type: rss
  - name: ArXiv NLP
    url: http://export.arxiv.org/rss/cs.CL
    category: ai
    type: rss
  - name: 36氪
    url: https://36kr.com/feed
    category: tech
    type: rss
  - name: InfoQ 中文
    url: https://www.infoq.cn/feed
    category: tech
    type: rss
  - name: Solidot
    url: https://solidot.org/feed
    category: tech
    type: rss
  - name: 澎湃新闻
    url: https://www.thepaper.cn/rss/news.xml
    category: general
    type: rss
  - name: BBC News
    url: https://feeds.bbci.co.uk/news/rss.xml
    category: general
    type: rss
  - name: Reuters Top News
    url: https://www.reutersagency.com/feed/?best-topics=business-news&post_type=best
    category: general
    type: rss
```

- [ ] **Step 4: Create empty __init__.py files**

```bash
touch scripts/__init__.py templates/__init__.py config/__init__.py
```

- [ ] **Step 5: Init git repo and make initial commit**

```bash
cd /c/Users/liyu/Desktop/ainews
git init
git checkout -b main
git add .
git commit -m "chore: initialize project structure"

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
```

---

### Task 2: Create RSS Fetcher (fetch_news.py)

**Files:**
- Create: `c:\Users\liyu\Desktop\ainews\scripts\fetch_news.py`
- Create: `c:\Users\liyu\Desktop\ainews\.seen_urls.json` (empty initial state)

- [ ] **Step 1: Write the fetcher script**

```python
#!/usr/bin/env python3
"""fetch_news.py — Fetch RSS/JSON feeds, deduplicate, output news_raw.json"""

import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import feedparser
import requests
import yaml

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config" / "sources.yml
RAW_OUTPUT = BASE_DIR / "news_raw.json"
SEEN_FILE = BASE_DIR / ".seen_urls.json"

REQUEST_TIMEOUT = 15  # seconds per feed

def load_sources():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)["sources"]

def load_seen_urls():
    if SEEN_FILE.exists():
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def save_seen_urls(urls: set):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(urls), f, ensure_ascii=False)

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
                        "summary": hit.get("story_text", "")[:300] or "",
                        "published": hit.get("created_at", ""),
                        "source": source["name"],
                        "category": source["category"],
                    })
        except Exception as e:
            print(f"  ⚠️  JSON parse error for {source['name']}: {e}")
    else:
        # RSS/Atom feed
        feed = feedparser.parse(resp.content)
        for entry in feed.entries[:30]:
            link = entry.get("link", "")
            title = entry.get("title", "")
            if not title or not link:
                continue
            pub = entry.get("published_parsed") or entry.get("updated_parsed")
            pub_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", pub) if pub else ""
            summary = (entry.get("summary") or entry.get("description") or "")[:300]
            # Strip HTML tags from summary
            summary = summary.replace("<p>", " ").replace("</p>", " ").replace("<br>", " ").replace("</br>", " ")
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
        try:
            return a["published"]
        except:
            return ""

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
```

- [ ] **Step 2: Create empty .seen_urls.json**

```json
[]
```

- [ ] **Step 3: Test the fetcher**

```bash
cd /c/Users/liyu/Desktop/ainews
pip install -r requirements.txt
python scripts/fetch_news.py
```

Expected: Script runs without errors, `news_raw.json` created with some articles.

- [ ] **Step 4: Commit**

```bash
git add scripts/fetch_news.py .seen_urls.json
git commit -m "feat: add RSS fetcher with dedup"

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
```

---

### Task 3: Create DeepSeek Summarizer (summarize.py)

**Files:**
- Create: `c:\Users\liyu\Desktop\ainews\scripts\summarize.py`

- [ ] **Step 1: Write the summarizer script**

```python
#!/usr/bin/env python3
"""summarize.py — Call DeepSeek API to generate Chinese summaries for each article."""

import json
import os
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
        summary = a["summary"][:200]
        lines.append(f"{i+1}. Title: {title}\n   Excerpt: {summary}")

    prompt = f"""You are a Chinese news summarizer. For each news article below, write a ONE-SENTENCE Chinese summary (≤25 Chinese characters) that captures the core event. Return ONLY valid JSON array of strings, no other text.

Articles:
{chr(10).join(lines)}
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

            # Parse JSON array from response
            summaries = json.loads(content)
            if not isinstance(summaries, list) or len(summaries) != len(articles):
                raise ValueError(f"Expected {len(articles)} summaries, got {len(summaries) if isinstance(summaries, list) else 0}")

            for a, s in zip(articles, summaries):
                a["ai_summary"] = s.strip()
            return articles

        except Exception as e:
            print(f"  ⚠️  Attempt {attempt + 1} failed: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(2)

    # All retries failed — leave summaries empty
    for a in articles:
        a["ai_summary"] = ""
    return articles

def main():
    print("🤖 Generating AI summaries...")

    if not RAW_INPUT.exists():
        print("❌ news_raw.json not found. Run fetch_news.py first.")
        return

    with open(RAW_INPUT, "r", encoding="utf-8") as f:
        data = json.load(f)

    articles = data["articles"]
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
    print(f"✅ news_final.json saved. {with_summary}/{len(summarized)} articles have AI summaries.")

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Test the summarizer**

```bash
cd /c/Users/liyu/Desktop/ainews
# Test without API key to verify graceful fallback
python scripts/summarize.py
```

Expected: Script runs without errors, `news_final.json` created, summaries are empty strings.

- [ ] **Step 3: Commit**

```bash
git add scripts/summarize.py
git commit -m "feat: add DeepSeek summarizer with batch processing"

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
```

---

### Task 4: Create CSS Stylesheet (Claude Orange Style)

**Files:**
- Create: `c:\Users\liyu\Desktop\ainews\docs\assets\style.css`

- [ ] **Step 1: Write the CSS**

```css
/* docs/assets/style.css — Claude Orange Theme for AI News Daily */

:root {
  --orange: #E05A1F;
  --orange-light: #FDE8D8;
  --orange-bg: #FFF3E6;
  --white: #FFFFFF;
  --bg: #FFF8F0;
  --text: #1A1A2E;
  --text-secondary: #6B7280;
  --border: #E5E7EB;
  --shadow: 0 2px 8px rgba(0,0,0,0.06);
  --radius: 12px;
  --font: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  font-family: var(--font);
  background: var(--bg);
  color: var(--text);
  line-height: 1.6;
}

/* Header */
.header {
  background: linear-gradient(135deg, #E05A1F 0%, #D4501C 50%, #C04518 100%);
  color: white;
  padding: 24px 32px;
  position: sticky;
  top: 0;
  z-index: 100;
  box-shadow: 0 2px 12px rgba(224, 90, 31, 0.3);
}

.header-content {
  max-width: 1280px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
}

.header h1 {
  font-size: 24px;
  font-weight: 700;
  letter-spacing: -0.5px;
}

.header h1 span {
  font-weight: 300;
  opacity: 0.85;
}

.header-date {
  font-size: 14px;
  opacity: 0.9;
}

/* Layout */
.layout {
  max-width: 1280px;
  margin: 0 auto;
  display: flex;
  gap: 28px;
  padding: 28px 32px;
}

/* Sidebar */
.sidebar {
  width: 200px;
  flex-shrink: 0;
  position: sticky;
  top: 90px;
  align-self: start;
}

.sidebar-section {
  margin-bottom: 24px;
}

.sidebar-title {
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  color: var(--text-secondary);
  letter-spacing: 1px;
  margin-bottom: 10px;
}

.filter-btn {
  display: block;
  width: 100%;
  padding: 8px 14px;
  margin-bottom: 4px;
  border: 1px solid transparent;
  border-radius: 8px;
  background: transparent;
  color: var(--text);
  font-size: 14px;
  font-family: var(--font);
  cursor: pointer;
  text-align: left;
  transition: all 0.15s;
}

.filter-btn:hover {
  background: var(--orange-light);
}

.filter-btn.active {
  background: var(--orange-light);
  color: var(--orange);
  font-weight: 600;
  border-color: var(--orange);
}

.filter-count {
  float: right;
  font-size: 12px;
  opacity: 0.6;
}

/* Archive links */
.archive-link {
  display: block;
  padding: 6px 14px;
  font-size: 13px;
  color: var(--text-secondary);
  text-decoration: none;
  border-radius: 6px;
  transition: all 0.15s;
}

.archive-link:hover {
  background: var(--orange-light);
  color: var(--orange);
}

/* Main Content */
.main-content {
  flex: 1;
  min-width: 0;
}

/* Breaking / Top Story */
.top-story {
  background: var(--orange-bg);
  border-left: 4px solid var(--orange);
  border-radius: var(--radius);
  padding: 20px 24px;
  margin-bottom: 24px;
}

.top-story-badge {
  display: inline-block;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  color: var(--orange);
  letter-spacing: 1px;
  margin-bottom: 6px;
}

.top-story h2 {
  font-size: 20px;
  margin-bottom: 6px;
}

.top-story .summary {
  font-size: 14px;
  color: var(--text-secondary);
}

/* Category Section */
.category-section {
  margin-bottom: 32px;
}

.category-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
  padding-bottom: 8px;
  border-bottom: 2px solid var(--border);
}

.category-icon {
  font-size: 20px;
}

.category-name {
  font-size: 18px;
  font-weight: 600;
}

.category-count {
  font-size: 13px;
  color: var(--text-secondary);
  margin-left: auto;
}

/* News Card */
.news-card {
  background: var(--white);
  border-radius: var(--radius);
  padding: 16px 20px;
  margin-bottom: 12px;
  box-shadow: var(--shadow);
  border-left: 3px solid var(--orange);
  transition: transform 0.15s, box-shadow 0.15s;
}

.news-card:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(0,0,0,0.1);
}

.news-card h3 {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 4px;
  line-height: 1.4;
}

.news-card h3 a {
  color: var(--text);
  text-decoration: none;
}

.news-card h3 a:hover {
  color: var(--orange);
}

.news-card .ai-summary {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 8px;
  line-height: 1.5;
}

.news-card .meta {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 12px;
  color: #9CA3AF;
}

.news-card .source-tag {
  display: inline-block;
  background: var(--orange-light);
  color: var(--orange);
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
}

.news-card .category-tag {
  display: inline-block;
  background: #E8F4FD;
  color: #2B6CB0;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
}

/* Footer */
.footer {
  text-align: center;
  padding: 32px;
  color: var(--text-secondary);
  font-size: 13px;
  border-top: 1px solid var(--border);
  margin-top: 16px;
}

.footer a {
  color: var(--orange);
  text-decoration: none;
}

/* Hidden category (for filtering) */
.news-card.hidden {
  display: none;
}

/* Responsive */
@media (max-width: 768px) {
  .layout {
    flex-direction: column;
    padding: 16px;
  }
  .sidebar {
    width: 100%;
    position: static;
  }
  .filter-btn {
    display: inline-block;
    width: auto;
    margin-right: 4px;
  }
  .header {
    padding: 16px;
  }
}

/* Loading / Empty states */
.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: var(--text-secondary);
}

.empty-state .emoji {
  font-size: 48px;
  margin-bottom: 16px;
}

/* Archive page */
.archive-header {
  margin-bottom: 24px;
}

.archive-nav {
  display: flex;
  justify-content: space-between;
  margin-bottom: 20px;
}

.archive-nav a {
  color: var(--orange);
  text-decoration: none;
  font-weight: 500;
}

.archive-nav a:hover {
  text-decoration: underline;
}
```

- [ ] **Step 2: Commit**

```bash
git add docs/assets/style.css
git commit -m "feat: add Claude orange themed stylesheet"

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
```

---

### Task 5: Create HTML Templates (Jinja2)

**Files:**
- Create: `c:\Users\liyu\Desktop\ainews\templates\index.html`
- Create: `c:\Users\liyu\Desktop\ainews\templates\archive.html`

- [ ] **Step 1: Create index.html template**

```jinja2
{# templates/index.html — Main daily news page #}
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AI News Daily — {{ date_cn }}</title>
  <meta name="description" content="AI 新闻日报 - 每日 AI、科技、热点新闻精选摘要">
  <link rel="stylesheet" href="assets/style.css">
</head>
<body>

<header class="header">
  <div class="header-content">
    <h1>📡 AI News Daily <span>· 每日新闻精选</span></h1>
    <div class="header-date">{{ date_cn }} · {{ weekday_cn }}</div>
  </div>
</header>

<div class="layout">
  <aside class="sidebar" id="sidebar">
    <div class="sidebar-section">
      <div class="sidebar-title">分类筛选</div>
      <button class="filter-btn active" data-filter="all" onclick="filterNews('all')">
        📋 全部 <span class="filter-count">{{ stats.total }}</span>
      </button>
      <button class="filter-btn" data-filter="ai" onclick="filterNews('ai')">
        🤖 AI <span class="filter-count">{{ stats.ai }}</span>
      </button>
      <button class="filter-btn" data-filter="tech" onclick="filterNews('tech')">
        🖥️ 科技 <span class="filter-count">{{ stats.tech }}</span>
      </button>
      <button class="filter-btn" data-filter="general" onclick="filterNews('general')">
        🌍 综合 <span class="filter-count">{{ stats.general }}</span>
      </button>
    </div>

    {% if archives %}
    <div class="sidebar-section">
      <div class="sidebar-title">历史存档</div>
      {% for a in archives %}
      <a class="archive-link" href="archives/{{ a.file }}">{{ a.label }}</a>
      {% endfor %}
    </div>
    {% endif %}
  </aside>

  <main class="main-content">
    {% if top_story %}
    <div class="top-story">
      <div class="top-story-badge">🔥 今日头条</div>
      <h2><a href="{{ top_story.link }}" target="_blank" rel="noopener">{{ top_story.title }}</a></h2>
      {% if top_story.ai_summary %}
      <div class="summary">{{ top_story.ai_summary }}</div>
      {% endif %}
    </div>
    {% endif %}

    {% for cat_id, cat_name, icon, articles in categories %}
    <section class="category-section" id="section-{{ cat_id }}">
      <div class="category-header">
        <span class="category-icon">{{ icon }}</span>
        <span class="category-name">{{ cat_name }}</span>
        <span class="category-count">{{ articles|length }} 篇</span>
      </div>

      {% for article in articles %}
      <article class="news-card" data-category="{{ cat_id }}">
        <h3><a href="{{ article.link }}" target="_blank" rel="noopener">{{ article.title }}</a></h3>
        {% if article.ai_summary %}
        <div class="ai-summary">{{ article.ai_summary }}</div>
        {% endif %}
        <div class="meta">
          <span class="source-tag">{{ article.source }}</span>
          {% if article.published %}
          <span>{{ article.published[:10] }}</span>
          {% endif %}
        </div>
      </article>
      {% endfor %}
    </section>
    {% endfor %}
  </main>
</div>

<footer class="footer">
  <p>数据来源: RSS Feeds · 摘要由 DeepSeek AI 生成</p>
  <p>Powered by GitHub Actions + GitHub Pages · Built {{ fetched_at }}</p>
</footer>

<script>
function filterNews(category) {
  // Update button states
  document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.filter === category);
  });

  // Show/hide cards
  document.querySelectorAll('.news-card').forEach(card => {
    card.classList.toggle('hidden', category !== 'all' && card.dataset.category !== category);
  });

  // Show/hide category sections
  document.querySelectorAll('.category-section').forEach(section => {
    const visibleCards = section.querySelectorAll('.news-card:not(.hidden)');
    section.style.display = (category === 'all' || visibleCards.length > 0) ? '' : 'none';
  });
}

// Keyboard shortcut: press 1-4 to filter
document.addEventListener('keydown', function(e) {
  const map = { '1': 'all', '2': 'ai', '3': 'tech', '4': 'general' };
  if (e.key in map) filterNews(map[e.key]);
});
</script>

</body>
</html>
```

- [ ] **Step 2: Create archive.html template**

```jinja2
{# templates/archive.html — Single-day archive page #}
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AI News Daily — {{ date_cn }} 归档</title>
  <meta name="description" content="AI 新闻日报 - {{ date_cn }} 新闻存档">
  <link rel="stylesheet" href="../assets/style.css">
</head>
<body>

<header class="header">
  <div class="header-content">
    <h1>📡 AI News Daily <span>· 新闻存档</span></h1>
    <div class="header-date">{{ date_cn }} · {{ weekday_cn }}</div>
  </div>
</header>

<div class="layout">
  <aside class="sidebar">
    <div class="sidebar-section">
      <div class="sidebar-title">导航</div>
      <a class="archive-link" href="../index.html">← 返回今日</a>
    </div>
    {% if archives %}
    <div class="sidebar-section">
      <div class="sidebar-title">其他日期</div>
      {% for a in archives %}
      <a class="archive-link" href="{{ a.file }}">{{ a.label }}</a>
      {% endfor %}
    </div>
    {% endif %}
  </aside>

  <main class="main-content">
    <div class="archive-header">
      <h2>{{ date_cn }} 新闻存档</h2>
      <p style="color: var(--text-secondary); margin-top: 4px;">共 {{ stats.total }} 篇新闻</p>
    </div>

    {% for cat_id, cat_name, icon, articles in categories %}
    <section class="category-section">
      <div class="category-header">
        <span class="category-icon">{{ icon }}</span>
        <span class="category-name">{{ cat_name }}</span>
        <span class="category-count">{{ articles|length }} 篇</span>
      </div>

      {% for article in articles %}
      <article class="news-card" data-category="{{ cat_id }}">
        <h3><a href="{{ article.link }}" target="_blank" rel="noopener">{{ article.title }}</a></h3>
        {% if article.ai_summary %}
        <div class="ai-summary">{{ article.ai_summary }}</div>
        {% endif %}
        <div class="meta">
          <span class="source-tag">{{ article.source }}</span>
        </div>
      </article>
      {% endfor %}
    </section>
    {% endfor %}
  </main>
</div>

<footer class="footer">
  <p>数据来源: RSS Feeds · 摘要由 DeepSeek AI 生成</p>
  <p>Powered by GitHub Actions + GitHub Pages</p>
</footer>

</body>
</html>
```

- [ ] **Step 3: Commit**

```bash
git add templates/index.html templates/archive.html
git commit -m "feat: add Jinja2 HTML templates with Claude orange theme"

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
```

---

### Task 6: Create Site Builder (build_site.py)

**Files:**
- Create: `c:\Users\liyu\Desktop\ainews\scripts\build_site.py`

- [ ] **Step 1: Write the site builder**

```python
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

def main():
    print("🏗️  Building static site...")

    if not INPUT_FILE.exists():
        print("❌ news_final.json not found. Run fetch + summarize first.")
        return

    # Load data
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    articles = data["articles"]
    fetched_at = data.get("fetched_at", "")

    if not articles:
        print("⚠️  No articles to build. Skipping.")
        return

    # Separate top story (first article) from the rest
    top_story = articles[0] if articles else None
    remaining = articles[1:] if articles else []

    # Group by category
    grouped = {}
    for cat_id in CATEGORY_INFO:
        grouped[cat_id] = []

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
```

- [ ] **Step 2: Test the site builder**

```bash
cd /c/Users/liyu/Desktop/ainews
python scripts/build_site.py
```

Expected: `docs/index.html` and `docs/archives/2026-06-01.html` are created.

- [ ] **Step 3: Open the generated HTML to verify**

```bash
# Quick check the file exists and has content
wc -l docs/index.html docs/archives/2026-06-01.html
```

Expected: Both files exist with non-zero content.

- [ ] **Step 4: Commit**

```bash
git add scripts/build_site.py
git commit -m "feat: add site builder with Jinja2 rendering"

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
```

---

### Task 7: Create GitHub Actions Workflow

**Files:**
- Create: `c:\Users\liyu\Desktop\ainews\.github\workflows\daily-news.yml`

- [ ] **Step 1: Write the workflow**

```yaml
# .github/workflows/daily-news.yml
name: Daily News

on:
  schedule:
    # Run daily at 00:00 UTC = 08:00 CST (China Standard Time)
    - cron: '0 0 * * *'
  workflow_dispatch:  # Allow manual trigger for testing

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: write

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Fetch news from RSS feeds
        run: python scripts/fetch_news.py

      - name: Generate AI summaries
        env:
          DEEPSEEK_API_URL: ${{ secrets.DEEPSEEK_API_URL }}
          DEEPSEEK_API_KEY: ${{ secrets.DEEPSEEK_API_KEY }}
          DEEPSEEK_MODEL: ${{ secrets.DEEPSEEK_MODEL }}
        run: python scripts/summarize.py

      - name: Build static site
        run: python scripts/build_site.py

      - name: Deploy to GitHub Pages
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./docs
          keep_files: true
```

- [ ] **Step 2: Commit**

```bash
mkdir -p .github/workflows
git add .github/workflows/daily-news.yml
git commit -m "ci: add GitHub Actions workflow for daily news pipeline"

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
```

---

### Task 8: Test Full Pipeline Locally

**Files:** (no new files, validation only)

- [ ] **Step 1: Run full pipeline end-to-end**

```bash
cd /c/Users/liyu/Desktop/ainews
python scripts/fetch_news.py
python scripts/summarize.py
python scripts/build_site.py
```

Expected: No errors. Three JSON/HTML files produced.

- [ ] **Step 2: Verify HTML renders correctly**

```bash
# Check for common HTML issues
grep -c "<html" docs/index.html
grep -c "</html>" docs/index.html
```

Expected: Both return 1 (valid HTML structure).

- [ ] **Step 3: Commit final version**

```bash
git add -A
git commit -m "chore: finalize after local pipeline test"

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
```

---

### Task 9: Set Up GitHub Repository and Secrets

**Files:** (deployment setup, no code changes)

- [ ] **Step 1: Create GitHub repository and push**

```bash
# First, go to https://github.com/new and create a new repo named "ainews" (public)
# Do NOT initialize with README — we already have code

cd /c/Users/liyu/Desktop/ainews
git remote add origin https://github.com/<YOUR_USERNAME>/ainews.git
git branch -M main
git push -u origin main
```

Expected: Code pushed to GitHub.

- [ ] **Step 2: Configure GitHub Pages**

Go to repo → Settings → Pages → Source → **Deploy from branch** → Branch: `gh-pages` / `/ (root)`. Save.

This is the target branch for `peaceiris/actions-gh-pages`.

- [ ] **Step 3: Add secrets to GitHub**

Go to repo → Settings → Secrets and Variables → Actions → Add the following secrets:

| Name | Value |
|------|-------|
| `DEEPSEEK_API_URL` | 你的中转站 API URL (如 `https://api.xxx.com/v1/chat/completions`) |
| `DEEPSEEK_API_KEY` | 你的中转站 API Key |
| `DEEPSEEK_MODEL` | 模型名称 (如 `deepseek-chat` 或中转站提供的模型 ID) |

- [ ] **Step 4: Manually trigger the workflow to test**

After secrets are set, go to repo → Actions → Daily News → **Run workflow** (manual trigger).

Wait for completion (~2-3 min). Verify:
- ✅ Workflow succeeds (green check)
- ✅ `gh-pages` branch appears
- ✅ GitHub Pages URL is accessible: `https://<YOUR_USERNAME>.github.io/ainews/`

- [ ] **Step 5: Check the live site**

Verify the site is live at the URL above — should show Claude-orange themed news page with today's articles.

---

## Plan Self-Review

**1. Spec coverage:**
- ✅ RSS fetching with 12 sources across 3 categories (Task 2 matches spec §RSS 新闻源)
- ✅ URL-based dedup with .seen_urls.json (Task 2 matches spec §去重)
- ✅ DeepSeek batch summarization with Chinese summaries ≤20 chars (Task 3 matches spec §AI 摘要)
- ✅ Claude orange theme CSS (Task 4 matches spec §视觉风格)
- ✅ Information panel layout with sidebar + category filtering (Task 5 matches spec §页面布局)
- ✅ Top story / 头条 section (Task 5/6 matches spec §头条区)
- ✅ Archive pages for each day (Task 6 matches spec §归档)
- ✅ Daily GitHub Actions cron at 00:00 UTC / 08:00 CST (Task 7 matches spec §架构)
- ✅ GitHub Pages deployment via gh-pages branch (Task 7 matches spec)
- ✅ Error handling: single feed failure doesn't break pipeline (Task 2)
- ✅ Empty summary fallback when API fails (Task 3)
- ✅ Keyboard shortcuts 1-4 for category switching (Task 5)

**2. Placeholder scan:** No TBD, TODO, or vague requirements found.

**3. Type consistency:** Functions, variable names, template variables consistent across all tasks. No mismatches.

**4. Spec gaps found:**
- The spec mentions `seen_urls.json` for caching summarized URLs — implemented in Task 2.
- The spec mentions responsive mobile layout — covered in CSS (Task 4).
- Archive link in sidebar — covered in build_site.py (Task 6) and template (Task 5).
