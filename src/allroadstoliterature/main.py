import asyncio
import click
from fastmcp import FastMCP

from allroadstoliterature.client import run_client
from allroadstoliterature.tools import get_doi_metadata, search_pubmed_for_pmids


def create_mcp():
    """Create the FastMCP server instance and register tools."""
    mcp = FastMCP("all-roads-to-literature")
    mcp.tool(get_doi_metadata)
    mcp.tool(search_pubmed_for_pmids)
    return mcp


# Server instance
mcp = create_mcp()


@click.command()
@click.option("--server", is_flag=True, help="Start the MCP server.")
@click.option("--doi-query", type=str, help="Run a direct query (DOI string).")
@click.option("--pmid-search", type=str, help="Search PubMed for PMIDs using keywords.")
@click.option("--max-results", type=int, default=20, help="Maximum number of results to return (default: 20).")
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
            print(f"Found {result['returned_count']} PMIDs out of {result['total_count']} total results for query '{pmid_search}':")
            for pmid in result["pmids"]:
                print(f"  {pmid}")
            if result["total_count"] > result["returned_count"]:
                print(f"\nTo get more results, use: --max-results {min(result['total_count'], 100)}")
        elif result:
            print(f"No PMIDs found for query '{pmid_search}'")
        else:
            print(f"Error searching for query '{pmid_search}'")
    else:
        click.echo(cli.get_help(click.Context(cli)))


if __name__ == "__main__":
    cli()
