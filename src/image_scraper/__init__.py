"""website-image-scraper — extract and download every image from any web page.

Discovers ``<img>`` / ``srcset`` / lazy-loaded image URLs from the fully rendered
page (via ScrapeUnblocker ``getPageSource``) and fetches each one through a real
browser as a clean PNG (via ScrapeUnblocker ``getImage``), so images behind
Cloudflare, hCaptcha or hotlink protection still come through.

Powered by ScrapeUnblocker: https://scrapeunblocker.com
"""

from __future__ import annotations

from .scraper import (
    ImageRecord,
    ImageScraper,
    discover_image_urls,
    write_csv,
    write_manifest,
)

__all__ = [
    "ImageScraper",
    "ImageRecord",
    "discover_image_urls",
    "write_manifest",
    "write_csv",
]
__version__ = "0.1.0"
