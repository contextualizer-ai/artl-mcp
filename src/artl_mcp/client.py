import json

from fastmcp import Client


async def run_client(query: str, mcp):
    """Call the MCP tool using an in-memory client connection."""
    async with Client(mcp) as client:
        # Search for papers using the query as keywords
        # This can be research keywords, DOI, or other search terms
        result = await client.call_tool(
            "search_europepmc_papers", {"keywords": query, "max_results": 5}
        )

        # CallToolResult returns a single object, not a list
        # Extract text from the result
        text = None

        # Try real API structure first: content[0].text
        if hasattr(result, "content") and result.content:
            try:
                # Real API returns content as list of TextContent objects
                if isinstance(result.content, list) and len(result.content) > 0:
                    if hasattr(result.content[0], "text"):
                        text = result.content[0].text
            except (TypeError, IndexError):
                pass

        # Try mock/test structure: text directly on result
        if text is None and hasattr(result, "text"):
            text = result.text

        # Print the extracted text
        if text:
            try:
                data = json.loads(text)
                print(json.dumps(data, indent=2))
            except json.JSONDecodeError:
                print(text)
        else:
            # Fallback to model_dump_json if available, otherwise str()
            if hasattr(result, "model_dump_json"):
                print(result.model_dump_json(indent=2))
            else:
                print(str(result))
