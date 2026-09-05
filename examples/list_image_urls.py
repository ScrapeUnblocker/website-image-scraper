"""Just list the image URLs on a page - no downloads, no files written.

Usage:
    export SCRAPEUNBLOCKER_KEY=your_key_here
    python examples/list_image_urls.py https://books.toscrape.com/
"""

from __future__ import annotations

import sys

from image_scraper import ImageScraper


def main() -> None:
    page = sys.argv[1] if len(sys.argv) > 1 else "https://books.toscrape.com/"
    urls = ImageScraper().discover(page)
    print(f"{len(urls)} image(s) on {page}:")
    for url in urls:
        print(f"  {url}")


if __name__ == "__main__":
    main()
