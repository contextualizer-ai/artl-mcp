# ARTL-MCP: All Roads to Literature

An MCP (Model Context Protocol) server and CLI toolkit for comprehensive scientific literature retrieval and analysis using PMIDs, DOIs, PMCIDs, and keyword searches.

## Quick Start

### MCP Server (Recommended)

Add this to your Claude Desktop MCP configuration:

```json
{
  "mcpServers": {
    "artl-mcp": {
      "command": "uvx",
      "args": ["artl-mcp"]
    }
  }
}
```

### Standalone CLI

```bash
# Install and use CLI commands
uvx --from artl-mcp artl-cli get-doi-metadata --doi "10.1038/nature12373"
uvx --from artl-mcp artl-cli search-papers-by-keyword --query "CRISPR gene editing" --max-results 5
```

## Core Features

### 🔍 **Literature Search & Discovery**
- Keyword-based paper search with advanced filtering
- Recent publication discovery
- PubMed search with multiple output formats

### 📄 **Metadata & Content Retrieval**
- DOI/PMID/PMCID metadata extraction
- Abstract retrieval from PubMed
- Full-text access via multiple sources (PMC, Unpaywall, BioC)
- PDF text extraction and processing

### 🔗 **Identifier Management**
- Universal identifier conversion (DOI ↔ PMID ↔ PMCID)
- Support for multiple input formats (URLs, CURIEs, raw IDs)
- Comprehensive identifier validation

### 📊 **Citation Networks**
- Reference analysis (papers cited BY a given paper)
- Citation analysis (papers that CITE a given paper)
- Multi-source citation data (CrossRef, OpenAlex, Semantic Scholar)
- Related paper discovery through citation networks

### 💾 **File Management**
- **MCP Mode**: Returns data directly without file saving (optimal for AI assistants)
- **CLI Mode**: Full file saving with path reporting and content management
- **Content size management** - large content automatically handled appropriately
- **Memory-efficient streaming** for large files (PDFs, datasets)  
- **Cross-platform filename sanitization**
- **Multiple output formats** (JSON, TXT, CSV, PDF) in CLI mode
- **Configurable directories** and temp file management in CLI mode

## Available MCP Tools

When running as an MCP server, you get access to 32 tools organized into categories:

### 🔄 **MCP vs CLI Mode Differences**

**MCP Mode** (AI assistants): Returns data directly without file saving:
```json
{
  "data": { /* tool-specific content */ },
  "mcp_mode": true,
  "note": "Data returned directly - use CLI for file saving"
}
```

**CLI Mode** (command line): Full file saving with path reporting:
```json
{
  "data": { /* tool-specific content */ },
  "saved_to": "/path/to/saved/file.json"
}
```

### Literature Search
- `search_papers_by_keyword` - Advanced keyword search with filtering
- `search_recent_papers` - Find recent publications  
- `search_pubmed_for_pmids` - PubMed search returning PMIDs

### Metadata & Abstracts
- `get_doi_metadata` - Comprehensive DOI metadata
- `get_abstract_from_pubmed_id` - PubMed abstracts
- `get_doi_fetcher_metadata` - Enhanced metadata (requires email)
- `get_unpaywall_info` - Open access availability

### Full Text Access
- `get_full_text_from_doi` - Multi-source full text (requires email)
- `extract_pdf_text` - PDF text extraction
- `get_pmcid_text` - PMC full text
- `get_full_text_from_bioc` - BioC format text

### Identifier Conversion
- `get_all_identifiers` - Get all IDs for any identifier
- `doi_to_pmid`, `pmid_to_doi` - Individual conversions
- `validate_identifier` - Format validation

### Citation Networks  
- `get_paper_references` - Papers cited by a given paper
- `get_paper_citations` - Papers citing a given paper
- `get_citation_network` - Comprehensive citation data
- `find_related_papers` - Citation-based recommendations

## CLI Commands

The `artl-cli` command provides access to all functionality. When using `uvx`, specify the package name:

```bash
# Metadata retrieval
uvx --from artl-mcp artl-cli get-doi-metadata --doi "10.1038/nature12373"
uvx --from artl-mcp artl-cli get-abstract-from-pubmed-id --pmid "23851394"

# Literature search
uvx --from artl-mcp artl-cli search-papers-by-keyword --query "machine learning" --max-results 10
uvx --from artl-mcp artl-cli search-recent-papers --query "COVID-19" --years-back 2

# Full text (requires email for some sources)
uvx --from artl-mcp artl-cli get-full-text-from-doi --doi "10.1038/nature12373" --email "user@institution.edu"

# Identifier conversion
uvx --from artl-mcp artl-cli doi-to-pmid --doi "10.1038/nature12373"
uvx --from artl-mcp artl-cli get-all-identifiers-from-europepmc --identifier "PMC3737249"
```

**Note:** Citation analysis tools are MCP-only (not available as CLI commands). Use the MCP server for citation network analysis.

**Note for local development**: If you have the package installed locally with `uv sync`, you can use `uv run artl-cli` directly without the `--from` flag.

## Configuration

### Email Requirements
Several APIs require institutional email addresses.

> **⚠️ Important:** Replace example emails with your actual institutional email address.

```bash
export ARTL_EMAIL_ADDR="researcher@university.edu"  # Replace with your real email
# or create local/.env file with: ARTL_EMAIL_ADDR=researcher@university.edu
```

**MCP Client Configuration:** Different MCP clients support configuration injection. ARTL-MCP's enhanced configuration system provides multiple methods for email setup:

- **Claude Desktop**: Inherits system environment variables automatically
- **Goose Desktop**: Requires MCP extension configuration (see [USERS.md](USERS.md#mcp-client-configuration-issues))  
- **Other clients**: May support client-specific configuration injection

See [USERS.md](USERS.md#email-configuration-for-literature-access) for comprehensive configuration instructions.

### File Output (CLI Mode Only)
Configure where files are saved when using CLI commands:
```bash
export ARTL_OUTPUT_DIR="~/Papers"           # Default: ~/Documents/artl-mcp
export ARTL_TEMP_DIR="/tmp/my-artl-temp"    # Default: system temp + artl-mcp
export ARTL_KEEP_TEMP_FILES=true            # Default: false
```

**Note**: MCP mode returns data directly without file saving.

## Supported Identifier Formats

**DOI**: `10.1038/nature12373`, `doi:10.1038/nature12373`, `https://doi.org/10.1038/nature12373`

**PMID**: `23851394`, `PMID:23851394`, `pmid:23851394`

**PMCID**: `PMC3737249`, `3737249`, `PMC:3737249`

All tools automatically detect and normalize identifier formats.

## Development Setup

```bash
# Clone and install
git clone https://github.com/contextualizer-ai/artl-mcp.git
cd artl-mcp
uv sync --group dev

# Run CLI commands during development
uv run artl-cli --help
uv run artl-cli get-doi-metadata --doi "10.1038/nature12373"
uv run artl-cli search-papers-by-keyword --query "CRISPR" --max-results 5

# Run the MCP server locally
uv run artl-mcp

# Run tests
make test                    # Fast development tests
make test-coverage          # Full test suite with coverage

# Code quality
make lint                   # Ruff linting
make format                 # Black formatting
make mypy                   # Type checking
```

**Development vs. Production Usage:**
- **Developers** (local repo): Use `uv run artl-cli` after `uv sync`
- **End users** (no local install): Use `uvx --from artl-mcp artl-cli`

## Documentation

- **[USERS.md](USERS.md)** - Comprehensive user guide with examples
- **[DEVELOPERS.md](DEVELOPERS.md)** - Development setup and architecture