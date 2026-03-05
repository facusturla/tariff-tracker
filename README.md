# Trump 2.0 Tariff Tracker 🌎

**By [PromArgentina](https://argentina.ar)** — Agencia Argentina de Promoción de Inversiones y Comercio Internacional

Live dashboard: **https://facusturla.github.io/tariff-tracker**

## What this is

An interactive dashboard tracking Trump 2.0 tariff policies, automatically updated daily from the [Trade Compliance Resource Hub (Reed Smith)](https://www.tradecomplianceresourcehub.com).

Features:
- 🗺️ World map with tariff markers by country
- 📋 Filterable tables (by country and by product)
- 🇦🇷 Argentina-specific impact analysis
- 📊 KPI cards (max tariff, implemented vs threatened, etc.)
- ⚙️ Auto-updated daily via GitHub Actions

## How it works

```
scraper/scrape.py          Fetches & parses the Reed Smith tracker page
       ↓
data/tariffs.json          Stores structured tariff data
       ↓
index.html                 Reads tariffs.json and renders the dashboard
```

## Auto-update schedule

GitHub Actions runs `scraper/scrape.py` every day at **08:00 UTC** (05:00 Buenos Aires).
If the data changed, it auto-commits and updates the live site.

You can also trigger a manual update from the **Actions** tab in GitHub.

## Local development

```bash
pip install requests beautifulsoup4 lxml
python scraper/scrape.py
# then open index.html in your browser
```
