import habanero
from typing import Dict, Any, Optional
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

