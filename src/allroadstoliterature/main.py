import pprint
from typing import Dict, Any, Optional

import click
from fastmcp import FastMCP

from src.allroadstoliterature.tools import get_doi_metadata


def create_mcp():
    """Create the FastMCP instance with registered tools."""
    mcp = FastMCP("all-roads-to-literature")

    # Register all tools
    mcp.tool(get_doi_metadata)

    return mcp


# Create the FastMCP instance at module level
mcp = create_mcp()


def main():
    """Main entry point for the application."""
    mcp.run()


if __name__ == "__main__":
    main()
