import asyncio
import sys
from importlib import metadata

import click
from fastmcp import FastMCP

from artl_mcp.client import run_client
from artl_mcp.tools import (
    search_europepmc_papers,
    # Search tools
    search_pubmed_for_pmids,
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
Europe PMC Paper Search - Focused Literature Discovery Tool

This MCP server provides ONE TOOL for searching scientific literature using Europe PMC.
No NCBI/PubMed APIs are accessed - only Europe PMC.

## Available Tool

**search_europepmc_papers** - Search Europe PMC and get comprehensive paper information

What it does:
1. Searches Europe PMC database with your keywords
2. Returns PMIDs, PMCIDs, DOIs for found papers
3. Provides direct links (PubMed, PMC, DOI URLs)
4. Indicates full text and PDF availability
5. Shows open access status

Parameters:
- `keywords`: Search terms (e.g., "rhizosphere microbiome", "CRISPR gene editing")
- `max_results`: Number of papers to return (default: 10, max: 100)

Returns comprehensive paper information including:
- Identifiers: PMIDs, PMCIDs, DOIs
- Metadata: title, authors, journal, publication year
- Links: Direct URLs to PubMed, PMC, DOI
- Availability: full text, PDF, open access status

Perfect for:
- Finding papers on specific topics
- Getting direct links to papers and PDFs
- Checking open access availability
- Literature discovery without NCBI dependencies

Example usage:
```
search_europepmc_papers(keywords="rhizosphere microbiome", max_results=5)
```

This tool exclusively uses Europe PMC and will never attempt to contact
NCBI/PubMed APIs.

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

    # Search tools - ONLY Europe PMC search enabled
    mcp.tool(search_europepmc_papers)  # Europe PMC search tool
    # mcp.tool(search_papers_by_keyword)
    # mcp.tool(search_recent_papers)

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
