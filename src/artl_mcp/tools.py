from typing import Any

import requests

import artl_mcp.utils.pubmed_utils as aupu
from artl_mcp.utils.doi_fetcher import DOIFetcher
from artl_mcp.utils.pdf_fetcher import extract_text_from_pdf


def get_doi_metadata(doi: str) -> dict[str, Any] | None:
    """
    Retrieve metadata for a scientific article using its DOI.

    Args:
        doi: The Digital Object Identifier of the article.

    Returns:
        A dictionary containing the article metadata if successful, None otherwise.
        Returns the same format as habanero.Crossref().works(ids=doi)
    """
    try:
        # Clean DOI (remove any URL prefixes)
        clean_doi = doi.replace("https://doi.org/", "").replace(
            "http://dx.doi.org/", ""
        )

        url = f"https://api.crossref.org/works/{clean_doi}"
        headers = {
            "Accept": "application/json",
            "User-Agent": "artl-mcp/1.0 (mailto:your-email@domain.com)",
        }  # Replace with your email

        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        data = response.json()

        # Return in the same format as habanero - just the API response
        return data

    except requests.exceptions.RequestException as e:
        print(f"Error retrieving metadata for DOI {doi}: {e}")
        return None
    except Exception as e:
        import traceback

        print(f"Unexpected error retrieving metadata for DOI {doi}: {e}")
        traceback.print_exc()
        raise


def search_papers_by_keyword(
    query: str,
    max_results: int = 20,
    sort: str = "relevance",
    filter_params: dict[str, str] | None = None,
) -> dict[str, Any] | None:
    """
    Search for scientific papers using keywords.

    Args:
        query: Search terms/keywords
        max_results: Maximum number of results to return (default 20, max 1000)
        sort: Sort order - "relevance", "published", "created", "updated",
              "is-referenced-by-count" (default "relevance")
        filter_params: Additional filters as key-value pairs, e.g.:
                      {"type": "journal-article", "from-pub-date": "2020"}

    Returns:
        A dictionary containing search results if successful, None otherwise.
        Format matches habanero.Crossref().works(query=query)
    """
    try:
        url = "https://api.crossref.org/works"

        # Build query parameters
        params = {
            "query": query,
            "rows": str(min(max_results, 1000)),  # API max is 1000
            "sort": sort,
        }

        # Add filters if provided
        if filter_params:
            for key, value in filter_params.items():
                if key == "type":
                    params["filter"] = f"type:{value}"
                elif key in ["from-pub-date", "until-pub-date"]:
                    # No need to assign filter_key; directly manipulate params["filter"]
                    existing_filter = params.get("filter", "")
                    new_filter = f"{key}:{value}"
                    params["filter"] = (
                        f"{existing_filter},{new_filter}"
                        if existing_filter
                        else new_filter
                    )
                else:
                    # Handle other filters
                    filter_key = "filter"
                    existing_filter = params.get(filter_key, "")
                    new_filter = f"{key}:{value}"
                    params[filter_key] = (
                        f"{existing_filter},{new_filter}"
                        if existing_filter
                        else new_filter
                    )

        headers = {
            "Accept": "application/json",
            "User-Agent": "artl-mcp/1.0 (mailto:your-email@domain.com)",
        }

        # Replace with your email

        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()

        # Return in the same format as habanero
        return data

    except requests.exceptions.RequestException as e:
        print(f"Error searching for papers with query '{query}': {e}")
        return None
    except Exception as e:
        print(f"Error searching for papers with query '{query}': {e}")
        return None


# Example usage and helper function
def search_recent_papers(
    query: str,
    years_back: int = 5,
    max_results: int = 20,
    paper_type: str = "journal-article",
) -> dict[str, Any] | None:
    """
    Convenience function to search for recent papers.

    Args:
        query: Search terms
        years_back: How many years back to search (default 5)
        max_results: Max results to return
        paper_type: Type of publication (default "journal-article")

    Returns:
        Search results or None
    """
    from datetime import datetime, timedelta

    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=years_back * 365)

    filters = {"type": paper_type, "from-pub-date": start_date.strftime("%Y-%m-%d")}

    return search_papers_by_keyword(
        query=query, max_results=max_results, sort="published", filter_params=filters
    )


# Example of how to extract common fields from results
def extract_paper_info(work_item: dict) -> dict[str, Any]:
    """
    Helper function to extract common fields from a CrossRef work item.

    Args:
        work_item: Single work item from CrossRef API response

    Returns:
        Dictionary with commonly used fields
    """
    try:
        return {
            "title": work_item.get("title", [""])[0] if work_item.get("title") else "",
            "authors": [
                f"{author.get('given', '')} {author.get('family', '')}"
                for author in work_item.get("author", [])
            ],
            "journal": (
                work_item.get("container-title", [""])[0]
                if work_item.get("container-title")
                else ""
            ),
            "published_date": work_item.get(
                "published-print", work_item.get("published-online", {})
            ),
            "doi": work_item.get("DOI", ""),
            "url": work_item.get("URL", ""),
            "abstract": work_item.get("abstract", ""),
            "citation_count": work_item.get("is-referenced-by-count", 0),
            "type": work_item.get("type", ""),
            "publisher": work_item.get("publisher", ""),
        }
    except Exception as e:
        print(f"Error extracting paper info: {e}")
        return {}


