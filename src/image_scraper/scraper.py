"""Core image discovery + download logic.

Two independent steps, each backed by a real ScrapeUnblocker endpoint:

1. :meth:`ImageScraper.discover` renders the page with ``getPageSource`` and pulls
   every image URL out of it (``src``, ``srcset``, common lazy-load attributes),
   resolving relative URLs and de-duplicating.
2. :meth:`ImageScraper.fetch_image` downloads a single image with ``getImage``,
   which loads it through a real browser and returns PNG bytes — handy for hosts
   that block plain GET requests.
"""

from __future__ import annotations

import csv
import json
import logging
import os
import re
import time
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

logger = logging.getLogger("image_scraper")

_DATA_URI = re.compile(r"^data:", re.IGNORECASE)
_IMG_EXT = re.compile(r"\.(?:jpe?g|png|gif|webp|bmp|svg|avif|tiff?)$", re.IGNORECASE)
# Attributes that commonly hold a real or lazy-loaded image URL.
_URL_ATTRS = ("src", "data-src", "data-original", "data-lazy-src", "data-lazy")
_SRCSET_ATTRS = ("srcset", "data-srcset")


class _ImgCollector(HTMLParser):
    """Collect candidate image URLs from ``<img>`` and ``<source>`` tags."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.urls: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag not in ("img", "source"):
            return
        a = {k: (v or "") for k, v in attrs}
        for key in _URL_ATTRS:
            value = a.get(key, "").strip()
            if value:
                self.urls.append(value)
        for key in _SRCSET_ATTRS:
            srcset = a.get(key, "").strip()
            if srcset:
                # "a.jpg 1x, b.jpg 2x" -> ["a.jpg", "b.jpg"]
                for part in srcset.split(","):
                    candidate = part.strip().split(" ", 1)[0].strip()
                    if candidate:
                        self.urls.append(candidate)


def discover_image_urls(
    html: str,
    base_url: str,
    include_data_uris: bool = False,
) -> list[str]:
    """Return de-duplicated, absolute image URLs found in ``html``.

    Relative URLs are resolved against ``base_url``. ``data:`` URIs are skipped
    unless ``include_data_uris`` is set. Order of first appearance is preserved.
    """
    parser = _ImgCollector()
    parser.feed(html)

    seen: set[str] = set()
    out: list[str] = []
    for raw in parser.urls:
        if _DATA_URI.match(raw):
            if not include_data_uris:
                continue
            resolved = raw
        else:
            resolved = urljoin(base_url, raw).split("#", 1)[0]
        if resolved and resolved not in seen:
            seen.add(resolved)
            out.append(resolved)
    return out


def _filename_for(image_url: str, index: int, used: set[str]) -> str:
    """Derive a safe, unique ``*.png`` filename for an image URL.

    ``getImage`` always returns PNG, so we normalise the extension to ``.png``.
    """
    if _DATA_URI.match(image_url):
        stem = f"image_{index}"
    else:
        base = os.path.basename(unquote(urlparse(image_url).path))
        base = _IMG_EXT.sub("", base)
        stem = re.sub(r"[^A-Za-z0-9._-]", "_", base).strip("._") or f"image_{index}"

    name = f"{stem}.png"
    counter = 1
    while name in used:
        name = f"{stem}_{counter}.png"
        counter += 1
    used.add(name)
    return name


@dataclass
class ImageRecord:
    """One row of the run manifest."""

    page_url: str
    image_url: str
    file: str | None
    bytes: int
    ok: bool
    error: str | None = None


class ImageScraper:
    """Discover and download images from a page via ScrapeUnblocker.

    Parameters
    ----------
    client:
        A ``scrapeunblocker.Client``-like object. If omitted, a real
        ``scrapeunblocker.Client()`` is created (it reads the
        ``SCRAPEUNBLOCKER_KEY`` environment variable).
    retries:
        Attempts per image before giving up (``getImage`` can transiently 403/408).
    backoff:
        Base for exponential back-off between attempts (seconds).
    proxy_country:
        Optional ISO 3166-1 alpha-2 country code for geo-targeting.
    sleep:
        Injectable sleep function (overridden in tests).
    """

    def __init__(
        self,
        client: object | None = None,
        *,
        retries: int = 3,
        backoff: float = 1.5,
        proxy_country: str | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if client is None:
            from scrapeunblocker import Client  # imported lazily so tests need no key

            client = Client()
        self.client = client
        self.retries = max(1, retries)
        self.backoff = backoff
        self.proxy_country = proxy_country
        self._sleep = sleep

    def _get_page_source(self, page_url: str) -> str:
        if self.proxy_country:
            return self.client.get_page_source(page_url, proxy_country=self.proxy_country)
        return self.client.get_page_source(page_url)

    def discover(self, page_url: str, include_data_uris: bool = False) -> list[str]:
        """Render ``page_url`` and return the image URLs found on it."""
        html = self._get_page_source(page_url)
        urls = discover_image_urls(html, page_url, include_data_uris=include_data_uris)
        logger.info("discovered %d image(s) on %s", len(urls), page_url)
        return urls

    def fetch_image(self, image_url: str) -> bytes:
        """Download a single image as PNG bytes, retrying transient failures."""
        last_error: Exception | None = None
        for attempt in range(1, self.retries + 1):
            try:
                data = self.client.get_image(image_url)
                if not data:
                    raise ValueError("empty image response")
                return bytes(data)
            except Exception as exc:  # noqa: BLE001 - surface the last error after retries
                last_error = exc
                logger.warning(
                    "getImage failed (%d/%d) for %s: %s",
                    attempt,
                    self.retries,
                    image_url,
                    exc,
                )
                if attempt < self.retries:
                    self._sleep(self.backoff**attempt)
        assert last_error is not None
        raise last_error

    def scrape(
        self,
        page_url: str,
        out_dir: str | os.PathLike[str] = "images",
        *,
        limit: int | None = None,
        include_data_uris: bool = False,
    ) -> list[ImageRecord]:
        """Discover images on ``page_url`` and download them into ``out_dir``.

        Returns one :class:`ImageRecord` per discovered image (whether or not the
        download succeeded), so callers can build a manifest.
        """
        urls = self.discover(page_url, include_data_uris=include_data_uris)
        if limit is not None:
            urls = urls[:limit]

        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)

        records: list[ImageRecord] = []
        used: set[str] = set()
        for index, image_url in enumerate(urls):
            dest = out / _filename_for(image_url, index, used)
            try:
                data = self.fetch_image(image_url)
                dest.write_bytes(data)
                records.append(ImageRecord(page_url, image_url, str(dest), len(data), True))
                logger.info("saved %s (%d bytes)", dest, len(data))
            except Exception as exc:  # noqa: BLE001 - record the failure, keep going
                records.append(ImageRecord(page_url, image_url, None, 0, False, str(exc)))
                logger.error("failed %s: %s", image_url, exc)
        return records


def write_manifest(records: Iterable[ImageRecord], path: str | os.PathLike[str]) -> None:
    """Write records as a JSON array."""
    payload = [asdict(r) for r in records]
    Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_csv(records: Iterable[ImageRecord], path: str | os.PathLike[str]) -> None:
    """Write records as CSV."""
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["page_url", "image_url", "file", "bytes", "ok", "error"])
        for r in records:
            writer.writerow([r.page_url, r.image_url, r.file or "", r.bytes, r.ok, r.error or ""])
