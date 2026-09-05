import json

import pytest

from image_scraper.scraper import ImageScraper, write_csv, write_manifest

PNG = b"\x89PNG\r\n\x1a\n" + b"payload"

PAGE = """
<html><body>
  <img src="/img/one.jpg">
  <img src="/img/two.png">
</body></html>
"""


class FakeClient:
    """Stand-in for scrapeunblocker.Client - no network, no API key needed."""

    def __init__(self, html=PAGE, image=PNG, fail_times=0):
        self._html = html
        self._image = image
        self._fail_times = fail_times
        self.image_calls = 0
        self.page_calls = 0
        self.last_country = None

    def get_page_source(self, url, proxy_country=None):
        self.page_calls += 1
        self.last_country = proxy_country
        return self._html

    def get_image(self, url):
        self.image_calls += 1
        if self.image_calls <= self._fail_times:
            raise RuntimeError("transient 403")
        return self._image


def _scraper(client, **kw):
    # sleep is stubbed so retry back-off does not slow the test suite
    return ImageScraper(client=client, sleep=lambda _s: None, **kw)


def test_fetch_image_retries_then_succeeds():
    client = FakeClient(fail_times=2)
    scraper = _scraper(client, retries=3)
    data = scraper.fetch_image("https://x.com/a.jpg")
    assert data == PNG
    assert client.image_calls == 3


def test_fetch_image_gives_up_after_retries():
    client = FakeClient(fail_times=5)
    scraper = _scraper(client, retries=3)
    with pytest.raises(RuntimeError):
        scraper.fetch_image("https://x.com/a.jpg")
    assert client.image_calls == 3


def test_empty_image_is_treated_as_failure():
    client = FakeClient(image=b"")
    scraper = _scraper(client, retries=1)
    with pytest.raises(ValueError):
        scraper.fetch_image("https://x.com/a.jpg")


def test_scrape_writes_files_and_records(tmp_path):
    client = FakeClient()
    scraper = _scraper(client)
    records = scraper.scrape("https://shop.example.com/", tmp_path)
    assert len(records) == 2
    assert all(r.ok for r in records)
    files = sorted(p.name for p in tmp_path.iterdir())
    assert files == ["one.png", "two.png"]
    assert (tmp_path / "one.png").read_bytes() == PNG


def test_scrape_limit_and_country_are_passed_through(tmp_path):
    client = FakeClient()
    scraper = _scraper(client, proxy_country="de")
    records = scraper.scrape("https://shop.example.com/", tmp_path, limit=1)
    assert len(records) == 1
    assert client.last_country == "de"


def test_scrape_records_failures_without_raising(tmp_path):
    client = FakeClient(fail_times=99)
    scraper = _scraper(client, retries=2)
    records = scraper.scrape("https://shop.example.com/", tmp_path)
    assert len(records) == 2
    assert all(not r.ok and r.error for r in records)
    assert list(tmp_path.iterdir()) == []


def test_manifest_writers(tmp_path):
    client = FakeClient()
    scraper = _scraper(client)
    records = scraper.scrape("https://shop.example.com/", tmp_path)

    jpath = tmp_path / "manifest.json"
    cpath = tmp_path / "manifest.csv"
    write_manifest(records, jpath)
    write_csv(records, cpath)

    data = json.loads(jpath.read_text())
    assert len(data) == 2
    assert data[0]["ok"] is True
    csv_text = cpath.read_text()
    assert "page_url,image_url,file,bytes,ok,error" in csv_text