def get_abstract_from_pubmed_id(pmid: str) -> str:
    """Get formatted abstract text from a PubMed ID.

    Returns title, abstract text, and PMID in a formatted structure with
    normalized whitespace. This is a wrapper around get_abstract_from_pubmed.

    Args:
        pmid: The PubMed ID of the article.

    Returns:
        Formatted text containing title, abstract, and PMID.
    """
    abstract_from_pubmed = aupu.get_abstract_from_pubmed(pmid)
    return abstract_from_pubmed


# DOIFetcher-based tools
def get_doi_fetcher_metadata(doi: str, email: str) -> dict[str, Any] | None:
    """
    Get metadata for a DOI using DOIFetcher. Requires a user email address.

    IMPORTANT: This tool requires an email address. If the user hasn't provided one,
    please ask them for their email address before calling this tool.

    Args:
        doi: The Digital Object Identifier of the article.
        email: Email address for API requests (required - ask user if not provided).

    Returns:
        A dictionary containing the article metadata if successful, None otherwise.
    """
    try:
        dfr = DOIFetcher(email=email)
        return dfr.get_metadata(doi)
    except Exception as e:
        print(f"Error retrieving metadata for DOI {doi}: {e}")
        return None


def get_unpaywall_info(
    doi: str, email: str, strict: bool = True
) -> dict[str, Any] | None:
    """
    Get Unpaywall information for a DOI to find open access versions.

    IMPORTANT: This tool requires an email address. If the user hasn't provided one,
    please ask them for their email address before calling this tool.

    Args:
        doi: The Digital Object Identifier of the article.
        email: Email address for API requests (required - ask user if not provided).
        strict: Whether to use strict mode for Unpaywall queries.

    Returns:
        A dictionary containing Unpaywall information if successful, None otherwise.
    """
    try:
        dfr = DOIFetcher(email=email)
        return dfr.get_unpaywall_info(doi, strict=strict)
    except Exception as e:
        print(f"Error retrieving Unpaywall info for DOI {doi}: {e}")
        return None


def get_full_text_from_doi(doi: str, email: str) -> str | None:
    """
    Get full text content from a DOI.

    IMPORTANT: This tool requires an email address. If the user hasn't provided one,
    please ask them for their email address before calling this tool.

    Args:
        doi: The Digital Object Identifier of the article.
        email: Email address for API requests (required - ask user if not provided).

    Returns:
        The full text content if successful, None otherwise.
    """
    try:
        dfr = DOIFetcher(email=email)
        return dfr.get_full_text(doi)
    except Exception as e:
        print(f"Error retrieving full text for DOI {doi}: {e}")
        return None


def get_full_text_info(doi: str, email: str) -> dict[str, Any] | None:
    """
    Get full text information (metadata about full text availability) from a DOI.

    IMPORTANT: This tool requires an email address. If the user hasn't provided one,
    please ask them for their email address before calling this tool.

    Args:
        doi: The Digital Object Identifier of the article.
        email: Email address for API requests (required - ask user if not provided).

    Returns:
        Information about full text availability if successful, None otherwise.
    """
    try:
        dfr = DOIFetcher(email=email)
        result = dfr.get_full_text_info(doi)
        if result is None:
            return None
        return {"success": getattr(result, "success", False), "info": str(result)}
    except Exception as e:
        print(f"Error retrieving full text info for DOI {doi}: {e}")
        return None


def get_text_from_pdf_url(pdf_url: str, email: str) -> str | None:
    """
    Extract text from a PDF URL using DOIFetcher.

    IMPORTANT: This tool requires an email address. If the user hasn't provided one,
    please ask them for their email address before calling this tool.

    Args:
        pdf_url: URL of the PDF to extract text from.
        email: Email address for API requests (required - ask user if not provided).

    Returns:
        The extracted text if successful, None otherwise.
    """
    try:
        dfr = DOIFetcher(email=email)
        return dfr.text_from_pdf_url(pdf_url)
    except Exception as e:
        print(f"Error extracting text from PDF URL {pdf_url}: {e}")
        return None


def extract_pdf_text(pdf_url: str) -> str | None:
    """
    Extract text from a PDF URL using the standalone pdf_fetcher.

    Args:
        pdf_url: URL of the PDF to extract text from.

    Returns:
        The extracted text if successful, None otherwise.
    """
    try:
        result = extract_text_from_pdf(pdf_url)
        # Check if result is an error message
        if result and "Error extracting PDF text:" in str(result):
            print(f"Error extracting text from PDF URL {pdf_url}: {result}")
            return None
        return result
    except Exception as e:
        print(f"Error extracting text from PDF URL {pdf_url}: {e}")
        return None


