import click
import asyncio
import os
import json
from openai import OpenAI
from fastmcp import FastMCP
from allroadstoliterature.tools import get_doi_metadata


def create_mcp():
    """Create the FastMCP instance with registered tools."""
    mcp = FastMCP("all-roads-to-literature")
    mcp.tool(get_doi_metadata)
    return mcp


# Create it once for both modes
mcp = create_mcp()



async def call_mcp(query: str):
    """Use OpenAI GPT-4o to process the query and run the appropriate tool."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set in environment.")

    client = OpenAI(api_key=api_key)

    system_prompt = (
        "You are an AI agent that maps natural language queries to tool calls. "
        "The only tool you have is `get_doi_metadata(doi: str)` which looks up metadata for a given DOI. "
        "Return ONLY a JSON object like: {\"tool\": \"get_doi_metadata\", \"args\": {\"doi\": \"...\"}}"
    )

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ],
        temperature=0
    )

    tool_call = response.choices[0].message.content

    try:
        parsed = json.loads(tool_call)
        tool_name = parsed["tool"]
        args = parsed["args"]
    except Exception as e:
        raise ValueError(f"Failed to parse GPT response: {tool_call}") from e

    return await mcp.invoke(tool_name, args)



@click.command()
@click.option('--server', is_flag=True, help='Start the MCP server.')
@click.option('--query', type=str, help='Run a natural language query to try out the mcp.')
def cli(server, query):
    """Run the All Roads to Literature MCP."""
    if server:
        mcp.run()
    elif query:
        result = asyncio.run(call_mcp(query))
        print(result)
    else:
        click.echo(cli.get_help(click.Context(cli)))


if __name__ == "__main__":
    cli()
