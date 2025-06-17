# server.py
from fastmcp import FastMCP
from aurelian.utils.doi_fetcher import DOIFetcher

mcp = FastMCP("Demo 🚀")


@mcp.tool
def get_text_from_doi(doi: str) -> str:
    """Get text from a DOI"""
    dfr = DOIFetcher(email="senior_distinguished_scientist@lbl.gov")
    doi_text = dfr.get_full_text(doi)
    return doi_text


if __name__ == "__main__":
    mcp.run()
