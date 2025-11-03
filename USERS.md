# ARTL-MCP User Guide

This guide provides comprehensive information for end users of ARTL-MCP (All Roads to Literature - Model Context
Protocol), a powerful toolkit for scientific literature retrieval and analysis.

## Table of Contents

- [Getting Started](#getting-started)
- [MCP Server Usage](#mcp-server-usage)
- [CLI Usage](#cli-usage)
- [Configuration](#configuration)
- [Identifier Formats](#identifier-formats)
- [File Management](#file-management)
- [Citation Networks](#citation-networks)
- [API Requirements](#api-requirements)
- [Troubleshooting](#troubleshooting)

## Getting Started

### Installation Options

**Option 1: Direct Usage (Recommended)**

```bash
# MCP Server
uvx artl-mcp

# CLI Commands
uvx --from artl-mcp artl-cli get-doi-metadata --doi "10.1038/nature12373"
```

**Option 2: Claude Desktop Integration**
Add to your Claude Desktop MCP configuration:

```json
{
  "mcpServers": {
    "artl-mcp": {
      "command": "uvx",
      "args": [
        "artl-mcp"
      ]
    }
  }
}
```

## MCP Server Usage

When running as an MCP server, ARTL-MCP provides 35+ tools organized into these categories:

### Literature Search Tools

- **`search_papers_by_keyword`** - Search papers using keywords with advanced filtering
- **`search_recent_papers`** - Find recent publications in specific fields
- **`search_pubmed_for_pmids`** - Search PubMed and return PMIDs

**Example queries to try:**

- "Find recent papers about CRISPR gene editing"
- "Search for machine learning papers published in the last 2 years"
- "Get metadata for DOI 10.1038/nature12373"

### Metadata & Content Tools

- **`get_doi_metadata`** - Get comprehensive paper metadata from DOI
- **`get_abstract_from_pubmed_id`** - Retrieve abstracts from PubMed
- **`get_full_text_from_doi`** - Access full text from multiple sources
- **`extract_pdf_text`** - Extract text from PDF URLs
- **`download_pdf_from_doi`** - Download PDF files directly from DOI via Unpaywall (requires email)
- **`download_pdf_from_url`** - Download PDF files directly from URL (no text extraction)

### Identifier Conversion Tools

- **`get_all_identifiers`** - Get all available IDs (DOI, PMID, PMCID) for any identifier
- **`doi_to_pmid`**, **`pmid_to_doi`** - Convert between identifier types
- **`validate_identifier`** - Check if an identifier is properly formatted

### Citation Analysis Tools

- **`get_paper_references`** - Find papers cited BY a given paper
- **`get_paper_citations`** - Find papers that CITE a given paper
- **`get_citation_network`** - Get comprehensive citation data
- **`find_related_papers`** - Discover related papers through citations

## Claude Desktop Integration

When using ARTL-MCP with Claude Desktop, you get seamless access to all literature tools through natural language queries. The MCP server handles the technical details while you focus on your research questions.

### Claude CLI Flags for Advanced Usage

For power users, Claude Desktop supports several command-line flags that provide additional control and debugging information:

```bash
claude --debug --verbose --dangerously-skip-permissions --print "your query here"
```

**Flag Explanations:**

- **`--debug`** - Enable debug output showing internal MCP communications and tool calls
- **`--verbose`** - Provide detailed logging of all operations and API calls  
- **`--dangerously-skip-permissions`** - Skip permission checks (use with caution)
- **`--print`** - Output results directly to terminal instead of chat interface

### Example Claude Desktop Queries

#### Basic Metadata Retrieval

**Query:** `"Who were the authors of 10.1093/nar/gkw343?"`

**Response:**
```
The authors of DOI 10.1093/nar/gkw343 are:
Enis Afgan, Dannon Baker, Marius van den Beek, Daniel Blankenberg, Dave Bouvier, 
Martin Čech, John Chilton, Dave Clements, Nate Coraor, Carl Eberhard, Björn Grüning, 
Aysam Guerler, Jennifer Hillman-Jackson, Greg Von Kuster, Eric Rasche, Nicola Soranzo, 
Nitesh Turaga, James Taylor, Anton Nekrutenko, and Jeremy Goecks.
```

#### Abstract Retrieval

**Query:** `"Show me the abstract of PMID:28231859"`

**Response:**
```
**Title:** Structural variability and niche differentiation in the rhizosphere and endosphere bacterial microbiome of field-grown poplar trees

**Abstract:** This study investigated bacterial microbiomes in different compartments of field-grown poplar trees, finding that rhizosphere microbiomes show lower structural variability than endosphere microbiomes. Each plant compartment (rhizosphere soil, root, stem, leaf) represents a unique ecological niche with distinct bacterial communities, demonstrating microbiome niche differentiation and adaptation throughout the plant.
```

#### Full Text Retrieval with File Saving

**Query:** `"Download the full text of PMC7523075. Tell me where you saved it."`

**Response:**
```
I saved the full text of PMC7523075 in the temporary directory with an auto-generated filename: 
/var/folders/.../artl-mcp/pmcid_text_PMC7523075_20250725_144439.txt (73K)

The file contains the complete text of the research article and is available for offline access.
```

#### Literature Search with PMIDs

**Query:** `"Show me the PMIDs of some papers that are indexed with the keywords 'hydrocarbon microbiome'"`

**Response:**
```
Here are PMIDs for papers indexed with "hydrocarbon microbiome" keywords:
39003601, 37445997, 29660711, 35421499, 37929905, 32208932, 38448800, 36427064, 
25605935, 37450270, 36029349, 36049506, 33205868, 39341532, 33205872, 36738429, 
33332645, 31713494, 34511152, 37779211

Total found: 12,118 papers (showing first 20 PMIDs)
```

#### PDF Discovery (Requires Email)

**Query:** `"Show me the PMIDs of papers about 'CRISPR gene editing'. Can you find a PDF URL for any of them?"`

**Response:**
```
I found several papers about CRISPR gene editing. However, to search for PDF URLs through 
the Unpaywall service, I need an email address for API access. Please set your email 
address using: export ARTL_EMAIL_ADDR="your@email.com"
```

#### Direct PDF Download (New Feature)

**Query:** `"My email address is MAM@lbl.gov. Download and save the PDF for 10.1371/journal.pone.0123456. I want the filename to be 0123456.pdf. Tell me the full path in which it was saved."`

**Response:**
```
I successfully downloaded the PDF for DOI 10.1371/journal.pone.0123456 using the Unpaywall API.

File saved to: /Users/MAM/Documents/artl-mcp/0123456.pdf
File size: 502,381 bytes (490 KB)
PDF URL: https://journals.plos.org/plosone/article/file?id=10.1371/journal.pone.0123456&type=printable

The PDF file has been saved directly as a binary file without any text extraction or content processing.
```

### File Saving Behavior

ARTL-MCP automatically saves retrieved content to your system's temporary directory with descriptive filenames:

**Filename Pattern:**
```
{content_type}_{identifier}_{timestamp}.{extension}
```

**Examples:**
- `metadata_10.1038_nature12373_20250725_152502.json`
- `pmcid_text_PMC7523075_20250725_144439.txt`  
- `abstract_PMID28231859_20250725_153015.txt`
- `search_hydrocarbon_microbiome_20250725_154230.json`

**Default Locations:**
- **Temporary files**: System temp directory + `artl-mcp/` (auto-cleanup)
- **Saved files**: `~/Documents/artl-mcp/` (persistent)
- **Custom location**: Set via `ARTL_OUTPUT_DIR` environment variable

### Email Configuration for Literature Access

ARTL-MCP requires institutional email addresses for certain literature APIs to comply with their terms of service and provide enhanced access to academic content. **This is mandatory for full-text retrieval and PDF discovery.**

#### When Email is Required vs Optional

**Email REQUIRED for:**
- **Full text retrieval** - Unpaywall API requires email for open access detection
- **PDF URL discovery** - DOIFetcher needs email for institutional access  
- **Enhanced metadata** - Some publishers require email for complete bibliographic data
- **Bulk downloads** - Rate limiting and fair use policies require identification

**Email NOT required for:**
- **Basic DOI metadata** - CrossRef API works without email
- **PubMed abstracts** - NCBI provides public access
- **Identifier conversions** - DOI ↔ PMID ↔ PMCID conversions
- **Basic literature searches** - PubMed search functionality
- **Citation analysis** - CrossRef citation data

#### How to Provide Your Email Address

**Method 1: Environment Variable (Persistent)**
```bash
# Add to your shell configuration (.bashrc, .zshrc, etc.)
export ARTL_EMAIL_ADDR="researcher@university.edu"

# Then restart Claude Desktop to pick up the new environment variable
```

**Method 2: Include in Your Request (Per-Session)**
Simply mention your email when making requests that need it:
```
"My email is researcher@university.edu. Please download the full text of PMC7523075."
```

**Method 3: MCP Client Configuration (Enhanced)**
ARTL-MCP's new ConfigManager system supports direct configuration injection from MCP clients:

- **Claude Desktop**: Uses system environment variables automatically
- **Goose Desktop**: Now supports configuration injection through the enhanced system
- **Other MCP clients**: Can inject configuration directly via the ConfigManager

**Configuration Priority System:**
1. **MCP Client Config** - Highest priority (injected by client)
2. **Environment Variables** - Medium priority (ARTL_EMAIL_ADDR)
3. **Local .env File** - Lowest priority (local/.env)

**Method 4: CLI Parameter (Command Line)**
```bash
# End users (uvx)
uvx --from artl-mcp artl-cli get-full-text-from-doi --doi "10.1038/nature12373" --email "researcher@university.edu"

# Developers (local installation)
uv run artl-cli get-full-text-from-doi --doi "10.1038/nature12373" --email "researcher@university.edu"
```

**Method 5: GitHub Actions/CI (Automated)**
```yaml
env:
  ARTL_EMAIL_ADDR: ${{ secrets.ARTL_EMAIL_ADDR }}
steps:
  - name: Test with email
    run: uvx --from artl-mcp artl-cli get-doi-metadata --doi "10.1038/nature12373"
```

#### Why Email Addresses are Required

Academic APIs require email addresses to:
- **Comply with publisher terms** - Many APIs mandate user identification
- **Enable fair use tracking** - Prevent abuse through rate limiting
- **Provide institutional access** - Some content requires academic affiliation
- **Support research integrity** - Maintain audit trails for academic use

**Important:**
- Use your **actual institutional email address** (university, research institute, or company) rather than personal email for best access to paywalled content
- **Do not use the examples literally** - Replace `researcher@university.edu` with your real email address
- The system validates emails and rejects common fake patterns (test@example.com, dummy@test.com, etc.)

### Best Practices for MCP Client Usage

1. **Start Simple**: Begin with basic queries like "Get metadata for DOI X" before complex multi-step requests
2. **Be Specific**: Include specific identifiers (DOI, PMID, PMCID) when possible for best results
3. **Check File Locations**: Always ask where files are saved for important downloads
4. **Configure Email Properly**: Use the enhanced configuration system for reliable email access:
   - **Claude Desktop**: Set environment variables normally
   - **Goose Desktop**: Use MCP client configuration injection
   - **Other clients**: Test configuration injection or use fallback methods
5. **Use Debug Mode**: Add `--debug --verbose` flags when troubleshooting or learning how tools work
6. **Batch Requests**: Combine related queries like "Get the abstract and find related papers for DOI X"
7. **Test Configuration**: Verify your email configuration works before starting research sessions

### Troubleshooting Claude Desktop Integration

**"No email address found" errors:**
```bash
export ARTL_EMAIL_ADDR="your@institution.edu"
# Restart Claude Desktop after setting environment variables
```

**Files not found in expected locations:**
- Check the temp directory: `/var/folders/.../artl-mcp/` (macOS) or `/tmp/artl-mcp/` (Linux)
- Files are auto-cleaned after some time unless `ARTL_KEEP_TEMP_FILES=true`

**MCP server not responding:**
- Verify MCP configuration in Claude Desktop settings
- Check that `uvx artl-mcp` works from command line
- Restart Claude Desktop application

#### MCP Client Configuration Issues

Different MCP clients handle environment variables and configuration differently. Here are known issues and solutions:

**Goose Desktop and Enhanced Configuration Support**

**✅ RESOLVED**: ARTL-MCP now includes enhanced configuration injection system

**New ConfigManager Features:**
- **Client Configuration Injection**: MCP clients can provide configuration directly
- **Priority System**: Client config → Environment variables → Local .env file
- **Automatic Integration**: All tools use the new configuration system

**Updated Configuration Methods:**

```json
// Claude Desktop - Environment variables (existing method)
{
  "mcpServers": {
    "artl-mcp": {
      "command": "uvx",
      "args": ["artl-mcp"],
      "env": {
        "ARTL_EMAIL_ADDR": "researcher@university.edu"
      }
    }
  }
}

// Goose Desktop or other clients - Configuration injection
{
  "mcpServers": {
    "artl-mcp": {
      "command": "uvx",
      "args": ["artl-mcp"],
      "config": {
        "ARTL_EMAIL_ADDR": "researcher@university.edu",
        "ARTL_OUTPUT_DIR": "/path/to/output"
      }
    }
  }
}
```

**For Developers/Advanced Users:**
The new system allows MCP clients to inject configuration via the ConfigManager:

```python
from artl_mcp.utils.config_manager import set_client_config

# Client initialization
client_config = {"ARTL_EMAIL_ADDR": "user@university.edu"}
set_client_config(client_config)
```

**Other MCP Clients**:
- **New**: Use configuration injection via ConfigManager system
- **Fallback**: Test environment variable support with your specific client  
- **Legacy**: Use CLI parameters or request-based email as fallbacks
- **Documentation**: Check client documentation for configuration injection methods

**Testing Your Configuration:**
Verify that your MCP client configuration is working:

```bash
# Test email configuration
uvx --from artl-mcp artl-cli get-doi-fetcher-metadata --doi "10.1038/nature12373"

# Expected behavior:
# ✅ Uses email from MCP client config (highest priority)
# ✅ Falls back to environment variable if no client config
# ✅ Falls back to local/.env file if no environment variable
# ❌ Clear error message if no email configured anywhere
```

## CLI Usage

The `artl-cli` command provides access to all functionality from the command line.

**Running CLI Commands:**

For direct usage without installation:
```bash
uvx --from artl-mcp artl-cli <command> [options]
```

For local development (after `uv sync`):
```bash
uv run artl-cli <command> [options]
```

**Note:** The package name is `artl-mcp`, but it provides the `artl-cli` command. When using `uvx`, you must specify `--from artl-mcp` to tell uvx which package to install.

### Basic Examples

**Get paper metadata:**

```bash
uvx --from artl-mcp artl-cli get-doi-metadata --doi "10.1038/nature12373"
uvx --from artl-mcp artl-cli get-abstract-from-pubmed-id --pmid "23851394"

# Or with local installation:
# uv run artl-cli get-doi-metadata --doi "10.1038/nature12373"
```

**Search for papers:**

```bash
# Basic keyword search
uvx --from artl-mcp artl-cli search-papers-by-keyword --query "CRISPR gene editing" --max-results 5

# Advanced search with filters
uvx --from artl-mcp artl-cli search-papers-by-keyword \
  --query "machine learning" \
  --max-results 20 \
  --sort "relevance" \
  --filter-type "journal-article" \
  --from-pub-date "2020-01-01"

# Recent papers (convenience function)
uvx --from artl-mcp artl-cli search-recent-papers --query "COVID-19" --years-back 2
```

**Identifier conversion:**

```bash
# Individual conversions
uvx --from artl-mcp artl-cli doi-to-pmid --doi "10.1038/nature12373"
uvx --from artl-mcp artl-cli pmid-to-doi --pmid "23851394"

# Get all available identifiers at once
uvx --from artl-mcp artl-cli get-all-identifiers --identifier "PMC3737249"
```

**Citation analysis:**

```bash
# Papers cited by this paper
uvx --from artl-mcp artl-cli get-paper-references --doi "10.1038/nature12373"

# Papers that cite this paper
uvx --from artl-mcp artl-cli get-paper-citations --doi "10.1038/nature12373"

# Comprehensive citation network
uvx --from artl-mcp artl-cli get-citation-network --doi "10.1038/nature12373"
```

**Full text access (requires email):**

```bash
uvx --from artl-mcp artl-cli get-full-text-from-doi \
  --doi "10.1038/nature12373" \
  --email "researcher@university.edu"

uvx --from artl-mcp artl-cli extract-pdf-text \
  --pdf-url "https://example.com/paper.pdf"
```

### File Saving Options

Most CLI commands support automatic file saving:

```bash
# Save with auto-generated filename
uvx --from artl-mcp artl-cli get-doi-metadata --doi "10.1038/nature12373" --save-file

# Save to specific path
uvx --from artl-mcp artl-cli search-papers-by-keyword \
  --query "CRISPR" \
  --save-to "crispr_papers.json"

# Save full text
uvx --from artl-mcp artl-cli get-full-text-from-doi \
  --doi "10.1038/nature12373" \
  --email "user@institution.edu" \
  --save-to "paper_fulltext.txt"
```

## Configuration

### Email Setup (Required for Some APIs)

Several APIs require institutional email addresses for rate limiting and access.

> **⚠️ Important:** Replace `researcher@university.edu` in all examples below with your actual institutional email address. Do not use the example emails literally - they will not work.

**Option 1: Environment Variable (Recommended)**

```bash
export ARTL_EMAIL_ADDR="researcher@university.edu"  # Replace with your real email
```

**Option 2: Local Configuration File**
Create `local/.env` file:

```
ARTL_EMAIL_ADDR=researcher@university.edu
```

**Option 3: CLI Parameter (Works with uvx)**

```bash
uvx --from artl-mcp artl-cli get-unpaywall-info \
  --doi "10.1038/nature12373" \
  --email "researcher@university.edu"
```

**Email Configuration with uvx:**

When using `uvx`, you have two main options for email configuration:

1. **CLI Parameter (Recommended for uvx):**
```bash
uvx --from artl-mcp artl-cli get-full-text-from-doi \
  --doi "10.1038/nature12373" \
  --email "researcher@university.edu"
```

2. **Environment Variable:**
```bash
export ARTL_EMAIL_ADDR="researcher@university.edu"
uvx --from artl-mcp artl-cli get-full-text-from-doi --doi "10.1038/nature12373"
```

**Note:** The local `.env` file (Option 2 above) only works when you have the package installed locally with `uv sync`. When using `uvx`, the tool runs in an isolated environment that doesn't have access to local configuration files.

### File Output Configuration

Configure where files are saved:

```bash
# Set custom output directory (default: ~/Documents/artl-mcp)
export ARTL_OUTPUT_DIR="~/Papers"

# Set temp directory (default: system temp + artl-mcp/)
export ARTL_TEMP_DIR="/tmp/my-artl-temp"  

# Keep temp files for debugging (default: false)
export ARTL_KEEP_TEMP_FILES=true
```

**Environment Variable Details:**

- **`ARTL_OUTPUT_DIR`** - Sets custom output directory for permanent files
  - Default: `~/Documents/artl-mcp`
  - Usage: Where saved files are permanently stored
  
- **`ARTL_TEMP_DIR`** - Sets custom temporary directory location  
  - Default: System temp directory + `/artl-mcp`
  - Usage: Where temporary files (PDFs, PMC texts) are stored during processing
  
- **`ARTL_KEEP_TEMP_FILES`** - Controls temporary file cleanup
  - Default: `false` (temp files are cleaned up automatically)
  - Values: `true`, `false`, `1`, `0`, `yes`, `no`, `on`, `off` (case-insensitive)
  - Usage: Set to `true` for debugging or to preserve downloaded files

**Note:** Additional development and testing environment variables are documented in [DEVELOPERS.md](DEVELOPERS.md#environment-variables).

## Identifier Formats

ARTL-MCP automatically recognizes and converts between multiple identifier formats:

### DOI (Digital Object Identifier)

- **Raw**: `10.1038/nature12373`
- **CURIE**: `doi:10.1038/nature12373`
- **URL**: `https://doi.org/10.1038/nature12373`
- **Legacy URL**: `http://dx.doi.org/10.1038/nature12373`

### PMID (PubMed ID)

- **Raw**: `23851394`
- **Prefixed**: `PMID:23851394`
- **Colon-separated**: `pmid:23851394`

### PMCID (PubMed Central ID)

- **Full**: `PMC3737249`
- **Numeric only**: `3737249`
- **Prefixed**: `PMC:3737249`

### Universal Identifier Handling

Use `get_all_identifiers` to get all available IDs for any identifier:

```bash
# Works with any format
uvx --from artl-mcp artl-cli get-all-identifiers --identifier "https://doi.org/10.1038/nature12373"
uvx --from artl-mcp artl-cli get-all-identifiers --identifier "PMID:23851394"
uvx --from artl-mcp artl-cli get-all-identifiers --identifier "PMC3737249"
```

## File Management

### Automatic File Saving

Many tools support automatic file saving with consistent options:

- **`--save-file`** - Save to output directory with auto-generated filename
- **`--save-to PATH`** - Save to specific path

### Save Path Reporting

When files are saved, tools now report exactly where the files were saved:

**MCP Tools Return:**
```json
{
  "data": { /* content */ },
  "saved_to": "/Users/researcher/Documents/artl-mcp/metadata_10.1038_nature12373.json"
}
```

**CLI Output:**
```bash
$ uvx --from artl-mcp artl-cli get-doi-metadata --doi "10.1038/nature12373" --save-file
File saved to: /Users/researcher/Documents/artl-mcp/metadata_10.1038_nature12373.json
```

### Memory Efficiency

For large files (>10MB), ARTL-MCP includes memory efficiency features:

- **Large content warnings** alert you when content exceeds memory thresholds
- **Streaming downloads** for PDF processing (where supported)
- **Chunked processing** to avoid loading entire large datasets into memory

### File Naming Convention

Auto-generated filenames follow this pattern:

```
{content_type}_{clean_identifier}_{timestamp}.{extension}
```

Examples:

- `metadata_10.1038_nature12373_20250724_152502.json`
- `fulltext_PMC1234567_20250724_153015.txt`
- `search_CRISPR_gene_editing_20250724_154230.json`

### Supported File Formats

| Content Type   | Default Format | Extensions      |
|----------------|----------------|-----------------|
| Metadata       | JSON           | `.json`         |
| Abstracts      | Text           | `.txt`          |
| Full text      | Text           | `.txt`          |
| Search results | JSON           | `.json`         |
| Citation data  | JSON           | `.json`, `.csv` |
| PDF content    | Binary         | `.pdf`          |

### Cross-Platform Safety

The system automatically sanitizes filenames for cross-platform compatibility:

- **Invalid characters** (`<>:"/\|?*`) → replaced with `_`
- **Reserved names** (Windows: `CON`, `PRN`, etc.) → prefixed with `_`
- **Length limits** → truncated while preserving extensions
- **Unicode support** → full UTF-8 support in content
- **Path handling** → Uses `pathlib.Path` for cross-platform operations
- **Directory creation** → Automatically creates output directories if needed

### Temp File Management

ARTL-MCP handles temporary files automatically:

- **PDF processing** creates temporary files for text extraction
- **Automatic cleanup** removes temp files after processing
- **Configurable retention** via `ARTL_KEEP_TEMP_FILES` environment variable

**Retention Policy:**

- `ARTL_KEEP_TEMP_FILES=false` (default) - Always delete temp files
- `ARTL_KEEP_TEMP_FILES=true` - Keep temp files for debugging

**Temp File Locations:**

- **Default**: System temp directory + `artl-mcp/`
- **Custom**: Set via `ARTL_TEMP_DIR` environment variable

## Citation Networks

ARTL-MCP provides comprehensive citation analysis through multiple data sources:

### Getting References (Papers Cited)

Find papers referenced by a given paper:

```bash
uvx --from artl-mcp artl-cli get-paper-references --doi "10.1038/nature12373"
```

Returns structured data including:

- Referenced paper DOIs and titles
- Authors and publication years
- Journal information
- Full citation text

### Getting Citations (Papers That Cite)

Find papers that cite a given paper:

```bash
uvx --from artl-mcp artl-cli get-paper-citations --doi "10.1038/nature12373"
```

Returns information about citing papers:

- DOIs and titles of citing papers
- Author lists and publication dates
- Citation counts and impact metrics

### Comprehensive Citation Analysis

Get data from multiple sources at once:

```bash
uvx --from artl-mcp artl-cli get-comprehensive-citation-info --doi "10.1038/nature12373"
```

Combines data from:

- **CrossRef**: Reference and citation data
- **OpenAlex**: Enhanced metadata and metrics
- **Semantic Scholar**: Additional citation context

### Finding Related Papers

Discover papers related through citation networks:

```bash
uvx --from artl-mcp artl-cli find-related-papers --doi "10.1038/nature12373" --max-results 10
```

## API Requirements

### Email Requirements by Function

Several APIs used by ARTL-MCP require email addresses for rate limiting identification, contact information, terms of
service compliance, and academic courtesy.

**Functions requiring email addresses:**

| Function                   | API Used             | Email Required | Purpose                     |
|----------------------------|----------------------|----------------|-----------------------------|
| `get_doi_fetcher_metadata` | CrossRef + Unpaywall | **YES**        | Enhanced metadata retrieval |
| `get_unpaywall_info`       | Unpaywall            | **YES**        | Open access information     |
| `get_full_text_from_doi`   | Multiple sources     | **YES**        | Full text retrieval         |
| `get_full_text_info`       | Multiple sources     | **YES**        | Text availability info      |
| `get_text_from_pdf_url`    | Unpaywall            | **YES**        | PDF text processing         |
| `download_pdf_from_doi`    | Unpaywall            | **YES**        | Direct PDF download via DOI |
| `clean_text`               | DOIFetcher           | **YES**        | Text cleaning utilities     |

**Functions NOT requiring email:**

- `get_doi_metadata` (basic CrossRef metadata)
- `get_abstract_from_pubmed_id` (PubMed abstracts)
- `search_papers_by_keyword` (CrossRef search)
- All identifier conversion functions
- `extract_pdf_text` (standalone PDF processing)

### Email Configuration Priority

The EmailManager looks for email addresses in this priority order:

1. **Direct parameter** - Email passed to function call
2. **`ARTL_EMAIL_ADDR` environment variable** - `export ARTL_EMAIL_ADDR=your@email.com`
3. **`local/.env` file** - `ARTL_EMAIL_ADDR=your@email.com`

### Email Validation Rules

The system validates email addresses and automatically rejects:

**Bogus Email Patterns:**

- `*@example.com` - Test domain
- `*test*@*` - Contains "test"
- `*dummy*@*` - Contains "dummy"
- `*fake*@*` - Contains "fake"
- `*placeholder*@*` - Contains "placeholder"
- `*invalid*@*` - Contains "invalid"
- `*noreply*@*` - No-reply addresses
- `*no-reply*@*` - No-reply addresses

**API-Specific Requirements:**

- **Unpaywall/CrossRef**: Prefer institutional emails (`.edu`, `.org`, `.gov`)
- **All APIs**: Must be valid email format (`user@domain.com`)

### Rate Limiting and Best Practices

When using APIs:

- **Use real institutional emails** when possible
- **Respect rate limits** (typically 1000 requests/hour per email)
- **Don't share email addresses** across different users/systems
- **Cache results** to minimize API calls
- APIs have built-in timeout and retry logic

### Current Known Issues

**High Priority Fixes Needed:**

1. **`pubmed_utils.py` uses bogus emails** - Functions use `"pubmed_utils@example.com"`
2. **Test files use bogus emails** - Multiple test files use `"test@example.com"`
3. **MCP tools don't expose email requirements** - Should indicate when email is needed

## Troubleshooting

### Common Issues

**"Bogus email address not allowed"**

- You're using a test/fake email address
- Set a real email via `ARTL_EMAIL_ADDR` environment variable

**"No valid email address found"**

- No email configured in environment or .env file
- Set `ARTL_EMAIL_ADDR=your@email.com` in environment or `local/.env`

**"Invalid identifier format"**

- Identifier doesn't match expected formats
- Use `validate_identifier` to check format
- Check for typos in identifier

**"API timeout" or "Connection error"**

- Network or server issues
- Retry operation after a moment
- Check internet connection

**"Conversion returned None"**

- No mapping exists between identifier types
- Not all papers have all identifier types
- Check if paper is indexed in target database

**Permission denied (file saving)**

- Insufficient write permissions for output directory
- Check directory permissions or change `ARTL_OUTPUT_DIR`

**"File not found" or "Directory doesn't exist"**

- Output directory doesn't exist
- ARTL-MCP automatically creates directories, but parent directories must exist

### Getting Help

1. **Check the documentation**: Review this guide and other markdown files
2. **Validate your inputs**: Use `validate_identifier` to check formats
3. **Test with known good identifiers**: Try with `10.1038/nature12373` or `23851394`
4. **Check your configuration**: Verify email and directory settings
5. **Submit issues**: Report bugs at the GitHub repository

### Performance Tips

1. **Use comprehensive functions**: `get_all_identifiers` instead of multiple individual conversions
2. **Cache results**: Save frequently-used data to avoid repeat API calls
3. **Use appropriate search limits**: Set reasonable `--max-results` for searches
4. **Configure file saving**: Set `ARTL_OUTPUT_DIR` to organize saved files
5. **Use fast tests during development**: Skip external API calls when developing

### Best Practices

1. **Always validate identifiers** before expensive operations
2. **Use institutional email addresses** for better API access
3. **Save important results to files** for offline access
4. **Organize output directories** by project or topic
5. **Respect API rate limits** and terms of service
6. **Handle multiple identifier formats** gracefully in your workflows