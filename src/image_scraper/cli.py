"""Command-line interface for website-image-scraper."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections.abc import Sequence

from .scraper import ImageScraper, write_csv, write_manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="su-image-scraper",
        description=(
            "Extract and download every image from a web page via ScrapeUnblocker "
            "(getPageSource + getImage)."
        ),
    )
    parser.add_argument("url", help="page URL to scrape images from")
    parser.add_argument(
        "-o",
        "--out-dir",
        default="images",
        help="directory to save images into (default: images)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="download at most N images",
    )
    parser.add_argument(
        "--country",
        default=None,
        metavar="XX",
        help="ISO 3166-1 alpha-2 country code for proxy geo-targeting",
    )
    parser.add_argument(
        "--manifest",
        default=None,
        metavar="PATH",
        help="write a JSON manifest of the run to PATH",
    )
    parser.add_argument(
        "--csv",
        default=None,
        metavar="PATH",
        help="write a CSV manifest of the run to PATH",
    )
    parser.add_argument(
        "--urls-only",
        action="store_true",
        help="only print discovered image URLs; do not download anything",
    )
    parser.add_argument(
        "--include-data-uris",
        action="store_true",
        help="include inline data: URIs (skipped by default)",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=3,
        help="attempts per image before giving up (default: 3)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="log progress to stderr",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(message)s",
    )

    scraper = ImageScraper(retries=args.retries, proxy_country=args.country)

    if args.urls_only:
        for url in scraper.discover(args.url, include_data_uris=args.include_data_uris):
            print(url)
        return 0

    records = scraper.scrape(
        args.url,
        args.out_dir,
        limit=args.limit,
        include_data_uris=args.include_data_uris,
    )
    downloaded = sum(1 for r in records if r.ok)

    if args.manifest:
        write_manifest(records, args.manifest)
    if args.csv:
        write_csv(records, args.csv)

    summary = {
        "page": args.url,
        "discovered": len(records),
        "downloaded": downloaded,
        "failed": len(records) - downloaded,
        "out_dir": args.out_dir,
    }
    print(json.dumps(summary, indent=2))

    # Success unless we found images but downloaded none of them.
    if records and downloaded == 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
