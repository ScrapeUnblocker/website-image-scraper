from image_scraper.scraper import _filename_for, discover_image_urls

SAMPLE = """
<html><body>
  <img src="/media/a.jpg">
  <img src="media/a.jpg">                     <!-- resolves to same absolute URL as above -->
  <img data-src="/lazy/b.png" src="spacer.gif">
  <picture>
    <source srcset="/img/c-1x.webp 1x, /img/c-2x.webp 2x">
    <img src="https://cdn.example.com/d.jpeg">
  </picture>
  <img src="data:image/gif;base64,R0lGOD= ">
  <img src="/media/a.jpg#fragment">
</body></html>
"""


def test_discover_resolves_and_dedupes():
    urls = discover_image_urls(SAMPLE, "https://shop.example.com/catalog/")
    assert "https://shop.example.com/media/a.jpg" in urls
    assert "https://shop.example.com/catalog/media/a.jpg" in urls
    assert "https://shop.example.com/lazy/b.png" in urls
    assert "https://shop.example.com/catalog/spacer.gif" in urls
    assert "https://shop.example.com/img/c-1x.webp" in urls
    assert "https://shop.example.com/img/c-2x.webp" in urls
    assert "https://cdn.example.com/d.jpeg" in urls
    # data: URI skipped by default
    assert not any(u.startswith("data:") for u in urls)
    # de-duplicated (fragment stripped -> same as /media/a.jpg)
    assert len(urls) == len(set(urls))
    assert urls.count("https://shop.example.com/media/a.jpg") == 1


def test_discover_can_include_data_uris():
    urls = discover_image_urls(SAMPLE, "https://shop.example.com/", include_data_uris=True)
    assert any(u.startswith("data:image/gif") for u in urls)


def test_filename_normalises_extension_to_png():
    used: set[str] = set()
    assert _filename_for("https://x.com/path/photo.jpg", 0, used) == "photo.png"
    assert _filename_for("https://x.com/path/pic.webp?w=200", 1, used) == "pic.png"


def test_filename_handles_collisions_and_empties():
    used: set[str] = set()
    assert _filename_for("https://x.com/a/logo.png", 0, used) == "logo.png"
    assert _filename_for("https://x.com/b/logo.png", 1, used) == "logo_1.png"
    # no basename -> synthesised name
    assert _filename_for("https://x.com/", 2, used) == "image_2.png"
    # data URI -> synthesised name
    assert _filename_for("data:image/png;base64,AAAA", 3, used) == "image_3.png"
