# All Roads to Literature

An MCP (Model Context Protocol) server for retrieving scientific literature metadata and content using PMIDs, DOIs, and other identifiers.

## Quick Start (MCP Client Configuration)

To use this MCP server with your Claude Desktop, add this configuration:

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

## Features

- Retrieve metadata for scientific articles using DOIs
- Fetch abstracts from PubMed using PMIDs  
- Search papers by keywords or recent publications
- Extract full text from various sources (PMC, Unpaywall, etc.)
- Convert between identifiers (DOI ↔ PMID, PMCID)
- Clean and process PDF text content

## Available Tools

Once configured, you'll have access to these tools in your MCP client:

- `get_abstract_from_pubmed_id` - Get abstract text from PubMed ID
- `get_doi_metadata` - Retrieve metadata for a DOI
- `search_papers_by_keyword` - Search for papers by keyword
- `search_recent_papers` - Find recently published papers
- `get_full_text_from_doi` - Extract full text content from DOI
- `doi_to_pmid` / `pmid_to_doi` - Convert between identifier types

## Command Line Usage (Optional)

For testing or standalone use, you can also run the MCP server directly:

```bash
# Install and run artl-mcp
uvx artl-mcp --server

## Development Setup

For contributors who want to modify the code:

```bash
git clone https://github.com/contextualizer-ai/artl-mcp.git
cd artl-mcp
uv sync --dev
uv run pytest tests/
```
