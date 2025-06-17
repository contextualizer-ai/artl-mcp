import asyncio
from fastmcp import Client
from fastmcp.client.transports import PythonStdioTransport


async def main():
    # Use explicit transport for better control
    transport = PythonStdioTransport(
        script_path="src/allroadstoliterature/mcp_servers.py",
        python_cmd="python"  # or "python3" depending on your system
    )

    async with Client(transport) as client:
        # List available tools
        tools = await client.list_tools()
        print(f"Available tools: {[tool.name for tool in tools]}")
        print("-" * 50)

        # Call the doi text tool
        print("Testing DOI fetcher:")
        doi = "10.7717/peerj.16290"
        print(f"Fetching text for DOI: {doi}")

        try:
            result = await client.call_tool("get_text_from_doi", {"doi": doi})
            print(f"Result type: {type(result)}")
            if result and len(result) > 0:
                text_content = result[0].text
                print(f"DOI text (first 500 chars):\n{text_content[:500]}...")
                print(f"\nTotal length: {len(text_content)} characters")
            else:
                print("No result returned from DOI fetcher")
        except Exception as e:
            print(f"Error calling DOI fetcher: {e}")


def run():
    """Synchronous entry point for script"""
    asyncio.run(main())


if __name__ == "__main__":
    # Run the async main function
    run()
