import asyncio
import sys
from importlib import metadata

import click
from fastmcp import FastMCP

from artl_mcp.client import run_client
from artl_mcp.tools import (
    clean_text,
    convert_identifier_format,
    # Enhanced identifier conversion tools
    doi_to_pmcid,
    doi_to_pmid,
    # PubMed utilities tools
    extract_doi_from_url,
    extract_pdf_text,
    find_related_papers,
    get_abstract_from_pubmed_id,
    get_all_identifiers,
    get_citation_network,
    get_comprehensive_citation_info,
    # DOIFetcher-based tools
    get_doi_fetcher_metadata,
    # Original tools
    get_doi_metadata,
    get_doi_text,
    get_full_text_from_bioc,
    get_full_text_from_doi,
    get_full_text_info,
    get_paper_citations,
    # Citation and reference tools
    get_paper_references,
    get_pmcid_text,
    get_pmid_from_pmcid,
    get_pmid_text,
    get_text_from_pdf_url,
    get_unpaywall_info,
    pmcid_to_doi,
    pmid_to_doi,
    pmid_to_pmcid,
    # Search tools
    search_papers_by_keyword,
    search_pubmed_for_pmids,
    search_recent_papers,
    validate_identifier,
)

try:
    __version__ = metadata.version("artl-mcp")
except metadata.PackageNotFoundError:
    __version__ = "unknown"


def create_mcp():
    """Create the FastMCP server instance and register tools."""
    mcp = FastMCP(
        "artl-mcp",
        instructions="""
All Roads to Literature (ARtL) MCP provides comprehensive tools for retrieving
scientific literature metadata, full text, abstracts, and citation networks via
DOI, PMID, or PMCID.

## 🗂️ COMPREHENSIVE FILE SAVING CAPABILITIES

**IMPORTANT**: Most tools support automatic file saving with two options:
- **`save_file: true`** - Auto-saves to temp directory with generated filename
- **`save_to: "path/file.ext"`** - Saves to your specified path (overrides save_file)

**Supported file formats**: JSON (metadata), TXT (full text), PDF, XML, YAML, CSV
**Cross-platform paths**: Works on Windows, macOS, and Linux
**Environment configuration**:
- `ARTL_OUTPUT_DIR` - Custom output directory
- `ARTL_TEMP_DIR` - Custom temp directory
- `ARTL_KEEP_TEMP_FILES` - Retention policy

## Supported Identifier Formats
- **DOI**: Multiple formats supported
  - Raw: 10.1038/nature12373
  - CURIE: doi:10.1038/nature12373
  - URLs: https://doi.org/10.1038/nature12373, http://dx.doi.org/...
- **PMID**: Multiple formats supported
  - Raw: 23851394
  - Prefixed: PMID:23851394
  - Colon-separated: pmid:23851394
- **PMCID**: Multiple formats supported
  - Full: PMC3737249
  - Numeric: 3737249
  - Prefixed: PMC:3737249
- **Keywords**: Natural language search terms

This server offers five main categories of functionality:

## 1. Literature Search and Discovery
- **search_papers_by_keyword** 📁: Search article metadata via keywords
- **search_recent_papers** 📁: Find recent publications for specific keywords or topics
- **search_pubmed_for_pmids** 📁: Search PubMed for articles using keywords and return
PMIDs with metadata

## 2. Metadata and Abstract Retrieval
- **get_doi_metadata** 📁: Get comprehensive metadata for papers using DOI
- **get_abstract_from_pubmed_id** 📁: Retrieve abstracts from PubMed using PMID
- **get_doi_fetcher_metadata** 📁: Enhanced metadata retrieval with email requirement
- **get_unpaywall_info** 📁: Check open access availability via Unpaywall

## 3. Full Text Access and Processing
- **get_full_text_from_doi** 📁: Retrieve full text content using DOI (requires email)
- **get_full_text_info** 📁: Get detailed full text availability information
- **get_text_from_pdf_url** 📁: Extract text content from PDF URLs
- **extract_pdf_text** 📁: Standalone PDF text extraction
- **get_pmcid_text** 📁: Get full text from PubMed Central ID
- **get_pmid_text** 📁: Get full text using PMID
- **get_full_text_from_bioc** 📁: Retrieve full text in BioC format
- **get_doi_text** 📁: Direct text retrieval using DOI
- **clean_text** 📁: Clean and format extracted text content

## 4. Identifier Conversion and Utilities
- **extract_doi_from_url**: Extract DOI from various URL formats
- **convert_identifier_format** 📁: Convert between ID formats (raw, CURIE, URL)
- **doi_to_pmid**: Convert DOI to PMID
- **doi_to_pmcid**: Convert DOI to PMCID
- **pmid_to_doi**: Convert PMID to DOI
- **pmid_to_pmcid**: Convert PMID to PMCID
- **pmcid_to_doi**: Convert PMCID to DOI
- **get_pmid_from_pmcid**: Get PMID from PMC ID
- **get_all_identifiers** 📁: Get all available IDs for any identifier
- **validate_identifier**: Validate identifier format

## 5. Citation Networks and Related Papers
- **get_paper_references** 📁: Get papers cited by a given paper
- **get_paper_citations** 📁: Get papers that cite a given paper
- **get_citation_network** 📁: Get comprehensive citation network from OpenAlex
- **find_related_papers** 📁: Find papers related through citations
- **get_comprehensive_citation_info** 📁: Get citation data from multiple sources

**📁 = Supports file saving with `save_file` and `save_to` parameters**

## Usage Notes
- **Identifier Flexibility**: All tools accept multiple identifier formats and
  auto-normalize
- **Format Interconversion**: Use convert_identifier_format to convert between
  DOI CURIEs (doi:10.1234/example), DOI URLs (https://doi.org/10.1234/example),
  and raw formats (10.1234/example)
- **Email Requirements**: Many tools require email addresses for API access
  (CrossRef, Unpaywall)
- **Format Consistency**: All tools return identifiers in standardized formats
- **Error Handling**: Graceful handling of invalid identifiers and API failures
- **Rate Limiting**: Proper headers and timeouts for respectful API usage
- **Comprehensive Coverage**: Support for DOI, PMID, PMCID conversion in all directions

""",
    )

    # Register all tools
    # Original tools
    mcp.tool(get_doi_metadata)
    mcp.tool(get_abstract_from_pubmed_id)

    # DOIFetcher-based tools (require email)
    mcp.tool(get_doi_fetcher_metadata)
    mcp.tool(get_unpaywall_info)
    mcp.tool(get_full_text_from_doi)
    mcp.tool(get_full_text_info)
    mcp.tool(get_text_from_pdf_url)
    mcp.tool(clean_text)

    # Standalone tools
    mcp.tool(extract_pdf_text)

    # PubMed utilities tools
    mcp.tool(extract_doi_from_url)
    mcp.tool(doi_to_pmid)
    mcp.tool(pmid_to_doi)
    mcp.tool(get_doi_text)
    mcp.tool(get_pmid_from_pmcid)
    mcp.tool(get_pmcid_text)
    mcp.tool(get_pmid_text)
    mcp.tool(get_full_text_from_bioc)
    mcp.tool(search_pubmed_for_pmids)

    # Enhanced identifier conversion tools
    mcp.tool(convert_identifier_format)
    mcp.tool(doi_to_pmcid)
    mcp.tool(pmid_to_pmcid)
    mcp.tool(pmcid_to_doi)
    mcp.tool(get_all_identifiers)
    mcp.tool(validate_identifier)

    # Citation and reference tools
    mcp.tool(get_paper_references)
    mcp.tool(get_paper_citations)
    mcp.tool(get_citation_network)
    mcp.tool(find_related_papers)
    mcp.tool(get_comprehensive_citation_info)

    # Search tools
    mcp.tool(search_papers_by_keyword)
    mcp.tool(search_recent_papers)

    return mcp


