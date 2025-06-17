# server.py
from fastmcp import FastMCP
from aurelian.utils.doi_fetcher import DOIFetcher
import aurelian.utils.pubmed_utils as aupu

mcp = FastMCP("Demo 🚀")


@mcp.tool
def get_abstract_from_pubmed_id(pmid: str) -> str:
    """Get text from a DOI"""
    abstract_from_pubmed = aupu.get_abstract_from_pubmed(pmid)
    return abstract_from_pubmed


if __name__ == "__main__":
    mcp.run()
