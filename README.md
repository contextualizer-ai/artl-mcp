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
uvx artl-cli get-doi-metadata --doi "10.1038/nature12373"
uvx artl-cli search-papers-by-keyword --query "CRISPR gene editing" --max-results 5
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
- Automatic file saving with configurable directories
- Cross-platform filename sanitization
- Multiple output formats (JSON, TXT, CSV, PDF)
- Temp file management with cleanup

## Available MCP Tools

When running as an MCP server, you get access to 32 tools organized into categories:

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

The `artl-cli` command provides access to all functionality:

```bash
# Metadata retrieval
artl-cli get-doi-metadata --doi "10.1038/nature12373"
artl-cli get-abstract-from-pubmed-id --pmid "23851394"

# Literature search
artl-cli search-papers-by-keyword --query "machine learning" --max-results 10
artl-cli search-recent-papers --query "COVID-19" --years-back 2

# Full text (requires email for some sources)
artl-cli get-full-text-from-doi --doi "10.1038/nature12373" --email "user@institution.edu"

# Identifier conversion
artl-cli doi-to-pmid --doi "10.1038/nature12373"
artl-cli get-all-identifiers --identifier "PMC3737249"

# Citation analysis  
artl-cli get-paper-citations --doi "10.1038/nature12373"
```

## Configuration

### Email Requirements
Several APIs require institutional email addresses:
```bash
export ARTL_EMAIL_ADDR="researcher@university.edu"
# or create local/.env file with: ARTL_EMAIL_ADDR=researcher@university.edu
```

**MCP Client Configuration:** Different MCP clients support configuration injection. ARTL-MCP's enhanced configuration system provides multiple methods for email setup:

- **Claude Desktop**: Inherits system environment variables automatically
- **Goose Desktop**: Requires MCP extension configuration (see [USERS.md](USERS.md#mcp-client-configuration-issues))  
- **Other clients**: May support client-specific configuration injection

See [USERS.md](USERS.md#email-configuration-for-literature-access) for comprehensive configuration instructions.

### File Output
Configure where files are saved:
```bash
export ARTL_OUTPUT_DIR="~/Papers"           # Default: ~/Documents/artl-mcp
export ARTL_TEMP_DIR="/tmp/my-artl-temp"    # Default: system temp + artl-mcp
export ARTL_KEEP_TEMP_FILES=true            # Default: false
```

## Supported Identifier Formats

**DOI**: `10.1038/nature12373`, `doi:10.1038/nature12373`, `https://doi.org/10.1038/nature12373`

**PMID**: `23851394`, `PMID:23851394`, `pmid:23851394`

**PMCID**: `PMC3737249`, `3737249`, `PMC:3737249`

All tools automatically detect and normalize identifier formats.

## Development Setup

```bash
git clone https://github.com/contextualizer-ai/artl-mcp.git
cd artl-mcp
uv sync --group dev

# Run tests
make test                    # Fast development tests
make test-coverage          # Full test suite with coverage

# Code quality
make lint                   # Ruff linting
make format                 # Black formatting
make mypy                   # Type checking
```

## Documentation

- **[USERS.md](USERS.md)** - Comprehensive user guide with examples
- **[DEVELOPERS.md](DEVELOPERS.md)** - Development setup and architecture