# Server instance
mcp = create_mcp()


@click.command()
@click.option("--doi-query", type=str, help="Run a direct query (DOI string).")
@click.option("--pmid-search", type=str, help="Search PubMed for PMIDs using keywords.")
@click.option(
    "--max-results",
    type=int,
    default=20,
    help="Maximum number of results to return (default: 20).",
)
def cli(doi_query, pmid_search, max_results):
    """
    Run All Roads to Literature MCP server (default) or CLI tools.

    CLI Options:
        --doi-query: Run a direct query using a DOI string.
        --pmid-search: Search PubMed for PMIDs using keywords.
        --max-results: Maximum number of results to return (default: 20).

    Default Behavior:
        If no options are provided, the MCP server runs over stdio.
    """
    # Validate mutual exclusion of CLI options
    if doi_query and pmid_search:
        raise click.ClickException(
            "Error: Cannot use both --doi-query and --pmid-search simultaneously. "
            "Please use only one option at a time."
        )

    if doi_query:
        # Run the client in asyncio
        asyncio.run(run_client(doi_query, mcp))
    elif pmid_search:
        # Run PubMed search directly
        result = search_pubmed_for_pmids(pmid_search, max_results)
        if result and result["pmids"]:
            print(
                f"Found {result['returned_count']} PMIDs out of "
                f"{result['total_count']} total results for query '{pmid_search}':"
            )
            for pmid in result["pmids"]:
                print(f"  {pmid}")
            if result["total_count"] > result["returned_count"]:
                max_possible = min(result["total_count"], 100)
                print(f"\nTo get more results, use: --max-results {max_possible}")
        elif result:
            print(f"No PMIDs found for query '{pmid_search}'")
        else:
            print(f"Error searching for query '{pmid_search}'")
    else:
        # Default behavior: Run the MCP server over stdio
        mcp.run()


def main():
    """Main entry point for the application."""
    if "--version" in sys.argv:
        print(__version__)
        sys.exit(0)
    cli()


if __name__ == "__main__":
    main()
