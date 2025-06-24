import asyncio

import click
from fastmcp import FastMCP

from artl_mcp.client import run_client
from artl_mcp.tools import get_doi_metadata


def create_mcp():
    """Create the FastMCP server instance and register tools."""
    mcp = FastMCP("all-roads-to-literature")
    mcp.tool(get_doi_metadata)
    return mcp


# Server instance
mcp = create_mcp()


@click.command()
@click.option("--server", is_flag=True, help="Start the MCP server.")
@click.option("--doi-query", type=str, help="Run a direct query (DOI string).")
def cli(server, doi_query):
    """Run All Roads to Literature MCP tool or server."""
    if server:
        # Run the server over stdio
        mcp.run()
    elif doi_query:
        # Run the client in asyncio
        asyncio.run(run_client(doi_query, mcp))
    else:
        click.echo(cli.get_help(click.Context(cli)))


if __name__ == "__main__":
    cli()
