from fastmcp import Client


async def run_client(doi: str, mcp):
    """Call the MCP tool using an in-memory client connection."""
    async with Client(mcp) as client:
        result = await client.call_tool("get_doi_metadata", {"doi": doi})

        for item in result:
            print(item.model_dump_json(indent=2))