def clean_text(text: str, email: str) -> str:
    """
    Clean text using DOIFetcher's text cleaning functionality.

    IMPORTANT: This tool requires an email address. If the user hasn't provided one,
    please ask them for their email address before calling this tool.

    Args:
        text: The text to clean.
        email: Email address for API requests (required - ask user if not provided).

    Returns:
        The cleaned text.
    """
    try:
        dfr = DOIFetcher(email=email)
        return dfr.clean_text(text)
    except Exception as e:
        print(f"Error cleaning text: {e}")
        return text


# PubMed utilities tools
def extract_doi_from_url(doi_url: str) -> str | None:
    """
    Extract DOI from a DOI URL.

    Args:
        doi_url: URL containing a DOI.

    Returns:
        The extracted DOI if successful, None otherwise.
    """
    try:
        return aupu.extract_doi_from_url(doi_url)
    except Exception as e:
        print(f"Error extracting DOI from URL {doi_url}: {e}")
        return None


def doi_to_pmid(doi: str) -> str | None:
    """
    Convert DOI to PubMed ID.

    Args:
        doi: The Digital Object Identifier.

    Returns:
        The PubMed ID if successful, None otherwise.
    """
    try:
        return aupu.doi_to_pmid(doi)
    except Exception as e:
        print(f"Error converting DOI {doi} to PMID: {e}")
        return None


def pmid_to_doi(pmid: str) -> str | None:
    """
    Convert PubMed ID to DOI.

    Args:
        pmid: The PubMed ID.

    Returns:
        The DOI if successful, None otherwise.
    """
    try:
        return aupu.pmid_to_doi(pmid)
    except Exception as e:
        print(f"Error converting PMID {pmid} to DOI: {e}")
        return None


def get_doi_text(doi: str) -> str | None:
    """
    Get full text from a DOI.

    Args:
        doi: The Digital Object Identifier.

    Returns:
        The full text if successful, None otherwise.
    """
    try:
        return aupu.get_doi_text(doi)
    except Exception as e:
        print(f"Error getting text for DOI {doi}: {e}")
        return None


def get_pmid_from_pmcid(pmcid: str) -> str | None:
    """
    Convert PMC ID to PubMed ID.

    Args:
        pmcid: The PMC ID (e.g., 'PMC1234567').

    Returns:
        The PubMed ID if successful, None otherwise.
    """
    try:
        return aupu.get_pmid_from_pmcid(pmcid)
    except Exception as e:
        print(f"Error converting PMCID {pmcid} to PMID: {e}")
        return None


def get_pmcid_text(pmcid: str) -> str | None:
    """
    Get full text from a PMC ID.

    Args:
        pmcid: The PMC ID (e.g., 'PMC1234567').

    Returns:
        The full text if successful, None otherwise.
    """
    try:
        return aupu.get_pmcid_text(pmcid)
    except Exception as e:
        print(f"Error getting text for PMCID {pmcid}: {e}")
        return None


def get_pmid_text(pmid: str) -> str | None:
    """
    Get full text from a PubMed ID.

    Args:
        pmid: The PubMed ID.

    Returns:
        The full text if successfully, None otherwise.
    """
    try:
        return aupu.get_pmid_text(pmid)
    except Exception as e:
        print(f"Error getting text for PMID {pmid}: {e}")
        return None


def get_full_text_from_bioc(pmid: str) -> str | None:
    """
    Get full text from BioC format for a PubMed ID.

    Args:
        pmid: The PubMed ID.

    Returns:
        The full text from BioC if successful, None otherwise.
    """
    try:
        return aupu.get_full_text_from_bioc(pmid)
    except Exception as e:
        print(f"Error getting BioC text for PMID {pmid}: {e}")
        return None


def search_pubmed_for_pmids(query: str, max_results: int = 20) -> dict[str, Any] | None:
    """
    Search PubMed for articles using keywords and return PMIDs with metadata.

    Args:
        query: The search query/keywords to search for in PubMed.
        max_results: Maximum number of PMIDs to return (default: 20).

    Returns:
        A dictionary containing PMIDs list, total count, and query info if
        successful, None otherwise.
    """
    esearch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {
        "db": "pubmed",
        "term": query,
        "retmode": "json",
        "retmax": str(max_results),
        "sort": "relevance",
    }

    try:
        response = requests.get(esearch_url, params=params)
        response.raise_for_status()

        data = response.json()

        if "esearchresult" in data:
            esearch_result = data["esearchresult"]
            pmids = esearch_result.get("idlist", [])
            total_count = int(esearch_result.get("count", 0))

            return {
                "pmids": pmids,
                "total_count": total_count,
                "returned_count": len(pmids),
                "query": query,
                "max_results": max_results,
            }
        else:
            print(f"No results found for query: {query}")
            return {
                "pmids": [],
                "total_count": 0,
                "returned_count": 0,
                "query": query,
                "max_results": max_results,
            }

    except Exception as e:
        print(f"Error searching PubMed for query '{query}': {e}")
        return None
