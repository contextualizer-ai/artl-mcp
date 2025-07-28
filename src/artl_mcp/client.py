import json

from fastmcp import Client


async def run_client(doi: str, mcp):
    """Call the MCP tool using an in-memory client connection."""
    async with Client(mcp) as client:
        # Search for papers using the DOI as a keyword
        # This will find the specific paper in Europe PMC
        result = await client.call_tool(
            "search_europepmc_papers", {"keywords": doi, "max_results": 5}
        )

        for item in result:
            # If item has text field containing JSON, pretty print that directly
            if hasattr(item, "text") and item.text:
                try:
                    data = json.loads(item.text)
                    print(json.dumps(data, indent=2))
                except json.JSONDecodeError:
                    print(item.text)
            else:
                print(item.model_dump_json(indent=2))
