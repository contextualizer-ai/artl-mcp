import habanero
import requests
from typing import Dict, Any, Optional, List, Tuple
import aurelian.utils.pubmed_utils as aupu


def get_doi_metadata(doi: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve metadata for a scientific article using its DOI.

    Args:
        doi: The Digital Object Identifier of the article.

    Returns:
        A dictionary containing the article metadata if successful, None otherwise.
    """
    cr = habanero.Crossref()
    try:
        result = cr.works(ids=doi)
        return result
    except Exception as e:
        print(f"Error retrieving metadata for DOI {doi}: {e}")
        return None


def get_abstract_from_pubmed_id(pmid: str) -> str:
    """Get text from a DOI

    Args:
        pmid: The PubMed ID of the article.

    Returns:
        The abstract text of the article.

    """
    abstract_from_pubmed = aupu.get_abstract_from_pubmed(pmid)
    return abstract_from_pubmed


def search_pubmed_for_pmids(query: str, max_results: int = 20) -> Optional[Dict[str, Any]]:
    """
    Search PubMed for articles using keywords and return PMIDs with metadata.

    Args:
        query: The search query/keywords to search for in PubMed.
        max_results: Maximum number of PMIDs to return (default: 20).

    Returns:
        A dictionary containing PMIDs list, total count, and query info if successful, None otherwise.
    """
    esearch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {
        "db": "pubmed",
        "term": query,
        "retmode": "json",
        "retmax": max_results,
        "sort": "relevance"
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
                "max_results": max_results
            }
        else:
            print(f"No results found for query: {query}")
            return {
                "pmids": [],
                "total_count": 0,
                "returned_count": 0,
                "query": query,
                "max_results": max_results
            }
            
    except Exception as e:
        print(f"Error searching PubMed for query '{query}': {e}")
        return None
