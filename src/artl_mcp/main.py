import asyncio
import sys
from importlib import metadata

import click
from fastmcp import FastMCP

from artl_mcp.client import run_client
from artl_mcp.tools import (
    get_all_identifiers_from_europepmc as _get_all_identifiers_from_europepmc,
)
from artl_mcp.tools import (
    get_europepmc_full_text as _get_europepmc_full_text,
)
from artl_mcp.tools import (
    get_europepmc_paper_by_id as _get_europepmc_paper_by_id,
)
from artl_mcp.tools import (
    get_europepmc_pdf as _get_europepmc_pdf,
)
from artl_mcp.tools import (
    get_europepmc_pdf_as_markdown as _get_europepmc_pdf_as_markdown,
)
from artl_mcp.tools import (
    search_europepmc_papers as _search_europepmc_papers,
)
from artl_mcp.tools import (
    search_pubmed_for_pmids,
)
from artl_mcp.utils.pubmed_utils import get_pmc_supplemental_material

try:
    __version__ = metadata.version("artl-mcp")
except metadata.PackageNotFoundError:
    __version__ = "unknown"


# MCP wrapper functions that disable file saving
def search_europepmc_papers(
    keywords: str, max_results: int = 10, result_type: str = "lite"
):
    """
    Search Europe PMC for papers without saving results to a file.

    This function wraps the `_search_europepmc_papers` function and disables
    file saving. It retrieves metadata about papers matching the given keywords.

    Args:
        keywords (str): The search query string containing keywords to look for.
        max_results (int, optional): The maximum number of results to return.
            Defaults to 10.
        result_type (str, optional): The type of results to retrieve.
            Options include "lite" (basic metadata)
            and "core" (detailed metadata). Defaults to "lite".

    Returns:
        list[dict]: A list of dictionaries, where each dictionary contains metadata
        about a paper matching the search query.

    Example:
        >>> results = search_europepmc_papers("machine learning", max_results=5)
        >>> for paper in results:
        ...     print(paper["title"])
    """
    return _search_europepmc_papers(
        keywords=keywords,
        max_results=max_results,
        result_type=result_type,
        save_file=False,
        save_to=None,
    )


def get_europepmc_paper_by_id(identifier: str):
    """MCP wrapper - Get Europe PMC paper metadata without file saving."""
    return _get_europepmc_paper_by_id(
        identifier=identifier,
        save_file=False,
        save_to=None,
    )


def get_all_identifiers_from_europepmc(identifier: str):
    """MCP wrapper - Get all identifiers without file saving."""
    return _get_all_identifiers_from_europepmc(
        identifier=identifier,
        save_file=False,
        save_to=None,
    )


def get_europepmc_full_text(identifier: str, offset: int = 0, limit: int | None = None):
    """MCP wrapper - Get full text without file saving."""
    return _get_europepmc_full_text(
        identifier=identifier,
        save_file=False,
        save_to=None,
        offset=offset,
        limit=limit,
    )


def get_europepmc_pdf(identifier: str):
    """MCP wrapper - Get PDF info without downloading/saving."""
    # For MCP, we get the PDF info but don't actually download
    result = _get_europepmc_pdf(
        identifier=identifier,
        save_to=None,
        filename=None,
    )

    # Remove any file paths from the result since we're not saving
    if result and "saved_to" in result:
        result = result.copy()  # Create a shallow copy before modifying
        result["saved_to"] = None
        # Add a note that this is MCP mode
        result["mcp_mode"] = True
        result["note"] = "PDF not downloaded in MCP mode - use CLI for file saving"

    return result


def get_europepmc_pdf_as_markdown(
    identifier: str,
    extract_tables: bool = True,
    processing_method: str = "auto",
    offset: int = 0,
    limit: int | None = None,
):
    """MCP wrapper - Convert PDF to Markdown without file saving."""
    return _get_europepmc_pdf_as_markdown(
        identifier=identifier,
        save_file=False,
        save_to=None,
        extract_tables=extract_tables,
        processing_method=processing_method,
        offset=offset,
        limit=limit,
    )


