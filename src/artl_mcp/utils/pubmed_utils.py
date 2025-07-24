import logging
import re

import requests
from bs4 import BeautifulSoup

from artl_mcp.utils.conversion_utils import IdentifierConverter
from artl_mcp.utils.doi_fetcher import DOIFetcher
from artl_mcp.utils.email_manager import get_email
from artl_mcp.utils.identifier_utils import IdentifierError, IdentifierUtils

logger = logging.getLogger(__name__)

BIOC_URL = "https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_xml/{pmid}/ascii"
PUBMED_EUTILS_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={pmid}&retmode=xml"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={pmid}&retmode=xml"

DOI_PATTERN = r"/(10\.\d{4,9}/[\w\-.]+)"


def extract_doi_from_url(url: str) -> str | None:
    """Extracts the DOI from a given journal URL.

    This function specifically extracts DOIs from URLs only, not from plain DOI strings.
    Use IdentifierUtils.normalize_doi() if you need to process plain DOIs.

    Supports URL formats:
    - https://doi.org/10.1234/example
    - http://dx.doi.org/10.1234/example
    - Any URL containing a DOI path

    Args:
        url: The URL of the article (must be a URL, not a plain DOI)

    Returns:
        DOI in standard format (10.1234/example) or None if not found in URL

    Examples:
        >>> extract_doi_from_url("https://doi.org/10.1038/nature12373")
        '10.1038/nature12373'
        >>> extract_doi_from_url("10.1038/nature12373")  # Plain DOI
        None
        >>> extract_doi_from_url("https://example.com/paper/123")
        None
    """
    if not url:
        return None

    # Only process if it looks like a URL (contains protocol or domain indicators)
    if not ("://" in url or url.startswith("www.") or "." in url):
        return None

    # Try URL-specific patterns first
    for pattern in IdentifierUtils.DOI_URL_PATTERNS:
        match = pattern.search(url)
        if match:
            return match.group(1)

    # Fallback to general DOI pattern in URL context
    doi_match = re.search(DOI_PATTERN, url)
    return doi_match.group(1) if doi_match else None


def doi_to_pmid(doi: str) -> str | None:
    """Converts a DOI to a PMID using the NCBI ID Converter API.

    Supports multiple DOI input formats:
    - Raw DOI: 10.1234/example
    - CURIE: doi:10.1234/example
    - URL: https://doi.org/10.1234/example

    Args:
        doi: The DOI to be converted in any supported format

    Returns:
        PMID as string (raw format, no prefix) or None if conversion fails

    Examples:
        >>> doi_to_pmid("10.1038/nature12373")
        '23851394'
        >>> doi_to_pmid("doi:10.1038/nature12373")
        '23851394'
        >>> doi_to_pmid("https://doi.org/10.1038/nature12373")
        '23851394'
    """
    return IdentifierConverter.doi_to_pmid(doi)


def get_doi_text(doi: str) -> str:
    """Fetch the full text of an article using a DOI.

    TODO: non pubmed sources

    Example:
        >>> doi = "10.1128/msystems.00045-18"
        >>> full_text = get_doi_text(doi)
        >>> assert "Populus Microbiome" in full_text

    Args:
        doi: The DOI of the article.

    Returns:
        The full text of the article if available, otherwise an empty string.

    """
    pmid = doi_to_pmid(doi)
    if not pmid:
        # Try to get full text via DOIFetcher if email is available
        email = get_email()
        if email:
            try:
                doi_fetcher = DOIFetcher(email=email)
                info = doi_fetcher.get_full_text(doi)
                if info:
                    return info
            except Exception:
                # If DOIFetcher fails, continue to return PMID not found message
                pass
        return (
            f"PMID not found for {doi} and full text not available "
            "(email required for DOI fallback)"
        )
    return get_pmid_text(pmid)


def get_pmid_from_pmcid(pmcid: str | int) -> str | None:
    """Fetch the PMID from a PMC ID using the Entrez E-utilities.

    Supports multiple PMCID input formats:
    - Full PMCID: PMC5048378
    - Numeric only: 5048378
    - Prefixed: PMC:5048378
    - Colon-separated: pmcid:PMC5048378

    Args:
        pmcid: PMCID in any supported format

    Returns:
        PMID as string (raw format) or None if conversion fails

    Examples:
        >>> get_pmid_from_pmcid("PMC5048378")
        '27629041'
        >>> get_pmid_from_pmcid("5048378")
        '27629041'
        >>> get_pmid_from_pmcid("PMC:5048378")
        '27629041'
    """
    return IdentifierConverter.pmcid_to_pmid(pmcid)


def get_pmcid_text(pmcid: str | int) -> str:
    """Fetch full text from PubMed Central Open Access BioC XML.

    Supports multiple PMCID input formats:
    - Full PMCID: PMC5048378
    - Numeric only: 5048378
    - Prefixed: PMC:5048378
    - Colon-separated: pmcid:PMC5048378

    Args:
        pmcid: PMCID in any supported format

    Returns:
        Full text content as string

    Examples:
        >>> get_pmcid_text("PMC5048378")
        'The full text content...'
        >>> get_pmcid_text("5048378")
        'The full text content...'
    """
    pmid = get_pmid_from_pmcid(pmcid)
    if pmid:
        return get_pmid_text(pmid)
    else:
        try:
            normalized_pmcid = IdentifierUtils.normalize_pmcid(pmcid, "raw")
            return (
                f"Could not retrieve text for PMCID {normalized_pmcid}: "
                "PMID conversion failed"
            )
        except IdentifierError:
            return f"Error: Invalid PMCID format: {pmcid}"


