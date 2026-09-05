import json

from image_scraper import cli
from image_scraper.scraper import ImageRecord


def test_parser_defaults():
    args = cli.build_parser().parse_args(["https://example.com"])
    assert args.url == "https://example.com"
    assert args.out_dir == "images"
    assert args.retries == 3
    assert args.limit is None
    assert not args.urls_only


def test_parser_flags():
    args = cli.build_parser().parse_args(
        ["https://example.com", "-o", "out", "--limit", "5", "--country", "us", "--urls-only"]
    )
    assert args.out_dir == "out"
    assert args.limit == 5
    assert args.country == "us"
    assert args.urls_only is True


class FakeScraper:
    def __init__(self, *a, **k):
        self.kwargs = k

    def discover(self, url, include_data_uris=False):
        return ["https://x.com/a.png", "https://x.com/b.png"]

    def scrape(self, url, out_dir, limit=None, include_data_uris=False):
        return [
            ImageRecord(url, "https://x.com/a.png", f"{out_dir}/a.png", 10, True),
            ImageRecord(url, "https://x.com/b.png", None, 0, False, "boom"),
        ]


def test_main_urls_only(monkeypatch, capsys):
    monkeypatch.setattr(cli, "ImageScraper", FakeScraper)
    rc = cli.main(["https://example.com", "--urls-only"])
    assert rc == 0
    out = capsys.readouterr().out.strip().splitlines()
    assert out == ["https://x.com/a.png", "https://x.com/b.png"]


def test_main_scrape_summary_and_manifest(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(cli, "ImageScraper", FakeScraper)
    manifest = tmp_path / "m.json"
    rc = cli.main(
        ["https://example.com", "-o", str(tmp_path / "imgs"), "--manifest", str(manifest)]
    )
    assert rc == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["discovered"] == 2
    assert summary["downloaded"] == 1
    assert summary["failed"] == 1
    assert manifest.exists()
    assert json.loads(manifest.read_text())[0]["ok"] is True
