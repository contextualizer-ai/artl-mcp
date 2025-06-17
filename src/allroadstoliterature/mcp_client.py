import asyncio
from fastmcp import Client
from fastmcp.client.transports import PythonStdioTransport


async def main():
    # Use explicit transport for better control
    transport = PythonStdioTransport(
        script_path="src/allroadstoliterature/mcps.py",
        python_cmd="python"  # or "python3" depending on your system
    )

    async with Client(transport) as client:
        # List available tools
        tools = await client.list_tools()
        print(f"Available tools: {[tool.name for tool in tools]}")
        print("-" * 50)

        # Call the add tool
        print("Testing add function:")
        result = await client.call_tool("add", {"a": 5, "b": 3})
        print(f"Result type: {type(result)}")
        print(f"Result: {result}")
        if result and len(result) > 0:
            print(f"Add result: 5 + 3 = {result[0].text}")
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


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
