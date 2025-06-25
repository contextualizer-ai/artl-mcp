.PHONY: test-coverage clean install dev format lint all server doi-test-query upload-test upload release deptry mypy

# Default target
all: clean install dev test-coverage format lint mypy deptry build doi-test-query

# Install everything for development
dev:
	uv sync --group dev

# Install production only
install:
	uv sync

# Run tests with coverage
test-coverage:
	uv run pytest --cov=artl_mcp --cov-report=html --cov-report=term tests/

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
	uv run artl-mcp --server

# Run DOI query mode
doi-test-query:
	uv run artl-mcp --doi-query 10.1099/ijsem.0.005153 # without extra --doi argument

 # Format code with black
format:
	uv run black src/ tests/

lint:
	uv run ruff check --fix src/ tests/

# Check for unused dependencies
deptry:
	uvx deptry .

# Type checking
mypy:
	uv run mypy src/


# Build package with hatch
build:
	uv run hatch build

# Upload to TestPyPI
upload-test:
	uv run hatch publish --repo test

# Upload to PyPI (set TWINE_PASSWORD environment variable first)
upload:
	uv run twine upload dist/*

# Complete release workflow
release: clean test-coverage build upload

# CLI Examples - Demonstrate all available CLI tools
# Basic metadata tools
cli-demo-doi-metadata:
	artl-get-doi-metadata --doi "10.1099/ijsem.0.005153"

cli-demo-pubmed-abstract:
	artl-get-abstract-from-pubmed-id --pmid "35545607"

# DOI/PMID conversion tools
cli-demo-doi-to-pmid:
	artl-doi-to-pmid --doi "10.1099/ijsem.0.005153"

cli-demo-pmid-to-doi:
	artl-pmid-to-doi --pmid "35545607"

# PMC ID tools
cli-demo-pmcid-to-pmid:
	artl-get-pmid-from-pmcid --pmcid "PMC9087108"

#cli-demo-pmcid-text:
#	# Warning: Error fetching Unpaywall data: 422 Client Error: UNPROCESSABLE ENTITY for url: https://api.unpaywall.org/v2/10.21873/invivo.12834?email=pubmed_utils@example.com
#	artl-get-pmcid-text --pmcid "PMC9087108"

# Text extraction tools (no email required)
cli-demo-doi-text:
	artl-get-doi-text --doi "10.1099/ijsem.0.005153"

cli-demo-pmid-text:
	artl-get-pmid-text --pmid "35545607"

cli-demo-bioc-text:
	artl-get-full-text-from-bioc --pmid "35545607"

#cli-demo-pdf-extract:
#	artl-extract-pdf-text --pdf-url "https://www.example.com/sample.pdf"

# URL utilities
cli-demo-extract-doi:
	artl-extract-doi-from-url --doi-url "https://doi.org/10.1099/ijsem.0.005153"

# Tools requiring email (use placeholder - user must provide real email)
cli-demo-doi-fetcher-metadata:
	@echo "Example: artl-get-doi-fetcher-metadata --doi '10.1099/ijsem.0.005153' --email 'your@email.com'"

cli-demo-unpaywall:
	@echo "Example: artl-get-unpaywall-info --doi '10.1099/ijsem.0.005153' --email 'your@email.com'"

cli-demo-full-text-doi:
	@echo "Example: artl-get-full-text-from-doi --doi '10.1099/ijsem.0.005153' --email 'your@email.com'"

cli-demo-full-text-info:
	@echo "Example: artl-get-full-text-info --doi '10.1099/ijsem.0.005153' --email 'your@email.com'"

cli-demo-pdf-url-text:
	@echo "Example: artl-get-text-from-pdf-url --pdf-url 'https://example.com/paper.pdf' --email 'your@email.com'"

cli-demo-clean-text:
	@echo "Example: artl-clean-text --text 'Some messy text...' --email 'your@email.com'"

## Run all CLI demos that don't require email
#cli-demo-all:
#	@echo "=== Running all CLI demos (no email required) ==="
#	@echo "1. DOI Metadata:"
#	@$(MAKE) cli-demo-doi-metadata
#	@echo "\n2. PubMed Abstract:"
#	@$(MAKE) cli-demo-pubmed-abstract
#	@echo "\n3. DOI to PMID:"
#	@$(MAKE) cli-demo-doi-to-pmid
#	@echo "\n4. PMID to DOI:"
#	@$(MAKE) cli-demo-pmid-to-doi
#	@echo "\n5. Extract DOI from URL:"
#	@$(MAKE) cli-demo-extract-doi
#	@echo "\n=== Email-required tools (examples only) ==="
#	@$(MAKE) cli-demo-doi-fetcher-metadata
#	@$(MAKE) cli-demo-unpaywall
#	@$(MAKE) cli-demo-full-text-doi
#	@$(MAKE) cli-demo-full-text-info
#	@$(MAKE) cli-demo-pdf-url-text
#	@$(MAKE) cli-demo-clean-text

# List all available CLI commands
cli-list:
	@echo "Available CLI commands:"
	@echo "Basic tools (no email required):"
	@echo "  artl-get-doi-metadata"
	@echo "  artl-get-abstract-from-pubmed-id"
	@echo "  artl-doi-to-pmid"
	@echo "  artl-pmid-to-doi"
	@echo "  artl-get-pmid-from-pmcid"
	@echo "  artl-get-pmcid-text"
	@echo "  artl-get-doi-text"
	@echo "  artl-get-pmid-text"
	@echo "  artl-get-full-text-from-bioc"
	@echo "  artl-extract-pdf-text"
	@echo "  artl-extract-doi-from-url"
	@echo ""
	@echo "Advanced tools (email required):"
	@echo "  artl-get-doi-fetcher-metadata"
	@echo "  artl-get-unpaywall-info"
	@echo "  artl-get-full-text-from-doi"
	@echo "  artl-get-full-text-info"
	@echo "  artl-get-text-from-pdf-url"
	@echo "  artl-clean-text"
