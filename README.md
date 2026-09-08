# website-image-scraper

[![CI](https://github.com/ScrapeUnblocker/website-image-scraper/actions/workflows/ci.yml/badge.svg)](https://github.com/ScrapeUnblocker/website-image-scraper/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**Extract and download every image from any web page — even images behind
Cloudflare, hCaptcha or hotlink protection.**

It works in two steps, each backed by a real
[ScrapeUnblocker](https://scrapeunblocker.com/?utm_source=github&utm_medium=integration&utm_campaign=example-repos)
endpoint:

1. **Discover** — render the page with `getPageSource` and pull out every image
   URL (`src`, `srcset`, and common lazy-load attributes), resolving relative
   URLs and de-duplicating.
2. **Download** — fetch each image with `getImage`, which loads it through a real
   browser and returns clean **PNG** bytes. That gets you images that a plain
   `GET` would be blocked from downloading.

> Powered by [ScrapeUnblocker](https://scrapeunblocker.com/?utm_source=github&utm_medium=integration&utm_campaign=example-repos).

## Features

- 🖼️ Grabs `<img>`, `<source>` / `srcset`, and lazy-loaded (`data-src`, `data-original`, …) images.
- 🔓 Downloads through a real browser, so anti-bot / hotlink-protected images still come through.
- 🧾 Writes a **JSON or CSV manifest** (source page, image URL, saved file, byte size, status).
- 🌍 Optional country geo-targeting.
- 🔁 Automatic retries with back-off for transient failures.
- 🧰 Use it as a **CLI** or a **Python library**.
- ✅ Offline unit tests (SDK mocked — no API credit spent in CI).

## Install

```bash
pip install .
# or, for development:
pip install -e ".[dev]"
```

Then set your API key (get one at
[scrapeunblocker.com](https://scrapeunblocker.com/?utm_source=github&utm_medium=integration&utm_campaign=example-repos)):

```bash
cp .env.example .env      # then edit it
export SCRAPEUNBLOCKER_KEY=your_key_here
```

The [official Python SDK](https://docs.scrapeunblocker.com/?utm_source=github&utm_medium=integration&utm_campaign=example-repos)
reads the key from `SCRAPEUNBLOCKER_KEY`.

## CLI usage

```bash
# Download up to 5 images and write a manifest
su-image-scraper https://books.toscrape.com/ --limit 5 --manifest images/manifest.json -v

# Just list the image URLs, download nothing
su-image-scraper https://books.toscrape.com/ --urls-only

# Save into a specific folder, export a CSV, geo-target the request
su-image-scraper https://example.com/ -o out --csv out/manifest.csv --country us
```

```
usage: su-image-scraper [-h] [-o OUT_DIR] [--limit LIMIT] [--country XX]
                        [--manifest PATH] [--csv PATH] [--urls-only]
                        [--include-data-uris] [--retries RETRIES] [-v]
                        url
```

## Library usage

```python
from image_scraper import ImageScraper, write_manifest

scraper = ImageScraper()  # reads SCRAPEUNBLOCKER_KEY

# 1) discover image URLs on a page
urls = scraper.discover("https://books.toscrape.com/")

# 2) download them (returns one record per image)
records = scraper.scrape("https://books.toscrape.com/", out_dir="images", limit=5)
write_manifest(records, "images/manifest.json")

# ...or fetch a single protected image directly as PNG bytes
png = scraper.fetch_image(
    "https://books.toscrape.com/media/cache/2c/da/2cdad67c44b002e7ead0cc35693c0e8b.jpg"
)
with open("cover.png", "wb") as f:
    f.write(png)
```

## Example output

```json
{
  "page": "https://books.toscrape.com/",
  "discovered": 5,
  "downloaded": 5,
  "failed": 0,
  "out_dir": "images"
}
```

`images/manifest.json`:

```json
[
  {
    "page_url": "https://books.toscrape.com/",
    "image_url": "https://books.toscrape.com/media/cache/2c/da/2cdad67c44b002e7ead0cc35693c0e8b.jpg",
    "file": "images/2cdad67c44b002e7ead0cc35693c0e8b.png",
    "bytes": 22683,
    "ok": true,
    "error": null
  }
]
```

More runnable scripts are in [`examples/`](examples/).

## Project layout

```
src/image_scraper/
  __init__.py        package exports + __version__
  scraper.py         discovery + download logic (ImageScraper, discover_image_urls, manifest writers)
  cli.py             argparse CLI (su-image-scraper)
examples/            runnable scripts (scrape a page, list URLs, single image)
tests/               offline unit tests (SDK mocked)
```

## Development

```bash
make install   # editable install + pre-commit hooks
make lint      # ruff check
make format    # ruff format
make test      # pytest (offline, no API key needed)
make run URL=https://books.toscrape.com/
```

## How it maps to the API

| Step | SDK call | Endpoint |
| ---- | -------- | -------- |
| Discover image URLs | `client.get_page_source(url)` | [`getPageSource`](https://docs.scrapeunblocker.com/?utm_source=github&utm_medium=integration&utm_campaign=example-repos) |
| Download an image | `client.get_image(image_url)` | [`getImage`](https://docs.scrapeunblocker.com/?utm_source=github&utm_medium=integration&utm_campaign=example-repos) |

## Links

- 🌐 Website: https://scrapeunblocker.com/?utm_source=github&utm_medium=integration&utm_campaign=example-repos
- 📚 Docs: https://docs.scrapeunblocker.com/?utm_source=github&utm_medium=integration&utm_campaign=example-repos

## License

[MIT](LICENSE) © 2026 ScrapeUnblocker