def create_mcp():
    """Create the FastMCP server instance and register tools."""
    mcp = FastMCP(
        "artl-mcp",
        instructions="""
Europe PMC Literature Discovery and ID Translation Tools

This MCP server provides SIX TOOLS for scientific literature discovery and
identifier translation using Europe PMC exclusively. No NCBI/PubMed APIs are accessed.

## Tool Selection Guide

**For KEYWORD SEARCHES** → Use `search_europepmc_papers`
**For FULL METADATA from identifier** → Use `get_europepmc_paper_by_id`
**For ID TRANSLATION/LINKS** → Use `get_all_identifiers_from_europepmc`
**For FULL TEXT CONTENT** → Use `get_europepmc_full_text`
**For PDF DOWNLOAD** → Use `get_europepmc_pdf`
**For PDF-TO-MARKDOWN CONVERSION** → Use `get_europepmc_pdf_as_markdown`

## Available Tools

**1. search_europepmc_papers** - Search Europe PMC for papers by keywords
- **INPUT**: Keywords/search terms
- **OUTPUT**: Multiple papers with metadata and identifiers
- Use this for: Literature discovery, topic research, finding papers on subjects

**2. get_europepmc_paper_by_id** - Get complete paper metadata from any identifier
- **INPUT**: ONE specific identifier (DOI, PMID, or PMCID)
- **OUTPUT**: Complete metadata including abstract, keywords, authors
- Use this for: Getting full details about a specific paper you already have an ID for

**3. get_all_identifiers_from_europepmc** - Get all available IDs and links for a paper
- **INPUT**: ONE specific identifier (DOI, PMID, or PMCID)
- **OUTPUT**: All available identifiers + direct URLs + access status
- Use this for: ID translation (DOI→PMID), finding all access points, link generation

**4. get_europepmc_full_text** - Get LLM-friendly full text content in Markdown
- **INPUT**: ONE specific identifier (DOI, PMID, or PMCID)
- **OUTPUT**: Clean Markdown with preserved structure, tables, and figures
- Use this for: Getting complete paper content for LLM analysis

**5. get_europepmc_pdf** - Get PDF metadata from Europe PMC (MCP mode without download)
- **INPUT**: ONE specific identifier (DOI, PMID, or PMCID)
- **OUTPUT**: PDF availability info and metadata (no file download in MCP mode)
- **PDF AVAILABILITY**: Only works if paper has PDFs available in Europe PMC
  (most successful with PMC papers)
- Use this for: Checking PDF availability and getting metadata (without download)

**6. get_europepmc_pdf_as_markdown** - Convert Europe PMC PDF to Markdown in-memory
- **INPUT**: ONE specific identifier (DOI, PMID, or PMCID)
- **OUTPUT**: PDF converted to structured Markdown with tables preserved
- **PDF AVAILABILITY**: Only works if paper has PDFs available in Europe PMC
  (most successful with PMC papers)
- Use this for: Getting PDF content as LLM-friendly Markdown without disk I/O

Key Features:
- Automatic identifier detection and normalization
- Comprehensive Europe PMC metadata retrieval
- Direct URL generation for all databases (PubMed, PMC, DOI, Europe PMC)
- Access status checking (open access, PDF availability)
- MCP mode: Returns data without file saving (use CLI for file operations)
- Exclusive Europe PMC usage - no NCBI API dependencies

Perfect for:
- Literature discovery and analysis
- Identifier translation and cross-referencing
- Finding all access points for papers
- Building comprehensive literature databases
- Research requiring detailed paper metadata

Example usage:
```
# Search for papers
search_europepmc_papers(
    keywords="CRISPR gene editing", max_results=10, result_type="core"
)

# Get full metadata from any identifier
get_europepmc_paper_by_id("10.1038/nature12373")
get_europepmc_paper_by_id("23851394")  # PMID
get_europepmc_paper_by_id("PMC3737249")  # PMCID

# Get all identifiers and links
get_all_identifiers_from_europepmc("10.1038/nature12373")

# Get full text content as Markdown (MCP mode - no file saving)
get_europepmc_full_text("10.1038/nature12373")
get_europepmc_full_text("PMC3737249")

# Get PDF metadata (MCP mode - no file download)
get_europepmc_pdf("10.1038/nature12373")
get_europepmc_pdf("PMC3737249")

# Convert PDF to Markdown in-memory (MCP mode - no file saving)
get_europepmc_pdf_as_markdown("10.1038/nature12373")
get_europepmc_pdf_as_markdown("PMC3737249", processing_method="auto")
```

The above tools exclusively use Europe PMC and will never attempt to contact
NCBI/PubMed APIs.

The following tools rely on an NCBI API:

# Retrieve Supplemental Material as text from a PubMed Central Open Access
# article via it's PubMed Central ID:
get_pmc_supplemental_material("PMC7294781", 1)
get_pmc_supplemental_material("PMC:7294781", 1)

""",
    )

    # Register only Europe PMC search tool
    # All other tools commented out to avoid NCBI API calls

    # # Original tools
    # mcp.tool(get_doi_metadata)
    # mcp.tool(get_abstract_from_pubmed_id)

    # # DOIFetcher-based tools (require email)
    # mcp.tool(get_doi_fetcher_metadata)
    # mcp.tool(get_unpaywall_info)
    # mcp.tool(get_full_text_from_doi)
    # mcp.tool(get_full_text_info)
    # mcp.tool(get_text_from_pdf_url)
    # mcp.tool(clean_text)

    # # PDF download tools
    # mcp.tool(download_pdf_from_doi)
    # mcp.tool(download_pdf_from_url)

    # # Standalone tools
    # mcp.tool(extract_pdf_text)

    # # PubMed utilities tools
    # mcp.tool(extract_doi_from_url)
    # mcp.tool(doi_to_pmid)
    # mcp.tool(pmid_to_doi)
    # mcp.tool(get_doi_text)
    # mcp.tool(get_pmid_from_pmcid)
    # mcp.tool(get_pmcid_text)
    # mcp.tool(get_pmid_text)
    # mcp.tool(get_full_text_from_bioc)
    # mcp.tool(search_pubmed_for_pmids)

    # # Enhanced identifier conversion tools
    # mcp.tool(convert_identifier_format)
    # mcp.tool(doi_to_pmcid)
    # mcp.tool(pmid_to_pmcid)
    # mcp.tool(pmcid_to_doi)
    # mcp.tool(get_all_identifiers)
    # mcp.tool(validate_identifier)

    # # Citation and reference tools
    # mcp.tool(get_paper_references)
    # mcp.tool(get_paper_citations)
    # mcp.tool(get_citation_network)
    # mcp.tool(find_related_papers)
    # mcp.tool(get_comprehensive_citation_info)

    # Europe PMC tools - Search and ID translation
    mcp.tool(search_europepmc_papers)  # Europe PMC search tool
    mcp.tool(get_europepmc_paper_by_id)  # Get full metadata from any ID
    mcp.tool(get_all_identifiers_from_europepmc)  # Get all IDs and links
    mcp.tool(get_europepmc_full_text)  # Get full text content as Markdown
    mcp.tool(get_europepmc_pdf)  # Download PDF files from Europe PMC
    mcp.tool(get_europepmc_pdf_as_markdown)  # Convert PDF to Markdown in-memory

    # Other tools commented out to avoid NCBI API calls
    # mcp.tool(search_papers_by_keyword)
    # mcp.tool(search_recent_papers)
    # The PubMed Central Supplemental Material API supports retrieval as text
    # (more immediately useful than Europe PMC which uses binary files).
    mcp.tool(get_pmc_supplemental_material)

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
