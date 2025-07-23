.PHONY: test-coverage clean install dev format lint all server doi-test-query upload-test upload release deptry mypy search-test-query cli-demo-search-papers cli-demo-search-recent test-version

# Default target
all: clean install dev test-coverage format lint mypy deptry build doi-test-query search-test-query test-version

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

# Test search functionality with sample query  
search-test-query:
	uv run artl-mcp --pmid-search "machine learning" --max-results 3

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

# CLI Examples - Demonstrate all available CLI tools using grouped commands
# Basic metadata tools
cli-demo-doi-metadata:
	artl-cli get-doi-metadata --doi "10.1099/ijsem.0.005153"

cli-demo-pubmed-abstract:
	artl-cli get-abstract-from-pubmed-id --pmid "35545607"

# DOI/PMID conversion tools
cli-demo-doi-to-pmid:
	artl-cli doi-to-pmid --doi "10.1099/ijsem.0.005153"

cli-demo-pmid-to-doi:
	artl-cli pmid-to-doi --pmid "35545607"

# PMC ID tools
cli-demo-pmcid-to-pmid:
	artl-cli get-pmid-from-pmcid --pmcid "PMC9087108"

#cli-demo-pmcid-text:
#	# Warning: Error fetching Unpaywall data: 422 Client Error: UNPROCESSABLE ENTITY for url: https://api.unpaywall.org/v2/10.21873/invivo.12834?email=pubmed_utils@example.com
#	artl-cli get-pmcid-text --pmcid "PMC9087108"

# Text extraction tools (no email required)
cli-demo-doi-text:
	artl-cli get-doi-text --doi "10.1099/ijsem.0.005153"

cli-demo-pmid-text:
	artl-cli get-pmid-text --pmid "35545607"

cli-demo-bioc-text:
	artl-cli get-full-text-from-bioc --pmid "35545607"

#cli-demo-pdf-extract:
#	artl-cli extract-pdf-text --pdf-url "https://www.example.com/sample.pdf"

# URL utilities
cli-demo-extract-doi:
	artl-cli extract-doi-from-url --doi-url "https://doi.org/10.1099/ijsem.0.005153"

# Search tools
cli-demo-search-papers:
	artl-cli search-papers-by-keyword --query "machine learning" --max-results 5 --filter-type "journal-article"

cli-demo-search-recent:
	artl-cli search-recent-papers --query "artificial intelligence" --years-back 3 --max-results 3

# Tools requiring email (use placeholder - user must provide real email)
cli-demo-doi-fetcher-metadata:
	@echo "Example: artl-cli get-doi-fetcher-metadata --doi '10.1099/ijsem.0.005153' --email 'your@email.com'"

cli-demo-unpaywall:
	@echo "Example: artl-cli get-unpaywall-info --doi '10.1099/ijsem.0.005153' --email 'your@email.com'"

cli-demo-full-text-doi:
	@echo "Example: artl-cli get-full-text-from-doi --doi '10.1099/ijsem.0.005153' --email 'your@email.com'"

cli-demo-full-text-info:
	@echo "Example: artl-cli get-full-text-info --doi '10.1099/ijsem.0.005153' --email 'your@email.com'"

cli-demo-pdf-url-text:
	@echo "Example: artl-cli get-text-from-pdf-url --pdf-url 'https://example.com/paper.pdf' --email 'your@email.com'"

cli-demo-clean-text:
	@echo "Example: artl-cli clean-text --text 'Some messy text...' --email 'your@email.com'"

# List all available CLI commands
cli-list:
	artl-cli --help

# Test version flag
test-version:
	@echo "🔢 Testing version flag..."
	uv run artl-mcp --version
