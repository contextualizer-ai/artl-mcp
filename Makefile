.PHONY: test test-coverage clean install dev format lint all server doi-test-query build upload-test upload

# Default target
all: clean install dev test test-coverage format lint build doi-test-query

# Install the package in development mode
install:
	uv pip install -e .

# Install with development dependencies
dev:
	uv pip install -e ".[dev]"

# Run tests
test:
	pytest tests/

# # Run tests with coverage
test-coverage:
	uv run pytest --cov=allroadstoliterature --cov-report=html --cov-report=term tests/

# Clean up build artifacts
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf src/*.egg-info

# Run server mode
server:
	uv run artl --server

# Run DOI query mode
doi-test-query:
	uv run artl --doi-query 10.1099/ijsem.0.005153 # without extra --doi argument

 # Format code with black
format:
	uv run black src/ tests/

lint:
	uv run ruff check --fix src/ tests/


# Build package with uv
build:
	uv pip install build
	uv run python -m build

# Upload to TestPyPI
upload-test:
	uv pip install twine
	uv run python -m twine upload --repository testpypi dist/*

# Upload to PyPI
upload:
	uv pip install twine
	uv run python -m twine upload dist/*
