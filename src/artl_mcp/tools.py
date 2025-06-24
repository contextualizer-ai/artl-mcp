from typing import Any

import aurelian.utils.pubmed_utils as aupu
import habanero
from aurelian.utils.doi_fetcher import DOIFetcher
from aurelian.utils.pdf_fetcher import extract_text_from_pdf


def get_doi_metadata(doi: str) -> dict[str, Any] | None:
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
    """Get abstract text from a PubMed ID.

    Args:
        pmid: The PubMed ID of the article.

    Returns:
        The abstract text of the article.
    """
    abstract_from_pubmed = aupu.get_abstract_from_pubmed(pmid)
    return abstract_from_pubmed


# DOIFetcher-based tools
def get_doi_fetcher_metadata(doi: str, email: str) -> dict[str, Any] | None:
    """
    Get metadata for a DOI using DOIFetcher.

    Args:
        doi: The Digital Object Identifier of the article.
        email: Email address for API requests (required by some services).

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
    Get Unpaywall information for a DOI.

    Args:
        doi: The Digital Object Identifier of the article.
        email: Email address for API requests (required by some services).
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

    Args:
        doi: The Digital Object Identifier of the article.
        email: Email address for API requests (required by some services).

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

    Args:
        doi: The Digital Object Identifier of the article.
        email: Email address for API requests (required by some services).

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

    Args:
        pdf_url: URL of the PDF to extract text from.
        email: Email address for API requests (required by some services).

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

    Args:
        text: The text to clean.
        email: Email address for API requests (required by some services).

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
