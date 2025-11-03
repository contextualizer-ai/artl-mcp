# ARTL-MCP: All Roads to Literature

An MCP (Model Context Protocol) server and CLI toolkit for comprehensive scientific literature retrieval and analysis using PMIDs, DOIs, PMCIDs, and keyword searches.

## Requirements

- **Python**: 3.11 or later
- **uv**: Python package installer ([install guide](https://github.com/astral-sh/uv))

> **📖 New to artl-mcp?** See [PREREQUISITES.md](PREREQUISITES.md) for detailed setup instructions including Python/uv installation, MCP client setup, and more.

## Three Ways to Use ARTL-MCP

### 1. CLI Only (FREE - No AI Required)
Use directly from command line with just Python + uv:
```bash
uvx --from artl-mcp artl-cli get-doi-metadata --doi "10.1038/nature12373"
```
- ✅ No installation, no API keys, no costs
- ✅ Direct access to literature databases
- ✅ Perfect for scripting and automation

### 2. MCP with AI Assistant (Recommended)
Use with any MCP-compatible AI assistant for natural language queries:
- **Claude Desktop** (most popular)
- **Goose Desktop**
- **Zed Editor**
- **Continue** (VS Code)
- Any MCP-compatible tool

> **Note**: You can use ANY MCP client - not just Claude! See [PREREQUISITES.md](PREREQUISITES.md) for setup guides.

### 3. Development (Optional)
For contributors working on artl-mcp itself. See [DEVELOPERS.md](DEVELOPERS.md).

## Quick Start

### MCP Server with AI Assistant

**Example: Claude Desktop** (works with any MCP client)

Add this to your `claude_desktop_config.json`:

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

Then ask Claude: `"Search Europe PMC for papers about CRISPR"`

> **Other MCP clients**: Goose, Zed, Continue, etc. also work! See [PREREQUISITES.md](PREREQUISITES.md) for setup guides for each client.

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
- Full-text access via multiple sources:
  - **PMC** (PubMed Central) - MCP + CLI
  - **Unpaywall** - MCP + CLI
  - **Europe PMC** - MCP + CLI
  - **BioC XML format** - CLI only
- PDF text extraction and processing

### 🔗 **Identifier Management**
- Universal identifier conversion (DOI ↔ PMID ↔ PMCID)
- Support for multiple input formats (URLs, CURIEs, raw IDs)
- Comprehensive identifier validation

### 📊 **Citation Networks**
- Reference analysis (papers cited BY a given paper)
- Citation analysis (papers that CITE a given paper)
- Citation data from CrossRef (when citation tools are enabled)
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

When running as an MCP server, you get access to 6 core tools. **Note:** 33 additional tools are currently disabled pending testing and stabilization (see Issues #210, #212).

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

### Currently Active MCP Tools (6):

1. **`search_europepmc_papers`** - Search Europe PMC database for papers
2. **`get_europepmc_paper_by_id`** - Get full metadata from Europe PMC by ID
3. **`get_all_identifiers_from_europepmc`** - Universal ID translation via Europe PMC
4. **`get_europepmc_full_text`** - Retrieve full text from Europe PMC
5. **`get_europepmc_pdf_as_markdown`** - Convert Europe PMC PDFs to Markdown
6. **`get_pmc_supplemental_material`** - Get supplementary materials from PMC

### Disabled/Unavailable MCP Tools (33 tools - see issues):

The following tools are implemented but currently disabled (commented out in main.py):
- ❌ **Citation analysis tools** (4 tools) - Issue #210
- ❌ **BioC full text tool** (1 tool) - Issue #213
- ❌ **DOI metadata tools** (3 tools) - Issue #212
- ❌ **Identifier conversion tools** (4 tools) - Issue #212
- ❌ **PubMed abstract/text retrieval** (5 tools) - Issue #212
- ❌ **PDF extraction tools** (3 tools) - Issue #212
- ❌ **Search tools** (2 tools) - Issue #212
- ❌ **Other tools** (11 tools) - Issue #212

**Note:** CLI has 23 active commands, many corresponding to these disabled MCP tools.

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

**Note:** Citation analysis tools are currently unavailable in both MCP and CLI. See Issue #210 for updates.

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

### Optional: Claude Code CLI for Makefile Demos

> **⚠️ Not Required**: Claude Code CLI is ONLY needed for running `make claude-demos-all` tests. Normal users and MCP users don't need this.

The repository includes optional MCP integration tests via Makefile targets:

```bash
make claude-demos-all  # Run all MCP demos (requires Claude Code CLI)
```

**Requirements for demos:**
- Claude Code CLI: `npm install -g @anthropic-ai/claude-code`
- Anthropic API key (pay-per-use, ~$1-2 for all demos based on current pricing – see [Anthropic pricing](https://www.anthropic.com/pricing))

See [PREREQUISITES.md](PREREQUISITES.md#claude-code-cli-optional---development-only) for setup instructions.

## Documentation

- **[PREREQUISITES.md](PREREQUISITES.md)** - Setup guide (Python, uv, MCP clients, email config)
- **[USERS.md](USERS.md)** - Comprehensive user guide with examples
- **[DEVELOPERS.md](DEVELOPERS.md)** - Development setup and architecture
- **[CBORG.md](CBORG.md)** - CBORG usage for LBL users (spending tracking)