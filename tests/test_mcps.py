import pytest
from fastmcp import Client

from artl_mcp.main import create_mcp


@pytest.mark.asyncio
async def test_get_doi_metadata_contains_neuroblastoma():
    # Create MCP server instance
    mcp = create_mcp()

    # Use in-memory testing with FastMCP Client
    async with Client(mcp) as client:
        # Call the DOI metadata tool through MCP protocol
        result = await client.call_tool(
            "get_doi_metadata", {"doi": "10.1038/nature12373"}
        )

        # Extract text from TextContent object and check for expected keyword
        result_text = result.text if hasattr(result, "text") else str(result)
        assert "neuroblastoma" in result_text.lower()
