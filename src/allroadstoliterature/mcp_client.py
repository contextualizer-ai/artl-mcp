import asyncio
from fastmcp import Client
from fastmcp.client.transports import PythonStdioTransport


async def main():
    # Method 1: Auto-detect transport (recommended)
    # Just pass the path to the Python file
    try:
        async with Client("src/allroadstoliterature/mcps.py") as client:
            # List available tools
            tools = await client.list_tools()
            print(f"Available tools: {[tool.name for tool in tools]}")

            # Call the add tool
            result = await client.call_tool("add", {"a": 5, "b": 3})
            print(f"Result type: {type(result)}")
            print(f"Result: {result}")

            # Try different ways to access the result
            if hasattr(result, 'content'):
                print(f"Result content: {result.content}")
            if hasattr(result, 'text'):
                print(f"Result text: {result.text}")
    except Exception as e:
        print(f"Method 1 failed: {e}")
        print("\nTrying Method 2...")

        # Method 2: Explicit transport
        transport = PythonStdioTransport(
            script_path="src/allroadstoliterature/mcps.py",
            python_cmd="python"  # or "python3" depending on your system
        )

        async with Client(transport) as client:
            # List available tools
            tools = await client.list_tools()
            print(f"Available tools: {[tool.name for tool in tools]}")

            # Call the add tool
            result = await client.call_tool("add", {"a": 5, "b": 3})
            print(f"Result type: {type(result)}")
            print(f"Result: {result}")


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
