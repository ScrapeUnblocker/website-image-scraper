.PHONY: install lint format test run clean

install:
	pip install -e ".[dev]"
	pre-commit install || true

lint:
	ruff check .

format:
	ruff format .

test:
	pytest -q

# Example run: make run URL=https://books.toscrape.com/
URL ?= https://books.toscrape.com/
run:
	su-image-scraper "$(URL)" --limit 5 --manifest images/manifest.json -v

clean:
	rm -rf build dist *.egg-info .pytest_cache .ruff_cache images
	find . -type d -name __pycache__ -exec rm -rf {} +