def get_pmid_text(pmid: str | int) -> str:
    """Fetch full text from PubMed Central Open Access BioC XML.
    If full text is not available, fallback to fetching the abstract from PubMed.

    Supports multiple PMID input formats:
    - Raw PMID: 12345678
    - Prefixed: PMID:12345678
    - Colon-separated: pmid:12345678

    Args:
        pmid: PubMed ID in any supported format

    Returns:
        Full text if available, otherwise abstract text

    Examples:
        >>> get_pmid_text("11")
        'Identification of adenylate cyclase-coupled beta-adrenergic receptors...'
        >>> get_pmid_text("PMID:11")
        'Identification of adenylate cyclase-coupled beta-adrenergic receptors...'
    """
    try:
        normalized_pmid = IdentifierUtils.normalize_pmid(pmid, "raw")
    except IdentifierError as e:
        logger.warning(f"Invalid PMID for text retrieval: {pmid} - {e}")
        return f"Error: Invalid PMID format: {pmid}"
    text = get_full_text_from_bioc(normalized_pmid)
    if not text:
        doi = pmid_to_doi(normalized_pmid)
        if doi:
            # Try to get full text via DOIFetcher if email is available
            email = get_email()
            if email:
                try:
                    doi_fetcher = DOIFetcher(email=email)
                    full_text_result = doi_fetcher.get_full_text(doi)
                    if full_text_result:
                        text = full_text_result
                except Exception:
                    # If DOIFetcher fails, continue to try other methods
                    pass
    if not text:
        text = get_abstract_from_pubmed(normalized_pmid)
    return text


def pmid_to_doi(pmid: str | int) -> str | None:
    """Converts a PMID to a DOI using PubMed E-utilities.

    Supports multiple PMID input formats:
    - Raw PMID: 12345678
    - Prefixed: PMID:12345678
    - Colon-separated: pmid:12345678

    Args:
        pmid: PMID in any supported format

    Returns:
        DOI in standard format (10.1234/example) or None if conversion fails

    Examples:
        >>> pmid_to_doi("23851394")
        '10.1038/nature12373'
        >>> pmid_to_doi("PMID:23851394")
        '10.1038/nature12373'
    """
    return IdentifierConverter.pmid_to_doi(pmid)


def get_full_text_from_bioc(pmid: str) -> str:
    """Fetch full text from PubMed Central Open Access BioC XML.

    Example:
        >>> pmid = "17299597"
        >>> full_text = get_full_text_from_bioc(pmid)
        >>> assert "Evolution of biological complexity." in full_text

    Args:
        pmid: PubMed ID of the article.

    Returns:
        The full text of the article if available, otherwise an empty string.

    """
    response = requests.get(BIOC_URL.format(pmid=pmid))

    if response.status_code != 200:
        return ""  # Return empty string if request fails

    soup = BeautifulSoup(response.text, "xml")

    # Extract ONLY text from <text> tags within <passage>
    text_sections = [text_tag.get_text() for text_tag in soup.find_all("text")]

    full_text = "\n".join(text_sections).strip()
    return full_text


def get_abstract_from_pubmed(pmid: str) -> str:
    """Fetch the title and abstract of an article from PubMed using Entrez
    E-utilities `efetch`.

    The output includes normalized whitespace (Unicode whitespace characters
    are replaced with regular spaces) and follows this format:
    - Article title
    - Blank line
    - Abstract text (as a single line, no paragraph breaks)
    - Blank line
    - "PMID:" followed by the PubMed ID

    Example:
        >>> pmid = "31653696"
        >>> abstract = get_abstract_from_pubmed(pmid)
        >>> assert "The apparent deglycase activity of DJ-1" in abstract
        >>> assert abstract.endswith(f"PMID:{pmid}")

    Args:
        pmid: PubMed ID of the article.

    Returns:
        Formatted text containing title, abstract, and PMID. Returns empty
        string if the article cannot be retrieved.

    """
    response = requests.get(EFETCH_URL.format(pmid=pmid))

    if response.status_code != 200:
        return ""

    soup = BeautifulSoup(response.text, "xml")

    # Extract title
    title_tag = soup.find("ArticleTitle")
    title = title_tag.get_text().strip() if title_tag else "No title available"

    # Extract abstract (may contain multiple sections)
    abstract_tags = soup.find_all("AbstractText")
    abstract = (
        "\n".join(tag.get_text().strip() for tag in abstract_tags)
        if abstract_tags
        else "No abstract available"
    )

    # Normalize whitespace - replace special Unicode whitespace with regular spaces
    # But preserve newlines for paragraph structure
    title = re.sub(r"[^\S\n]", " ", title)  # Replace non-newline whitespace
    title = re.sub(r" +", " ", title).strip()  # Collapse multiple spaces

    abstract = re.sub(r"[^\S\n]", " ", abstract)  # Replace non-newline whitespace
    abstract = re.sub(r" +", " ", abstract).strip()  # Collapse multiple spaces

    return f"{title}\n\n{abstract}\n\nPMID:{pmid}"
