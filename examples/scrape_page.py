"""Download every image from a page and write a JSON manifest.

Usage:
    export SCRAPEUNBLOCKER_KEY=your_key_here
    python examples/scrape_page.py https://books.toscrape.com/
"""

from __future__ import annotations

import sys

from image_scraper import ImageScraper, write_manifest


def main() -> None:
    page = sys.argv[1] if len(sys.argv) > 1 else "https://books.toscrape.com/"
    scraper = ImageScraper()
    records = scraper.scrape(page, out_dir="images", limit=5)
    write_manifest(records, "images/manifest.json")

    ok = sum(1 for r in records if r.ok)
    print(f"{page}: discovered {len(records)}, downloaded {ok}")
    for r in records:
        status = f"{r.bytes} bytes -> {r.file}" if r.ok else f"FAILED ({r.error})"
        print(f"  {r.image_url}  {status}")


if __name__ == "__main__":
    main()
