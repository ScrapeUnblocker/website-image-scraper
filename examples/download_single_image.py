"""Fetch one image through a real browser and save it as PNG.

Handy when a specific image is behind Cloudflare / hotlink protection and a plain
GET returns 403. ``getImage`` always returns PNG bytes regardless of source format.

Usage:
    export SCRAPEUNBLOCKER_KEY=your_key_here
    python examples/download_single_image.py "<image_url>" out.png
"""

from __future__ import annotations

import sys

from image_scraper import ImageScraper


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: download_single_image.py <image_url> [out.png]")
    image_url = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else "out.png"

    data = ImageScraper().fetch_image(image_url)
    with open(out, "wb") as fh:
        fh.write(data)
    print(f"saved {len(data)} bytes to {out}")


if __name__ == "__main__":
    main()
