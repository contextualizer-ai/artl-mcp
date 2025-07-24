"""Citation and reference utilities for scientific literature.

Provides functionality to retrieve citation networks, references, and related papers
using CrossRef, OpenAlex, and other APIs.
"""

import json
import logging

import requests

from .email_manager import get_email
from .identifier_utils import IdentifierError, IdentifierUtils

logger = logging.getLogger(__name__)

# Default headers
DEFAULT_HEADERS = {
    "User-Agent": "ARTL-MCP/1.0 (https://github.com/contextualizer-ai/artl-mcp)"
}

# API endpoints
CROSSREF_API_URL = "https://api.crossref.org/works"
OPENALEX_API_URL = "https://api.openalex.org/works"
SEMANTIC_SCHOLAR_API_URL = "https://api.semanticscholar.org/graph/v1/paper"


class CitationError(Exception):
    """Exception raised for citation retrieval errors."""

    pass


class CitationUtils:
    """Utilities for retrieving citation networks and related papers."""

    @staticmethod
    def _make_api_request(
        url: str,
        params: dict | None = None,
        headers: dict | None = None,
        timeout: int = 10,
    ) -> dict | None:
        """Make API request with proper error handling.

        Args:
            url: API endpoint URL
            params: Request parameters
            headers: Request headers
            timeout: Request timeout in seconds

        Returns:
            JSON response data or None on error
        """
        if headers is None:
            headers = DEFAULT_HEADERS.copy()

        # Add email if available for CrossRef
        email = get_email()
        if email and "crossref.org" in url:
            headers["mailto"] = email

        try:
            response = requests.get(
                url, params=params, headers=headers, timeout=timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.warning(f"API request failed for {url}: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON response from {url}: {e}")
            return None

    @classmethod
    def get_references_crossref(cls, doi: str, timeout: int = 10) -> list[dict] | None:
        """Get references cited by a paper using CrossRef API.

        Args:
            doi: DOI of the paper
            timeout: Request timeout in seconds

        Returns:
            List of reference dictionaries or None on error

        Examples:
            >>> refs = CitationUtils.get_references_crossref("10.1038/nature12373")
            >>> len(refs) if refs else 0
            25
        """
        try:
            normalized_doi = IdentifierUtils.normalize_doi(doi, "raw")
        except IdentifierError as e:
            logger.warning(f"Invalid DOI for references: {doi} - {e}")
            return None

        url = f"{CROSSREF_API_URL}/{normalized_doi}"
        data = cls._make_api_request(url, timeout=timeout)

        if not data:
            return None

        try:
            work = data["message"]
            references = work.get("reference", [])

            # Process references to extract useful information
            processed_refs = []
            for ref in references:
                ref_info = {
                    "key": ref.get("key"),
                    "doi": ref.get("DOI"),
                    "title": ref.get("article-title"),
                    "journal": ref.get("journal-title"),
                    "year": ref.get("year"),
                    "volume": ref.get("volume"),
                    "page": ref.get("first-page"),
                    "author": ref.get("author"),
                    "unstructured": ref.get("unstructured"),
                }
                processed_refs.append(ref_info)

            return processed_refs

        except (KeyError, TypeError) as e:
            logger.warning(f"Error processing references for DOI {doi}: {e}")
            return None

    @classmethod
    def get_citations_crossref(cls, doi: str, timeout: int = 10) -> list[dict] | None:
        """Get papers that cite a given paper using CrossRef API.

        Args:
            doi: DOI of the paper
            timeout: Request timeout in seconds

        Returns:
            List of citing paper dictionaries or None on error

        Examples:
            >>> citations = CitationUtils.get_citations_crossref("10.1038/nature12373")
            >>> len(citations) if citations else 0
            150
        """
        try:
            normalized_doi = IdentifierUtils.normalize_doi(doi, "raw")
        except IdentifierError as e:
            logger.warning(f"Invalid DOI for citations: {doi} - {e}")
            return None

        # Search for papers that reference this DOI
        params = {
            "query.bibliographic": normalized_doi,
            "rows": 100,  # Limit to first 100 citations
            "select": "DOI,title,author,published-print,is-referenced-by-count",
        }

        data = cls._make_api_request(CROSSREF_API_URL, params=params, timeout=timeout)

        if not data:
            return None

        try:
            items = data["message"]["items"]

            # Process citing papers
            citations = []
            for item in items:
                citation_info = {
                    "doi": item.get("DOI"),
                    "title": item.get("title", [None])[0],
                    "authors": [
                        f"{author.get('given', '')} {author.get('family', '')}"
                        for author in item.get("author", [])
                    ],
                    "published_date": item.get("published-print"),
                    "citation_count": item.get("is-referenced-by-count", 0),
                }
                citations.append(citation_info)

            return citations

        except (KeyError, TypeError) as e:
            logger.warning(f"Error processing citations for DOI {doi}: {e}")
            return None

    @classmethod
    def get_citation_network_openalex(cls, doi: str, timeout: int = 10) -> dict | None:
        """Get comprehensive citation network using OpenAlex API.

        Args:
            doi: DOI of the paper
            timeout: Request timeout in seconds

        Returns:
            Dictionary with citation network information or None on error

        Examples:
            >>> network = CitationUtils.get_citation_network_openalex(
            ...     "10.1038/nature12373"
            ... )
            >>> network["cited_by_count"] if network else 0
            245
        """
        try:
            normalized_doi = IdentifierUtils.normalize_doi(doi, "raw")
        except IdentifierError as e:
            logger.warning(f"Invalid DOI for citation network: {doi} - {e}")
            return None

        # OpenAlex uses DOI URLs
        openalex_id = f"https://doi.org/{normalized_doi}"
        url = f"{OPENALEX_API_URL}/{openalex_id}"

        data = cls._make_api_request(url, timeout=timeout)

        if not data:
            return None

        try:
            work = data

            # Extract citation network information
            network = {
                "doi": normalized_doi,
                "title": work.get("title"),
                "publication_year": work.get("publication_year"),
                "cited_by_count": work.get("cited_by_count", 0),
                "references_count": len(work.get("referenced_works", [])),
                "concepts": [
                    {
                        "display_name": concept.get("display_name"),
                        "level": concept.get("level"),
                        "score": concept.get("score"),
                    }
                    for concept in work.get("concepts", [])[:10]  # Top 10 concepts
                ],
                "mesh_terms": [
                    mesh.get("descriptor_name")
                    for mesh in work.get("mesh", [])[:10]  # Top 10 MeSH terms
                ],
                "referenced_works": work.get("referenced_works", [])[:20],  # 20 refs
                "cited_by_api_url": work.get("cited_by_api_url"),
                "open_access": work.get("open_access", {}),
            }

            return network

        except (KeyError, TypeError) as e:
            logger.warning(f"Error processing OpenAlex data for DOI {doi}: {e}")
            return None

    @classmethod
    def get_semantic_scholar_info(cls, doi: str, timeout: int = 10) -> dict | None:
        """Get paper information from Semantic Scholar API.

        Args:
            doi: DOI of the paper
            timeout: Request timeout in seconds

        Returns:
            Dictionary with Semantic Scholar information or None on error
        """
        try:
            normalized_doi = IdentifierUtils.normalize_doi(doi, "raw")
        except IdentifierError as e:
            logger.warning(f"Invalid DOI for Semantic Scholar: {doi} - {e}")
            return None

        url = f"{SEMANTIC_SCHOLAR_API_URL}/DOI:{normalized_doi}"
        params = {
            "fields": (
                "title,authors,year,citationCount,referenceCount,"
                "citations,references,tldr,abstract"
            )
        }

        data = cls._make_api_request(url, params=params, timeout=timeout)

        if not data:
            return None

        try:
            # Process the response
            paper_info = {
                "doi": normalized_doi,
                "title": data.get("title"),
                "authors": [author.get("name") for author in data.get("authors", [])],
                "year": data.get("year"),
                "citation_count": data.get("citationCount", 0),
                "reference_count": data.get("referenceCount", 0),
                "abstract": data.get("abstract"),
                "tldr": data.get("tldr", {}).get("text") if data.get("tldr") else None,
                "citations": [
                    {
                        "title": citation.get("title"),
                        "doi": citation.get("externalIds", {}).get("DOI"),
                        "year": citation.get("year"),
                    }
                    for citation in data.get("citations", [])[:10]  # First 10 citations
                ],
                "references": [
                    {
                        "title": ref.get("title"),
                        "doi": ref.get("externalIds", {}).get("DOI"),
                        "year": ref.get("year"),
                    }
                    for ref in data.get("references", [])[:10]  # First 10 references
                ],
            }

            return paper_info

        except (KeyError, TypeError) as e:
            logger.warning(f"Error processing Semantic Scholar data for DOI {doi}: {e}")
            return None

    @classmethod
    def get_comprehensive_citation_info(
        cls, doi: str, timeout: int = 10
    ) -> dict[str, str | dict | list | None]:
        """Get comprehensive citation information from multiple sources.

        Args:
            doi: DOI of the paper
            timeout: Request timeout in seconds

        Returns:
            Dictionary with information from multiple sources

        Examples:
            >>> info = CitationUtils.get_comprehensive_citation_info(
            ...     "10.1038/nature12373"
            ... )
            >>> info.keys()
            dict_keys(['crossref_references', 'crossref_citations',
                       'openalex_network', 'semantic_scholar'])
        """
        try:
            normalized_doi = IdentifierUtils.normalize_doi(doi, "raw")
        except IdentifierError as e:
            logger.warning(f"Invalid DOI for comprehensive citation info: {doi} - {e}")
            return {"error": str(e)}

        result: dict[str, str | dict | list | None] = {
            "doi": normalized_doi,
            "crossref_references": None,
            "crossref_citations": None,
            "openalex_network": None,
            "semantic_scholar": None,
        }

        # Get data from each source (continue even if one fails)
        try:
            result["crossref_references"] = cls.get_references_crossref(
                normalized_doi, timeout
            )
        except Exception as e:
            logger.warning(f"Error getting CrossRef references: {e}")

        try:
            result["crossref_citations"] = cls.get_citations_crossref(
                normalized_doi, timeout
            )
        except Exception as e:
            logger.warning(f"Error getting CrossRef citations: {e}")

        try:
            result["openalex_network"] = cls.get_citation_network_openalex(
                normalized_doi, timeout
            )
        except Exception as e:
            logger.warning(f"Error getting OpenAlex network: {e}")

        try:
            result["semantic_scholar"] = cls.get_semantic_scholar_info(
                normalized_doi, timeout
            )
        except Exception as e:
            logger.warning(f"Error getting Semantic Scholar info: {e}")

        return result

    @classmethod
    def find_related_papers(
        cls, doi: str, max_results: int = 10, timeout: int = 10
    ) -> list[dict] | None:
        """Find papers related to a given paper based on citations and concepts.

        Args:
            doi: DOI of the reference paper
            max_results: Maximum number of related papers to return
            timeout: Request timeout in seconds

        Returns:
            List of related paper dictionaries or None on error
        """
        # Get comprehensive citation info
        citation_info = cls.get_comprehensive_citation_info(doi, timeout)

        related_papers = []

        # Extract related papers from citations (papers that cite this one)
        crossref_citations = citation_info.get("crossref_citations")
        if crossref_citations and isinstance(crossref_citations, list):
            for citation in crossref_citations[: max_results // 2]:
                if citation.get("doi"):
                    related_papers.append(
                        {
                            "doi": citation["doi"],
                            "title": citation.get("title"),
                            "authors": citation.get("authors", []),
                            "relationship": "cites_this_paper",
                            "citation_count": citation.get("citation_count", 0),
                        }
                    )

        # Extract related papers from references (papers this one cites)
        crossref_references = citation_info.get("crossref_references")
        if crossref_references and isinstance(crossref_references, list):
            for reference in crossref_references[: max_results // 2]:
                if reference.get("doi"):
                    related_papers.append(
                        {
                            "doi": reference["doi"],
                            "title": reference.get("title"),
                            "journal": reference.get("journal"),
                            "relationship": "cited_by_this_paper",
                            "year": reference.get("year"),
                        }
                    )

        # Remove duplicates and limit results
        seen_dois = set()
        unique_papers = []
        for paper in related_papers:
            if paper["doi"] not in seen_dois:
                seen_dois.add(paper["doi"])
                unique_papers.append(paper)
                if len(unique_papers) >= max_results:
                    break

        return unique_papers if unique_papers else None


# Convenience functions
def get_references(doi: str, timeout: int = 10) -> list[dict] | None:
    """Get references cited by a paper."""
    return CitationUtils.get_references_crossref(doi, timeout)


def get_citations(doi: str, timeout: int = 10) -> list[dict] | None:
    """Get papers that cite a given paper."""
    return CitationUtils.get_citations_crossref(doi, timeout)


def get_citation_network(doi: str, timeout: int = 10) -> dict | None:
    """Get comprehensive citation network information."""
    return CitationUtils.get_citation_network_openalex(doi, timeout)


def find_related_papers(
    doi: str, max_results: int = 10, timeout: int = 10
) -> list[dict] | None:
    """Find papers related to a given paper."""
    return CitationUtils.find_related_papers(doi, max_results, timeout)
