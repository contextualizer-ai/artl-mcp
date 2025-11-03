.PHONY: test test-coverage test-unit test-external-api clean install dev format lint all server doi-test-query upload-test upload release deptry mypy search-test-query cli-demo-search-papers cli-demo-search-recent test-version clean-claude-demos claude-demos-all

# Default target - use test-coverage for comprehensive CI/release checks
all: clean install dev test-coverage format lint mypy deptry build doi-test-query search-test-query test-version

no-tests: clean install dev format lint mypy deptry build doi-test-query search-test-query test-version

# Install everything for development
dev:
	uv sync --group dev

# Install production only
install:
	uv sync

# Run tests with pytest (fast, for development)
test:
	@echo "🧪 Running tests with pytest..."
	uv run pytest tests/ -v --durations=0

# Run tests with coverage using pytest (comprehensive, for CI/releases)
test-coverage:
	@echo "🧪 Running pytest with coverage reporting..."
	uv run pytest --cov=artl_mcp --cov-report=html --cov-report=term --durations=0 tests/

# Run only unit tests (skip external API calls) using pytest
test-unit:
	@echo "🧪 Running unit tests only (no external APIs)..."
	uv run pytest -m "not external_api" tests/ -v

# Run only external API tests using pytest  
test-external-api:
	@echo "🧪 Running external API tests..."
	uv run pytest -m "external_api" tests/ -v

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

# Upload to PyPI
upload:
	uv run hatch publish

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

# Text extraction tools (no email required)
cli-demo-doi-text:
	artl-cli get-doi-text --doi "10.1099/ijsem.0.005153"

cli-demo-pmid-text:
	artl-cli get-pmid-text --pmid "35545607"

cli-demo-bioc-text:
	artl-cli get-full-text-from-bioc --pmid "35545607"

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

# Claude CLI examples using local MCP server
local/claude-demo-rhizosphere.txt:
	@echo "🤖 Claude CLI: Search Europe PMC for rhizosphere microbiome papers"
	claude --debug --verbose --mcp-config claude-mcp-config.json --dangerously-skip-permissions --print "Search Europe PMC for rhizosphere microbiome papers" 2>&1 | tee $@

local/claude-demo-get-paper-by-id.txt:
	@echo "🤖 Claude CLI: Get full paper metadata for DOI:10.1038/nature12352 using Europe PMC"
	claude --debug --verbose --mcp-config claude-mcp-config.json --dangerously-skip-permissions --print "Get full paper metadata for DOI 10.1038/nature12373 using Europe PMC" 2>&1 | tee $@

local/claude-demo-get-all-identifiers.txt:
	@echo "🤖 Claude CLI: Get all identifiers and links for PMID:23851394 using Europe PMC"
	claude --debug --verbose --mcp-config claude-mcp-config.json --dangerously-skip-permissions --print "Get all available identifiers and access links for PMID:23851394 using Europe PMC" 2>&1 | tee $@

local/claude-demo-full-text.txt:
	@echo "🤖 Claude CLI: Get full text content"
	claude --debug --verbose --mcp-config claude-mcp-config.json --dangerously-skip-permissions --print "Get the full text for DOI 10.1371/journal.pone.0000217" 2>&1 | tee $@


local/claude-demo-windowing.txt:
	@echo "🤖 Claude CLI: Get partial text using windowing"
	claude --debug --verbose --mcp-config claude-mcp-config.json --dangerously-skip-permissions --print "Get characters 1000-3000 from the full text of DOI 10.1371/journal.pone.0000217" 2>&1 | tee $@

local/claude-demo-pdf-to-markdown.txt:
	@echo "🤖 Claude CLI: Convert Europe PMC PDF to Markdown"
	claude --debug --verbose --mcp-config claude-mcp-config.json --dangerously-skip-permissions --print "Convert the PDF for PMC3737249 to Markdown format" 2>&1 | tee $@

local/claude-demo-supplementary-material.txt:
	@echo "🤖 Claude CLI: Get supplementary material from PMC"
	claude --debug --verbose --mcp-config claude-mcp-config.json --dangerously-skip-permissions --print "Get supplementary material for PMC7294781 file index 1" 2>&1 | tee $@

# Clean up Claude demo output files
clean-claude-demos:
	rm -f local/claude-demo-*.txt

# Run all Claude demos with cleanup (comprehensive meta-target)
claude-demos-all: clean-claude-demos local/claude-demo-rhizosphere.txt local/claude-demo-get-paper-by-id.txt local/claude-demo-get-all-identifiers.txt local/claude-demo-full-text.txt local/claude-demo-pdf-to-markdown.txt local/claude-demo-windowing.txt local/claude-demo-supplementary-material.txt
	@echo "✅ All Claude demos completed! Check local/claude-demo-*.txt for output"
