# Trump 2.0 Tariff Tracker focused on Argentina

Interactive dashboard tracking U.S. tariff policy under the Trump administration — country-specific and product-specific measures, with real-time status (implemented, threatened, or delayed).

🔗 **Live site:** https://facusturla.github.io/tariff-tracker

---

## What's tracked

- **Country-specific tariffs** — measures targeting Canada, China, the EU, Russia, and others
- **Product-specific tariffs** — steel, aluminum, cars, semiconductors, pharmaceuticals, and more
- Current status of each measure (implemented / threatened / delayed)
- Argentina-specific impact analysis

Data source: [Trade Compliance Resource Hub — Reed Smith](https://www.tradecomplianceresourcehub.com)

> **Copyright notice:** All tariff data is sourced from the *Trade Compliance Resource Hub*, published by [Reed Smith LLP](https://www.reedsmith.com). Content is the intellectual property of Reed Smith LLP and its authors. This dashboard reproduces data for informational and non-commercial research purposes only. For the original and authoritative text, refer to the source linked above.

> **Note:** The U.S. Supreme Court ruled that IEEPA does not authorize the President to impose tariffs. Several measures may be subject to legal challenge.

---

## Auto-updates

A GitHub Action scrapes the Reed Smith tracker every day at 08:00 UTC and updates `data/tariffs.json` automatically if anything changed. No manual intervention needed.

---

## Local setup

```bash
pip install requests beautifulsoup4 lxml
python scraper/scrape.py
```

Then open `index.html` in your browser.

---

*Maintained by [PromArgentina](https://argentina.ar/es/quienes-somos) — Agencia Argentina de Promoción de Inversiones y Comercio Internacional*
