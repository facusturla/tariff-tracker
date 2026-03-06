"""
Trump 2.0 Tariff Tracker — Scraper
===================================
Fetches the latest tariff data from the Trade Compliance Resource Hub (Reed Smith)
and saves it to data/tariffs.json for the GitHub Pages dashboard.

Run manually: python scraper/scrape.py
Run automatically: via GitHub Actions every day at 08:00 UTC
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ── Configuration ────────────────────────────────────────────────────────────

BASE_URL = "https://www.tradecomplianceresourcehub.com"
TRACKER_SLUG = "trump-2-0-tariff-tracker"
OUTPUT_FILE = Path(__file__).parent.parent / "data" / "tariffs.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# ── Utilities ─────────────────────────────────────────────────────────────────

def find_latest_tracker_url() -> str:
    """Search the site for the latest tariff tracker article URL."""
    search_url = f"{BASE_URL}/?s={TRACKER_SLUG}"
    try:
        r = requests.get(search_url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
        # Find first article link matching our slug
        for a in soup.select("a[href]"):
            href = a["href"]
            if TRACKER_SLUG in href and BASE_URL in href:
                return href
    except Exception as e:
        print(f"[WARN] Search failed: {e}. Falling back to known URL.")

    # Fallback: try known recent patterns
    year = datetime.now().year
    month = datetime.now().month
    for y in [year, year - 1]:
        for m in range(12, 0, -1):
            url = f"{BASE_URL}/{y}/{m:02d}/"
            try:
                r = requests.get(url, headers=HEADERS, timeout=10)
                soup = BeautifulSoup(r.text, "lxml")
                for a in soup.select("a[href]"):
                    if TRACKER_SLUG in a.get("href", ""):
                        return a["href"]
            except Exception:
                continue

    # Last resort hardcoded URL
    return f"{BASE_URL}/2026/03/05/trump-2-0-tariff-tracker/"


def clean(text: str) -> str:
    """Normalise whitespace and strip link artifacts."""
    text = re.sub(r"Details\s*▸", "", text)
    text = re.sub(r"Trade Deal\s*", "", text)
    text = re.sub(r"Sec\. 232 Invest\.\s*", "(Sec. 232) ", text)
    text = re.sub(r"Tariff CMs\s*▸", "", text)
    text = re.sub(r"Sec\. 301 Invest\.\s*", "(Sec. 301) ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_rate(cell_text: str) -> tuple[str, float | None]:
    """Return (display_rate, numeric_rate) from a rate cell."""
    text = clean(cell_text)
    if not text or text.upper() == "TBD":
        return "TBD", None
    # Try to extract highest numeric value
    nums = re.findall(r"(\d+(?:\.\d+)?)\s*%", text)
    num = max(float(n) for n in nums) if nums else None
    return text, num


def extract_status(cell_text: str) -> str:
    txt = cell_text.lower()
    if "delayed" in txt:
        return "delayed"
    if "implemented" in txt or "effective" in txt:
        return "implemented"
    if "threatened" in txt:
        return "threatened"
    return "tbd"


def parse_tables(soup: BeautifulSoup) -> tuple[list, list]:
    """Return (country_rows, product_rows)."""
    tables = soup.find_all("table")
    if len(tables) < 2:
        raise ValueError(f"Expected ≥2 tables, found {len(tables)}")

    country_rows = []
    product_rows = []

    def rows_from(table) -> list[list[str]]:
        result = []
        for tr in table.find_all("tr"):
            cells = [td.get_text(" ", strip=True) for td in tr.find_all(["td", "th"])]
            if cells:
                result.append(cells)
        return result

    # ── Country table (first table) ──────────────────────────────────────────
    raw_country = rows_from(tables[0])
    header_skipped = False
    current_country = None
    for row in raw_country:
        if not header_skipped:
            header_skipped = True
            continue
        if len(row) == 0:
            continue

        # Detect separator / footer rows
        first = clean(row[0])
        if not first or "Reciprocal" in first or "Invalidated" in first:
            continue

        # If row has ≥4 cols: Country | Status | Rate | Scope | Countermeasures
        if len(row) >= 4:
            country_name = clean(row[0])
            # Strip metadata tags from country name
            country_name = re.sub(r"\s*(Trade Deal|Tariff CMs ▸|Sec\. 301 Invest\.)\s*", "", country_name).strip()
            if country_name:
                current_country = country_name
            status = extract_status(row[1] if len(row) > 1 else "")
            display_rate, num_rate = extract_rate(row[2] if len(row) > 2 else "")
            scope = clean(row[3]) if len(row) > 3 else ""
            countermeasures = clean(row[4]) if len(row) > 4 else "—"
            country_rows.append({
                "country": current_country or first,
                "status": status,
                "rate": display_rate,
                "rateNum": num_rate,
                "scope": scope,
                "countermeasures": countermeasures or "—",
            })
        elif len(row) >= 2 and current_country:
            # Sub-row (additional measure for same country)
            status = extract_status(row[0])
            display_rate, num_rate = extract_rate(row[1] if len(row) > 1 else "")
            scope = clean(row[2]) if len(row) > 2 else ""
            country_rows.append({
                "country": current_country,
                "status": status,
                "rate": display_rate,
                "rateNum": num_rate,
                "scope": scope,
                "countermeasures": "—",
            })

    # ── Product table (second table) ─────────────────────────────────────────
    raw_product = rows_from(tables[1])
    header_skipped = False
    current_product = None
    for row in raw_product:
        if not header_skipped:
            header_skipped = True
            continue
        if not row:
            continue
        first = clean(row[0])
        if not first:
            continue

        if len(row) >= 3:
            product_name = re.sub(r"\s*\(Sec\. 232\)\s*", "", first).strip()
            if product_name:
                current_product = product_name
            status = extract_status(row[1] if len(row) > 1 else "")
            display_rate, num_rate = extract_rate(row[2] if len(row) > 2 else "")
            scope = clean(row[3]) if len(row) > 3 else ""
            notes = clean(row[4]) if len(row) > 4 else ""
            product_rows.append({
                "product": current_product or first,
                "status": status,
                "rate": display_rate,
                "rateNum": num_rate,
                "scope": scope,
                "notes": notes,
            })
        elif len(row) >= 2 and current_product:
            status = extract_status(row[0])
            display_rate, num_rate = extract_rate(row[1] if len(row) > 1 else "")
            scope = clean(row[2]) if len(row) > 2 else ""
            product_rows.append({
                "product": current_product,
                "status": status,
                "rate": display_rate,
                "rateNum": num_rate,
                "scope": scope,
                "notes": "",
            })

    return country_rows, product_rows


def extract_context(soup: BeautifulSoup) -> list[dict]:
    """
    Extract context/explanatory sections that appear below the tables.
    Returns a list of {heading, items} dicts.
    """
    sections = []
    # Find the last table in the article, then grab everything after it
    tables = soup.find_all("table")
    if not tables:
        return sections

    last_table = tables[-1]
    current_heading = None
    current_items = []

    # Walk siblings after the last table
    for el in last_table.find_all_next():
        tag = el.name
        if not tag:
            continue
        # Stop at footer / nav / aside
        if tag in ("footer", "nav", "aside"):
            break
        # Headings start a new section
        if tag in ("h2", "h3", "h4"):
            if current_heading and current_items:
                sections.append({"heading": current_heading, "items": current_items})
            current_heading = el.get_text(" ", strip=True)
            current_items = []
        elif tag in ("p", "li"):
            text = el.get_text(" ", strip=True)
            if text and len(text) > 20:  # skip trivial lines
                current_items.append(text)

    # Flush last section
    if current_heading and current_items:
        sections.append({"heading": current_heading, "items": current_items})

    # If no headings found, fallback: grab all paragraphs after last table
    if not sections:
        items = []
        for el in last_table.find_all_next(["p", "li"]):
            text = el.get_text(" ", strip=True)
            if text and len(text) > 20:
                items.append(text)
        if items:
            sections.append({"heading": "Notes & Context", "items": items})

    return sections


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("[1/4] Finding latest tracker URL...")
    url = find_latest_tracker_url()
    print(f"      → {url}")

    print("[2/4] Fetching page...")
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")

    # Extract article date from URL or page
    date_match = re.search(r"/(\d{4}/\d{2}/\d{2})/", url)
    article_date = date_match.group(1).replace("/", "-") if date_match else datetime.now(timezone.utc).strftime("%Y-%m-%d")

    print("[3/5] Parsing tables...")
    country_rows, product_rows = parse_tables(soup)
    print(f"      → {len(country_rows)} country rows, {len(product_rows)} product rows")

    print("[4/5] Extracting context sections...")
    context_sections = extract_context(soup)
    print(f"      → {len(context_sections)} context sections")

    print("[5/5] Writing data/tariffs.json...")
    output = {
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "article_date": article_date,
        "source_url": url,
        "countries": country_rows,
        "products": product_rows,
        "context": context_sections,
    }
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"      → Saved {len(country_rows) + len(product_rows)} records + {len(context_sections)} context sections to {OUTPUT_FILE}")
    print("Done ✓")


if __name__ == "__main__":
    main()
