import pytest
from fastmcp import Client

from artl_mcp.main import create_mcp


@pytest.mark.external_api
@pytest.mark.slow
@pytest.mark.asyncio
async def test_search_europepmc_papers_contains_content():
    # Create MCP server instance
    mcp = create_mcp()

    # Use in-memory testing with FastMCP Client
    async with Client(mcp) as client:
        # Call the Europe PMC search tool through MCP protocol
        result = await client.call_tool(
            "search_europepmc_papers", {"keywords": "neuroblastoma", "max_results": 5}
        )

        # Extract text from TextContent object and check for expected keyword
        result_text = result.text if hasattr(result, "text") else str(result)
        assert "neuroblastoma" in result_text.lower() or "pmids" in result_text.lower()
