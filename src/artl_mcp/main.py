import asyncio

import click
from fastmcp import FastMCP

from artl_mcp.client import run_client
from artl_mcp.tools import (
    clean_text,
    doi_to_pmid,
    # PubMed utilities tools
    extract_doi_from_url,
    extract_pdf_text,
    get_abstract_from_pubmed_id,
    # DOIFetcher-based tools
    get_doi_fetcher_metadata,
    # Original tools
    get_doi_metadata,
    get_doi_text,
    get_full_text_from_bioc,
    get_full_text_from_doi,
    get_full_text_info,
    get_pmcid_text,
    get_pmid_from_pmcid,
    get_pmid_text,
    get_text_from_pdf_url,
    get_unpaywall_info,
    pmid_to_doi,
    # Search tools
    search_papers_by_keyword,
    search_pubmed_for_pmids,
    search_recent_papers,
)


def create_mcp():
    """Create the FastMCP server instance and register tools."""
    mcp = FastMCP("all-roads-to-literature")

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

    # Search tools
    mcp.tool(search_papers_by_keyword)
    mcp.tool(search_recent_papers)

    return mcp


# Server instance
mcp = create_mcp()


@click.command()
@click.option("--server", is_flag=True, help="Start the MCP server.")
@click.option("--doi-query", type=str, help="Run a direct query (DOI string).")
@click.option("--pmid-search", type=str, help="Search PubMed for PMIDs using keywords.")
@click.option(
    "--max-results",
    type=int,
    default=20,
    help="Maximum number of results to return (default: 20).",
)
def cli(server, doi_query, pmid_search, max_results):
    """Run All Roads to Literature MCP tool or server."""
    if server:
        # Run the server over stdio
        mcp.run()
    elif doi_query:
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
        click.echo(cli.get_help(click.Context(cli)))


if __name__ == "__main__":
    cli()
