# AI News Daily — 设计文档

## 概述

自动化的 AI 新闻日报系统，每天定时从全球多个 RSS 源抓取 AI、科技、综合热点新闻，使用 DeepSeek API 生成中文摘要，以 Claude 风格的信息面板页面展示在 GitHub Pages 上。

## 架构

```
GitHub Actions (08:00 CST)
    │
    ├─ fetch_news.py  ──→  RSS 抓取 + 去重 → news_raw.json
    ├─ summarize.py   ──→  DeepSeek 摘要  → news_final.json
    └─ build_site.py  ──→  Jinja2 渲染    → docs/ (GitHub Pages)
```

- **触发方式**: GitHub Actions cron 定时，每天北京时间 08:00
- **产物托管**: GitHub Pages，从 `docs/` 目录提供
- **全部免费**: GitHub Actions 免费额度 + GitHub Pages 免费托管

## RSS 新闻源

约 20-25 个源，分四大类：

| 分类 | 语言 | 示例源 |
|------|------|--------|
| 🤖 AI 新闻 | 中/英 | Hacker News AI, TechCrunch AI, 机器之心, 量子位, ArXiv |
| 🖥️ 科技 | 中/英 | 36氪, InfoQ, Solidot |
| 🌍 综合热点 | 中/英 | 澎湃新闻, BBC, Reuters (top stories) |
| 🔥 头条精选 | — | 从当日所有新闻中自动选出热度最高的 1-2 条 |

去重策略：基于 URL hash 去重，相同文章跨源只保留一条。

## AI 摘要

- **模型**: DeepSeek（通过中转站 API）
- **Prompt**: 用 20 字以内中文总结核心内容
- **批量**: 每次 5 条并发，失败自动重试 1 次
- **缓存**: 已摘要的 URL 存入 `seen_urls.json`，避免重复

## 页面布局

### 整体结构

```
┌──────────────────────────────────────────────────┐
│  📡 AI News Daily       2026年6月1日 星期一      │  ← 暖橙顶栏
├──────────┬───────────────────────────────────────┤
│          │  🔥 头条区（1-2条精选）                │
│  左侧栏   │                                        │
│  分类筛选  │  🤖 AI  (按时间倒序卡片排列)          │
│  日期导航  │  🖥️ 科技                              │
│          │  🌍 综合热点                            │
│          │                                        │
│          │  📦 历史存档链接                        │
├──────────┴───────────────────────────────────────┤
│  Footer: 数据来源 | Powered by RSS + DeepSeek     │
└──────────────────────────────────────────────────┘
```

### 视觉风格（Claude 风格）

| 元素 | 设计 |
|------|------|
| **主色调** | 暖橙 `#E05A1F`、浅橙 `#FDE8D8`、暖白 `#FFF8F0` |
| **顶栏** | 暖橙渐变背景，白色柔和字体 |
| **卡片** | 白色底、圆角 12px、box-shadow 轻微阴影、左边框暖橙 3px 实线点缀 |
| **头条区** | 浅橙色背景 `#FFF3E6` 高亮，醒目的标题+摘要 |
| **分类标签** | 浅橙背景 + 深橙文字、圆角 pill 形状 |
| **字体** | 系统无衬线 (`-apple-system`, `Segoe UI`, sans-serif) |
| **整体** | 大量留白、呼吸感、极简温暖干净 |

### 交互

- **分类筛选**: 点击左侧分类标签，仅显示该分类新闻（纯 CSS/JS 实现）
- **日期导航**: 左侧栏显示最近 7 天存档链接
- **响应式**: 手机端左侧栏折叠为顶部下拉菜单

### 页面类型

1. **首页 `index.html`** — 当日新闻 + 左侧分类筛选 + 历史存档链接
2. **归档页 `archives/YYYY-MM-DD.html`** — 历史某一天的完整新闻

## 项目结构

```
ainews/
├── .github/workflows/daily-news.yml    # GitHub Actions 配置
├── scripts/
│   ├── fetch_news.py                   # RSS 抓取 + 去重
│   ├── summarize.py                    # DeepSeek API 摘要
│   └── build_site.py                   # Jinja2 生成 HTML
├── templates/
│   ├── index.html                      # 首页模板
│   └── archive.html                    # 归档页模板
├── config/
│   └── sources.yml                     # RSS 源配置
├── docs/                               # GitHub Pages 根目录
│   ├── index.html
│   ├── assets/
│   │   └── style.css
│   └── archives/
├── requirements.txt                    # Python 依赖
└── .gitignore
```

## 数据流

```
sources.yml
    │
    ▼
fetch_news.py ──→ 每个 RSS 源 HTTP GET
    │             解析 feed (feedparser)
    │             去重 (URL hash)
    │             按时间排序
    ▼
news_raw.json
    │
    ▼
summarize.py ──→ 调用 DeepSeek API (5条/批)
    │             中文摘要 ≤20 字
    ▼
news_final.json
    │
    ▼
build_site.py ──→ Jinja2 渲染 index.html
                    渲染 archive.html
    │             复制 assets
    ▼
docs/ 目录 ───→ GitHub Pages 部署
```

## 错误处理

- 单个 RSS 源超时/失败 → 跳过，不影响其他源
- DeepSeek API 调用失败 → 重试 1 次，仍失败则留空摘要
- 构建步骤失败 → GitHub Actions 发送失败通知
- 没有新新闻 → 跳过当天部署，保留上次页面

## 后续可扩展

- 支持多语言摘要
- 增加新闻搜索功能
- 邮件/Telegram 推送精选
- 月报/周报聚合页
