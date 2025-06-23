.PHONY: test clean install dev format lint all

# Default target
all: clean install dev test build

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
# test-coverage:
# 	pytest --cov=allroadstoliterature tests/

# Clean up build artifacts
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf src/all_roads_to_literature.egg-info

# Run server mode
server:
	uv run artl --server

# Run DOI query mode
doi-test-query:
	uv run artl --doi-query --doi 10.1099/ijsem.0.005153

# # Format code with black
# format:
# 	black src/ tests/
#
# # Lint code with flake8
# lint:
# 	flake8 src/ tests/
#
# # Build package
# build:
# 	python -m build

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
