import logging
from datetime import datetime, timedelta
from typing import Any

import requests

import artl_mcp.utils.pubmed_utils as aupu
from artl_mcp.utils.citation_utils import CitationUtils
from artl_mcp.utils.config_manager import get_email_manager
from artl_mcp.utils.conversion_utils import IdentifierConverter
from artl_mcp.utils.doi_fetcher import DOIFetcher
from artl_mcp.utils.file_manager import FileFormat, file_manager
from artl_mcp.utils.identifier_utils import IdentifierError, IdentifierUtils, IDType
from artl_mcp.utils.pdf_fetcher import extract_text_from_pdf

logger = logging.getLogger(__name__)


def _auto_generate_filename(
    base_name: str, identifier: str, file_format: FileFormat
) -> str:
    """Generate filename automatically if user provides True for save_to_file."""
    clean_identifier = identifier.replace("/", "_").replace(":", "_")
    return file_manager.generate_filename(base_name, clean_identifier, file_format)


def get_doi_metadata(
    doi: str, save_file: bool = False, save_to: str | None = None
) -> dict[str, Any] | None:
    """Retrieve metadata for a scientific article using its DOI.

    Supports multiple DOI input formats:
    - Raw DOI: 10.1038/nature12373
    - CURIE format: doi:10.1038/nature12373
    - URL formats: https://doi.org/10.1038/nature12373, http://dx.doi.org/10.1038/nature12373

    Args:
        doi: The Digital Object Identifier in any supported format
        save_file: Whether to save metadata to temp directory with auto-generated
            filename
        save_to: Specific path to save metadata (overrides save_file if provided)

    Returns:
        Dictionary containing article metadata from CrossRef API, or None if
        retrieval fails.
        Returns the complete CrossRef API response with 'message' containing work data.

    Examples:
        >>> metadata = get_doi_metadata("10.1038/nature12373")
        >>> metadata["message"]["title"][0]
        'Article title here'
        >>> get_doi_metadata("10.1038/nature12373", save_file=True)
        # Saves with auto-generated filename in temp directory
        >>> get_doi_metadata("10.1038/nature12373", save_to="my_paper.json")
        # Saves to specified path
    """
    try:
        # Normalize DOI to standard format
        try:
            clean_doi = IdentifierUtils.normalize_doi(doi, "raw")  # type: ignore[arg-type]
        except IdentifierError as e:
            logger.warning(f"Invalid DOI format: {doi} - {e}")
            return None

        url = f"https://api.crossref.org/works/{clean_doi}"
        headers = {
            "Accept": "application/json",
            "User-Agent": "ARTL-MCP/1.0 (https://github.com/contextualizer-ai/artl-mcp)",
        }

        # Add email if available for better API access
        em = get_email_manager()
        email = em.get_email()
        if email:
            headers["mailto"] = email

        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        data = response.json()

        # Save to file if requested
        saved_path = file_manager.handle_file_save(
            content=data,
            base_name="metadata",
            identifier=clean_doi,
            file_format="json",
            save_file=save_file,
            save_to=save_to,
            use_temp_dir=True,
        )
        if saved_path:
            logger.info(f"Metadata saved to: {saved_path}")

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
    save_file: bool = False,
    save_to: str | None = None,
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
        save_file: Whether to save search results to temp directory with
            auto-generated filename
        save_to: Specific path to save search results (overrides save_file if provided)

    Returns:
        A dictionary containing search results if successful, None otherwise.
        Format matches habanero.Crossref().works(query=query)
        If save_to is provided or save_file is True, also saves the search
        results to that file.

    Examples:
        >>> results = search_papers_by_keyword("CRISPR")
        >>> search_papers_by_keyword("CRISPR", save_file=True)
        # Saves with auto-generated filename in temp directory
        >>> search_papers_by_keyword("CRISPR", save_to="my_search.json")
        # Saves to specified path
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

        # Save to file if requested
        saved_path = file_manager.handle_file_save(
            content=data,
            base_name="search",
            identifier=query.replace(" ", "_"),
            file_format="json",
            save_file=save_file,
            save_to=save_to,
            use_temp_dir=True,
        )
        if saved_path:
            logger.info(f"Search results saved to: {saved_path}")

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
    save_file: bool = False,
    save_to: str | None = None,
) -> dict[str, Any] | None:
    """
    Convenience function to search for recent papers.

    Args:
        query: Search terms
        years_back: How many years back to search (default 5)
        max_results: Max results to return
        paper_type: Type of publication (default "journal-article")
        save_file: Whether to save search results to temp directory with
            auto-generated filename
        save_to: Specific path to save search results (overrides save_file if provided)

    Returns:
        Search results or None.
        If save_to is provided or save_file is True, also saves the search results
        to that file.

    Examples:
        >>> results = search_recent_papers("CRISPR", years_back=3)
        >>> search_recent_papers("CRISPR", save_file=True)
        # Saves with auto-generated filename in temp directory
        >>> search_recent_papers("CRISPR", save_to="recent_crispr.json")
        # Saves to specified path
    """

    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=years_back * 365)

    filters = {"type": paper_type, "from-pub-date": start_date.strftime("%Y-%m-%d")}

    # Use search_papers_by_keyword with file saving parameters
    return search_papers_by_keyword(
        query=query,
        max_results=max_results,
        sort="published",
        filter_params=filters,
        save_file=save_file,
        save_to=save_to,
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


def get_abstract_from_pubmed_id(
    pmid: str, save_file: bool = False, save_to: str | None = None
) -> str:
    """Get formatted abstract text from a PubMed ID.

    Returns title, abstract text, and PMID in a formatted structure with
    normalized whitespace. This is a wrapper around get_abstract_from_pubmed.

    Args:
        pmid: The PubMed ID of the article.
        save_file: Whether to save abstract to temp directory with
            auto-generated filename
        save_to: Specific path to save abstract (overrides save_file if provided)

    Returns:
        Formatted text containing title, abstract, and PMID.
        If save_to is provided or save_file is True, also saves the abstract
        to that file.

    Examples:
        >>> abstract = get_abstract_from_pubmed_id("31653696")
        >>> get_abstract_from_pubmed_id("31653696", save_file=True)
        # Saves with auto-generated filename in temp directory
        >>> get_abstract_from_pubmed_id("31653696", save_to="my_abstract.txt")
        # Saves to specified path
    """
    abstract_from_pubmed = aupu.get_abstract_from_pubmed(pmid)

    # Save to file if requested
    if abstract_from_pubmed:
        saved_path = file_manager.handle_file_save(
            content=abstract_from_pubmed,
            base_name="abstract",
            identifier=pmid,
            file_format="txt",
            save_file=save_file,
            save_to=save_to,
            use_temp_dir=True,
        )
        if saved_path:
            logger.info(f"Abstract saved to: {saved_path}")

    return abstract_from_pubmed


# DOIFetcher-based tools
def get_doi_fetcher_metadata(
    doi: str, email: str, save_file: bool = False, save_to: str | None = None
) -> dict[str, Any] | None:
    """
    Get metadata for a DOI using DOIFetcher. Requires a user email address.

    IMPORTANT: This tool requires an email address. If the user hasn't provided one,
    please ask them for their email address before calling this tool.

    Args:
        doi: The Digital Object Identifier of the article.
        email: Email address for API requests (required - ask user if not provided).
        save_file: Whether to save metadata to temp directory with
            auto-generated filename
        save_to: Specific path to save metadata (overrides save_file if provided)

    Returns:
        A dictionary containing the article metadata if successful, None otherwise.
        If save_to is provided or save_file is True, also saves the metadata
        to that file.

    Examples:
        >>> metadata = get_doi_fetcher_metadata("10.1038/nature12373", "user@email.com")
        >>> get_doi_fetcher_metadata(
        ...     "10.1038/nature12373", "user@email.com", save_file=True
        ... )
        # Saves with auto-generated filename in temp directory
        >>> get_doi_fetcher_metadata(
        ...     "10.1038/nature12373", "user@email.com", save_to="metadata.json"
        ... )
        # Saves to specified path
    """
    try:
        em = get_email_manager()
        validated_email = em.validate_for_api("crossref", email)
        dfr = DOIFetcher(email=validated_email)
        metadata = dfr.get_metadata(doi)

        # Save to file if requested
        if metadata:
            try:
                clean_doi = IdentifierUtils.normalize_doi(doi, "raw")  # type: ignore[arg-type]
            except IdentifierError:
                clean_doi = doi.replace("/", "_").replace(":", "_")

            saved_path = file_manager.handle_file_save(
                content=metadata,
                base_name="doi_fetcher_metadata",
                identifier=clean_doi,
                file_format="json",
                save_file=save_file,
                save_to=save_to,
                use_temp_dir=True,
            )
            if saved_path:
                logger.info(f"DOI Fetcher metadata saved to: {saved_path}")

        return metadata
    except Exception as e:
        print(f"Error retrieving metadata for DOI {doi}: {e}")
        return None


def get_unpaywall_info(
    doi: str,
    email: str,
    strict: bool = True,
    save_file: bool = False,
    save_to: str | None = None,
) -> dict[str, Any] | None:
    """
    Get Unpaywall information for a DOI to find open access versions.

    IMPORTANT: This tool requires an email address. If the user hasn't provided one,
    please ask them for their email address before calling this tool.

    Args:
        doi: The Digital Object Identifier of the article.
        email: Email address for API requests (required - ask user if not provided).
        strict: Whether to use strict mode for Unpaywall queries.
        save_file: Whether to save Unpaywall info to temp directory with
            auto-generated filename
        save_to: Specific path to save Unpaywall info (overrides save_file if provided)

    Returns:
        A dictionary containing Unpaywall information if successful, None otherwise.
        If save_to is provided or save_file is True, also saves the Unpaywall info
        to that file.

    Examples:
        >>> info = get_unpaywall_info("10.1038/nature12373", "user@email.com")
        >>> get_unpaywall_info("10.1038/nature12373", "user@email.com", save_file=True)
        # Saves with auto-generated filename in temp directory
        >>> get_unpaywall_info(
        ...     "10.1038/nature12373", "user@email.com", save_to="unpaywall.json"
        ... )
        # Saves to specified path
    """
    try:
        em = get_email_manager()
        validated_email = em.validate_for_api("unpaywall", email)
        dfr = DOIFetcher(email=validated_email)
        unpaywall_info = dfr.get_unpaywall_info(doi, strict=strict)

        # Save to file if requested
        if unpaywall_info:
            try:
                clean_doi = IdentifierUtils.normalize_doi(doi, "raw")  # type: ignore[arg-type]
            except IdentifierError:
                clean_doi = doi.replace("/", "_").replace(":", "_")

            saved_path = file_manager.handle_file_save(
                content=unpaywall_info,
                base_name="unpaywall_info",
                identifier=clean_doi,
                file_format="json",
                save_file=save_file,
                save_to=save_to,
                use_temp_dir=True,
            )
            if saved_path:
                logger.info(f"Unpaywall info saved to: {saved_path}")

        return unpaywall_info
    except Exception as e:
        print(f"Error retrieving Unpaywall info for DOI {doi}: {e}")
        return None


def get_full_text_from_doi(
    doi: str, email: str, save_file: bool = False, save_to: str | None = None
) -> str | None:
    """
    Get full text content from a DOI.

    IMPORTANT: This tool requires an email address. If the user hasn't provided one,
    please ask them for their email address before calling this tool.

    Args:
        doi: The Digital Object Identifier of the article.
        email: Email address for API requests (required - ask user if not provided).
        save_file: Whether to save full text to temp directory with
            auto-generated filename
        save_to: Specific path to save full text (overrides save_file if provided)

    Returns:
        The full text content if successful, None otherwise.
        If save_to is provided or save_file is True, also saves the full text
        to that file.

    Examples:
        >>> text = get_full_text_from_doi("10.1038/nature12373", "user@example.com")
        >>> get_full_text_from_doi(
        ...     "10.1038/nature12373", "user@example.com", save_file=True
        ... )
        # Saves with auto-generated filename in temp directory
        >>> get_full_text_from_doi(
        ...     "10.1038/nature12373", "user@example.com", save_to="paper.txt"
        ... )
        # Saves to specified path
    """
    try:
        em = get_email_manager()
        validated_email = em.validate_for_api("unpaywall", email)
        dfr = DOIFetcher(email=validated_email)
        full_text = dfr.get_full_text(doi)

        # Save to file if requested
        if full_text:
            clean_doi = IdentifierUtils.normalize_doi(doi, "raw")  # type: ignore[arg-type]
            saved_path = file_manager.handle_file_save(
                content=full_text,
                base_name="fulltext",
                identifier=clean_doi,
                file_format="txt",
                save_file=save_file,
                save_to=save_to,
                use_temp_dir=True,
            )
            if saved_path:
                logger.info(f"Full text saved to: {saved_path}")

        return full_text
    except Exception as e:
        print(f"Error retrieving full text for DOI {doi}: {e}")
        return None


def get_full_text_info(
    doi: str, email: str, save_file: bool = False, save_to: str | None = None
) -> dict[str, Any] | None:
    """
    Get full text information (metadata about full text availability) from a DOI.

    IMPORTANT: This tool requires an email address. If the user hasn't provided one,
    please ask them for their email address before calling this tool.

    Args:
        doi: The Digital Object Identifier of the article.
        email: Email address for API requests (required - ask user if not provided).
        save_file: Whether to save full text info to temp directory with
            auto-generated filename
        save_to: Specific path to save full text info (overrides save_file if provided)

    Returns:
        Information about full text availability if successful, None otherwise.
        If save_to is provided or save_file is True, also saves the full text info
        to that file.

    Examples:
        >>> info = get_full_text_info("10.1038/nature12373", "user@email.com")
        >>> get_full_text_info("10.1038/nature12373", "user@email.com", save_file=True)
        # Saves with auto-generated filename in temp directory
        >>> get_full_text_info(
        ...     "10.1038/nature12373", "user@email.com", save_to="fulltext_info.json"
        ... )
        # Saves to specified path
    """
    try:
        em = get_email_manager()
        validated_email = em.validate_for_api("unpaywall", email)
        dfr = DOIFetcher(email=validated_email)
        result = dfr.get_full_text_info(doi)
        if result is None:
            return None

        full_text_info = {
            "success": getattr(result, "success", False),
            "info": str(result),
        }

        # Save to file if requested
        if full_text_info:
            try:
                clean_doi = IdentifierUtils.normalize_doi(doi, "raw")  # type: ignore[arg-type]
            except IdentifierError:
                clean_doi = doi.replace("/", "_").replace(":", "_")

            saved_path = file_manager.handle_file_save(
                content=full_text_info,
                base_name="fulltext_info",
                identifier=clean_doi,
                file_format="json",
                save_file=save_file,
                save_to=save_to,
                use_temp_dir=True,
            )
            if saved_path:
                logger.info(f"Full text info saved to: {saved_path}")

        return full_text_info
    except Exception as e:
        print(f"Error retrieving full text info for DOI {doi}: {e}")
        return None


def get_text_from_pdf_url(
    pdf_url: str, email: str, save_file: bool = False, save_to: str | None = None
) -> str | None:
    """
    Extract text from a PDF URL using DOIFetcher.

    IMPORTANT: This tool requires an email address. If the user hasn't provided one,
    please ask them for their email address before calling this tool.

    Args:
        pdf_url: URL of the PDF to extract text from.
        email: Email address for API requests (required - ask user if not provided).
        save_file: Whether to save extracted text to temp directory with
            auto-generated filename
        save_to: Specific path to save extracted text (overrides save_file if provided)

    Returns:
        The extracted text if successful, None otherwise.
        If save_to is provided or save_file is True, also saves the extracted text
        to that file.

    Examples:
        >>> text = get_text_from_pdf_url(
        ...     "https://example.com/paper.pdf", "user@email.com"
        ... )
        >>> get_text_from_pdf_url(
        ...     "https://example.com/paper.pdf", "user@email.com", save_file=True
        ... )
        # Saves with auto-generated filename in temp directory
        >>> get_text_from_pdf_url(
        ...     "https://example.com/paper.pdf",
        ...     "user@email.com",
        ...     save_to="pdf_text.txt"
        ... )
        # Saves to specified path
    """
    try:
        em = get_email_manager()
        validated_email = em.validate_for_api("unpaywall", email)
        dfr = DOIFetcher(email=validated_email)
        extracted_text = dfr.text_from_pdf_url(pdf_url)

        # Save to file if requested
        if extracted_text:
            url_identifier = (
                pdf_url.split("/")[-1].replace(".pdf", "")
                if "/" in pdf_url
                else "pdf_extract"
            )
            saved_path = file_manager.handle_file_save(
                content=extracted_text,
                base_name="pdf_url_text",
                identifier=url_identifier,
                file_format="txt",
                save_file=save_file,
                save_to=save_to,
                use_temp_dir=True,
            )
            if saved_path:
                logger.info(f"PDF URL text saved to: {saved_path}")

        return extracted_text
    except Exception as e:
        print(f"Error extracting text from PDF URL {pdf_url}: {e}")
        return None


def extract_pdf_text(
    pdf_url: str, save_file: bool = False, save_to: str | None = None
) -> str | None:
    """
    Extract text from a PDF URL using the standalone pdf_fetcher.

    Args:
        pdf_url: URL of the PDF to extract text from.
        save_file: Whether to save extracted text to temp directory with
            auto-generated filename
        save_to: Specific path to save extracted text (overrides save_file if provided)

    Returns:
        The extracted text if successful, None otherwise.
        If save_to is provided or save_file is True, also saves the extracted
        text to that file.

    Examples:
        >>> text = extract_pdf_text("https://example.com/paper.pdf")
        >>> extract_pdf_text("https://example.com/paper.pdf", save_file=True)
        # Saves with auto-generated filename in temp directory
        >>> extract_pdf_text("https://example.com/paper.pdf", save_to="extracted.txt")
        # Saves to specified path
    """
    try:
        result = extract_text_from_pdf(pdf_url)
        # Check if result is an error message
        if result and "Error extracting PDF text:" in str(result):
            print(f"Error extracting text from PDF URL {pdf_url}: {result}")
            return None

        # Save to file if requested
        if result:
            url_identifier = (
                pdf_url.split("/")[-1].replace(".pdf", "")
                if "/" in pdf_url
                else "pdf_extract"
            )
            saved_path = file_manager.handle_file_save(
                content=result,
                base_name="pdf_text",
                identifier=url_identifier,
                file_format="txt",
                save_file=save_file,
                save_to=save_to,
                use_temp_dir=True,
            )
            if saved_path:
                logger.info(f"PDF text saved to: {saved_path}")

        return result
    except Exception as e:
        print(f"Error extracting text from PDF URL {pdf_url}: {e}")
        return None


def clean_text(
    text: str, email: str, save_file: bool = False, save_to: str | None = None
) -> str:
    """
    Clean text using DOIFetcher's text cleaning functionality.

    IMPORTANT: This tool requires an email address. If the user hasn't provided one,
    please ask them for their email address before calling this tool.

    Args:
        text: The text to clean.
        email: Email address for API requests (required - ask user if not provided).
        save_file: Whether to save cleaned text to temp directory with
            auto-generated filename
        save_to: Specific path to save cleaned text (overrides save_file if provided)

    Returns:
        The cleaned text.
        If save_to is provided or save_file is True, also saves the cleaned text
        to that file.

    Examples:
        >>> cleaned = clean_text("messy text", "user@email.com")
        >>> clean_text("messy text", "user@email.com", save_file=True)
        # Saves with auto-generated filename in temp directory
        >>> clean_text("messy text", "user@email.com", save_to="cleaned.txt")
        # Saves to specified path
    """
    try:
        em = get_email_manager()
        validated_email = em.validate_for_api("crossref", email)
        dfr = DOIFetcher(email=validated_email)
        cleaned_text = dfr.clean_text(text)

        # Save to file if requested
        if cleaned_text and (save_file or save_to):
            # Generate identifier from text preview
            text_preview = text[:50].replace(" ", "_").replace("\n", "_")
            saved_path = file_manager.handle_file_save(
                content=cleaned_text,
                base_name="cleaned_text",
                identifier=text_preview,
                file_format="txt",
                save_file=save_file,
                save_to=save_to,
                use_temp_dir=True,
            )
            if saved_path:
                logger.info(f"Cleaned text saved to: {saved_path}")

        return cleaned_text
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


def get_doi_text(
    doi: str, save_file: bool = False, save_to: str | None = None
) -> str | None:
    """
    Get full text from a DOI.

    Args:
        doi: The Digital Object Identifier.
        save_file: Whether to save full text to temp directory with
            auto-generated filename
        save_to: Specific path to save full text (overrides save_file if provided)

    Returns:
        The full text if successful, None otherwise.
        If save_to is provided or save_file is True, also saves the full text
        to that file.

    Examples:
        >>> text = get_doi_text("10.1038/nature12373")
        >>> get_doi_text("10.1038/nature12373", save_file=True)
        # Saves with auto-generated filename in temp directory
        >>> get_doi_text("10.1038/nature12373", save_to="paper_text.txt")
        # Saves to specified path
    """
    try:
        full_text = aupu.get_doi_text(doi)

        # Save to file if requested
        if full_text:
            try:
                clean_doi = IdentifierUtils.normalize_doi(doi, "raw")  # type: ignore[arg-type]
            except IdentifierError:
                clean_doi = doi.replace("/", "_").replace(":", "_")

            saved_path = file_manager.handle_file_save(
                content=full_text,
                base_name="fulltext",
                identifier=clean_doi,
                file_format="txt",
                save_file=save_file,
                save_to=save_to,
                use_temp_dir=True,
            )
            if saved_path:
                logger.info(f"Full text saved to: {saved_path}")

        return full_text
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


def get_pmcid_text(
    pmcid: str, save_file: bool = False, save_to: str | None = None
) -> str | None:
    """
    Get full text from a PMC ID.

    Args:
        pmcid: The PMC ID (e.g., 'PMC1234567').
        save_file: Whether to save full text to temp directory with
            auto-generated filename
        save_to: Specific path to save full text (overrides save_file if provided)

    Returns:
        The full text if successful, None otherwise.
        If save_to is provided or save_file is True, also saves the full text
        to that file.

    Examples:
        >>> text = get_pmcid_text("PMC1234567")
        >>> get_pmcid_text("PMC1234567", save_file=True)
        # Saves with auto-generated filename in temp directory
        >>> get_pmcid_text("PMC1234567", save_to="pmc_text.txt")
        # Saves to specified path
    """
    try:
        full_text = aupu.get_pmcid_text(pmcid)

        # Save to file if requested
        if full_text:
            try:
                clean_pmcid = IdentifierUtils.normalize_pmcid(pmcid, "raw")  # type: ignore[arg-type]
            except IdentifierError:
                clean_pmcid = str(pmcid).replace(":", "_")

            saved_path = file_manager.handle_file_save(
                content=full_text,
                base_name="pmcid_text",
                identifier=clean_pmcid,
                file_format="txt",
                save_file=save_file,
                save_to=save_to,
                use_temp_dir=True,
            )
            if saved_path:
                logger.info(f"PMC text saved to: {saved_path}")

        return full_text
    except Exception as e:
        print(f"Error getting text for PMCID {pmcid}: {e}")
        return None


def get_pmid_text(
    pmid: str, save_file: bool = False, save_to: str | None = None
) -> str | None:
    """
    Get full text from a PubMed ID.

    Args:
        pmid: The PubMed ID.
        save_file: Whether to save full text to temp directory with
            auto-generated filename
        save_to: Specific path to save full text (overrides save_file if provided)

    Returns:
        The full text if successful, None otherwise.
        If save_to is provided or save_file is True, also saves the full text
        to that file.

    Examples:
        >>> text = get_pmid_text("23851394")
        >>> get_pmid_text("23851394", save_file=True)
        # Saves with auto-generated filename in temp directory
        >>> get_pmid_text("23851394", save_to="pmid_text.txt")
        # Saves to specified path
    """
    try:
        full_text = aupu.get_pmid_text(pmid)

        # Save to file if requested
        if full_text:
            try:
                clean_pmid = IdentifierUtils.normalize_pmid(pmid, "raw")  # type: ignore[arg-type]
            except IdentifierError:
                clean_pmid = str(pmid).replace(":", "_")

            saved_path = file_manager.handle_file_save(
                content=full_text,
                base_name="pmid_text",
                identifier=clean_pmid,
                file_format="txt",
                save_file=save_file,
                save_to=save_to,
                use_temp_dir=True,
            )
            if saved_path:
                logger.info(f"PMID text saved to: {saved_path}")

        return full_text
    except Exception as e:
        print(f"Error getting text for PMID {pmid}: {e}")
        return None


def get_full_text_from_bioc(
    pmid: str, save_file: bool = False, save_to: str | None = None
) -> str | None:
    """
    Get full text from BioC format for a PubMed ID.

    Args:
        pmid: The PubMed ID.
        save_file: Whether to save BioC text to temp directory with
            auto-generated filename
        save_to: Specific path to save BioC text (overrides save_file if provided)

    Returns:
        The full text from BioC if successful, None otherwise.
        If save_to is provided or save_file is True, also saves the BioC text
        to that file.

    Examples:
        >>> text = get_full_text_from_bioc("23851394")
        >>> get_full_text_from_bioc("23851394", save_file=True)
        # Saves with auto-generated filename in temp directory
        >>> get_full_text_from_bioc("23851394", save_to="bioc_text.txt")
        # Saves to specified path
    """
    try:
        bioc_text = aupu.get_full_text_from_bioc(pmid)

        # Save to file if requested
        if bioc_text:
            try:
                clean_pmid = IdentifierUtils.normalize_pmid(pmid, "raw")  # type: ignore[arg-type]
            except IdentifierError:
                clean_pmid = str(pmid).replace(":", "_")

            saved_path = file_manager.handle_file_save(
                content=bioc_text,
                base_name="bioc_text",
                identifier=clean_pmid,
                file_format="txt",
                save_file=save_file,
                save_to=save_to,
                use_temp_dir=True,
            )
            if saved_path:
                logger.info(f"BioC text saved to: {saved_path}")

        return bioc_text
    except Exception as e:
        print(f"Error getting BioC text for PMID {pmid}: {e}")
        return None


def search_pubmed_for_pmids(
    query: str,
    max_results: int = 20,
    save_file: bool = False,
    save_to: str | None = None,
) -> dict[str, Any] | None:
    """
    Search PubMed for articles using keywords and return PMIDs with metadata.

    Args:
        query: The search query/keywords to search for in PubMed.
        max_results: Maximum number of PMIDs to return (default: 20).
        save_file: Whether to save search results to temp directory with
            auto-generated filename
        save_to: Specific path to save search results (overrides save_file if provided)

    Returns:
        A dictionary containing PMIDs list, total count, and query info if
        successful, None otherwise.
        If save_to is provided or save_file is True, also saves the search results
        to that file.

    Examples:
        >>> results = search_pubmed_for_pmids("CRISPR")
        >>> search_pubmed_for_pmids("CRISPR", save_file=True)
        # Saves with auto-generated filename in temp directory
        >>> search_pubmed_for_pmids("CRISPR", save_to="pubmed_search.json")
        # Saves to specified path
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

            search_results = {
                "pmids": pmids,
                "total_count": total_count,
                "returned_count": len(pmids),
                "query": query,
                "max_results": max_results,
            }
        else:
            print(f"No results found for query: {query}")
            search_results = {
                "pmids": [],
                "total_count": 0,
                "returned_count": 0,
                "query": query,
                "max_results": max_results,
            }

        # Save to file if requested
        if search_results and (save_file or save_to):
            saved_path = file_manager.handle_file_save(
                content=search_results,
                base_name="pubmed_search",
                identifier=query.replace(" ", "_"),
                file_format="json",
                save_file=save_file,
                save_to=save_to,
                use_temp_dir=True,
            )
            if saved_path:
                logger.info(f"PubMed search results saved to: {saved_path}")

        return search_results

    except Exception as e:
        print(f"Error searching PubMed for query '{query}': {e}")
        return None


# Enhanced identifier conversion tools
def doi_to_pmcid(doi: str) -> str | None:
    """Convert DOI to PMCID using NCBI ID Converter API.

    Supports multiple DOI input formats:
    - Raw DOI: 10.1038/nature12373
    - CURIE format: doi:10.1038/nature12373
    - URL formats: https://doi.org/10.1038/nature12373

    Args:
        doi: The Digital Object Identifier in any supported format

    Returns:
        PMCID in standard format (PMC1234567) or None if conversion fails

    Examples:
        >>> doi_to_pmcid("10.1038/nature12373")
        'PMC3737249'
        >>> doi_to_pmcid("doi:10.1038/nature12373")
        'PMC3737249'
    """
    try:
        return IdentifierConverter.doi_to_pmcid(doi)
    except Exception as e:
        logger.warning(f"Error converting DOI to PMCID: {doi} - {e}")
        return None


def pmid_to_pmcid(pmid: str | int) -> str | None:
    """Convert PMID to PMCID using PubMed E-utilities.

    Supports multiple PMID input formats:
    - Raw PMID: 23851394
    - Prefixed: PMID:23851394
    - Colon-separated: pmid:23851394

    Args:
        pmid: The PubMed ID in any supported format

    Returns:
        PMCID in standard format (PMC1234567) or None if conversion fails

    Examples:
        >>> pmid_to_pmcid("23851394")
        'PMC3737249'
        >>> pmid_to_pmcid("PMID:23851394")
        'PMC3737249'
    """
    try:
        return IdentifierConverter.pmid_to_pmcid(pmid)
    except Exception as e:
        logger.warning(f"Error converting PMID to PMCID: {pmid} - {e}")
        return None


def pmcid_to_doi(pmcid: str | int) -> str | None:
    """Convert PMCID to DOI via PMID lookup.

    Supports multiple PMCID input formats:
    - Full PMCID: PMC3737249
    - Numeric only: 3737249
    - Prefixed: PMC:3737249

    Args:
        pmcid: The PMC ID in any supported format

    Returns:
        DOI in standard format (10.1234/example) or None if conversion fails

    Examples:
        >>> pmcid_to_doi("PMC3737249")
        '10.1038/nature12373'
        >>> pmcid_to_doi("3737249")
        '10.1038/nature12373'
    """
    try:
        return IdentifierConverter.pmcid_to_doi(pmcid)
    except Exception as e:
        logger.warning(f"Error converting PMCID to DOI: {pmcid} - {e}")
        return None


def get_all_identifiers(
    identifier: str, save_file: bool = False, save_to: str | None = None
) -> dict[str, str | None]:
    """Get all available identifiers (DOI, PMID, PMCID) for any given identifier.

    Supports all identifier formats and automatically detects type.

    Args:
        identifier: Any scientific identifier (DOI, PMID, or PMCID) in any format
        save_file: Whether to save all identifiers to temp directory with
            auto-generated filename
        save_to: Specific path to save all identifiers (overrides save_file if provided)

    Returns:
        Dictionary with all available identifiers and metadata
        If save_to is provided or save_file is True, also saves the identifiers
        to that file.

    Examples:
        >>> get_all_identifiers("10.1038/nature12373")
        >>> get_all_identifiers("10.1038/nature12373", save_file=True)
        # Saves with auto-generated filename in temp directory
        >>> get_all_identifiers("10.1038/nature12373", save_to="identifiers.json")
        # Saves to specified path
        {
            'doi': '10.1038/nature12373',
            'pmid': '23851394',
            'pmcid': 'PMC3737249',
            'input_type': 'doi'
        }
    """
    try:
        all_identifiers = IdentifierConverter.get_comprehensive_ids(identifier)

        # Save to file if requested
        if (
            all_identifiers
            and "error" not in all_identifiers
            and (save_file or save_to)
        ):
            clean_identifier = str(identifier).replace("/", "_").replace(":", "_")
            saved_path = file_manager.handle_file_save(
                content=all_identifiers,
                base_name="all_identifiers",
                identifier=clean_identifier,
                file_format="json",
                save_file=save_file,
                save_to=save_to,
                use_temp_dir=True,
            )
            if saved_path:
                logger.info(f"All identifiers saved to: {saved_path}")

        return all_identifiers
    except Exception as e:
        logger.warning(f"Error getting comprehensive IDs for: {identifier} - {e}")
        return {
            "doi": None,
            "pmid": None,
            "pmcid": None,
            "input_type": "unknown",
            "error": str(e),
        }


def validate_identifier(identifier: str, expected_type: str | None = None) -> bool:
    """Validate if an identifier is properly formatted.

    Args:
        identifier: The identifier to validate
        expected_type: Optional expected type ('doi', 'pmid', 'pmcid')

    Returns:
        True if valid, False otherwise

    Examples:
        >>> validate_identifier("10.1038/nature12373")
        True
        >>> validate_identifier("invalid-doi")
        False
        >>> validate_identifier("23851394", "pmid")
        True
    """
    try:
        typed_expected_type: IDType | None = None
        if expected_type in ("doi", "pmid", "pmcid", "unknown"):
            typed_expected_type = expected_type  # type: ignore
        return IdentifierUtils.validate_identifier(identifier, typed_expected_type)
    except Exception:
        return False


# Citation and reference tools
def get_paper_references(
    doi: str, save_file: bool = False, save_to: str | None = None
) -> list[dict] | None:
    """Get list of references cited by a paper.

    Args:
        doi: The DOI of the paper (supports all DOI formats)
        save_file: Whether to save references to temp directory with
            auto-generated filename
        save_to: Specific path to save references (overrides save_file if provided)

    Returns:
        List of reference dictionaries with DOI, title, journal, etc. or None if fails
        If save_to is provided or save_file is True, also saves the references
        to that file.

    Examples:
        >>> refs = get_paper_references("10.1038/nature12373")
        >>> get_paper_references("10.1038/nature12373", save_file=True)
        # Saves with auto-generated filename in temp directory
        >>> get_paper_references("10.1038/nature12373", save_to="references.json")
        # Saves to specified path
        >>> len(refs) if refs else 0
        25
        >>> refs[0]['title'] if refs else None
        'Reference paper title'
    """
    try:
        references = CitationUtils.get_references_crossref(doi)

        # Save to file if requested
        if references:
            try:
                clean_doi = IdentifierUtils.normalize_doi(doi, "raw")  # type: ignore[arg-type]
            except IdentifierError:
                clean_doi = doi.replace("/", "_").replace(":", "_")

            saved_path = file_manager.handle_file_save(
                content=references,
                base_name="references",
                identifier=clean_doi,
                file_format="json",
                save_file=save_file,
                save_to=save_to,
                use_temp_dir=True,
            )
            if saved_path:
                logger.info(f"Paper references saved to: {saved_path}")

        return references
    except Exception as e:
        logger.warning(f"Error getting references for DOI: {doi} - {e}")
        return None


def get_paper_citations(
    doi: str, save_file: bool = False, save_to: str | None = None
) -> list[dict] | None:
    """Get list of papers that cite a given paper.

    Args:
        doi: The DOI of the paper (supports all DOI formats)
        save_file: Whether to save citations to temp directory with
            auto-generated filename
        save_to: Specific path to save citations (overrides save_file if provided)

    Returns:
        List of citing paper dictionaries with DOI, title, authors, etc. or
        None if fails
        If save_to is provided or save_file is True, also saves the citations
        to that file.

    Examples:
        >>> citations = get_paper_citations("10.1038/nature12373")
        >>> get_paper_citations("10.1038/nature12373", save_file=True)
        # Saves with auto-generated filename in temp directory
        >>> get_paper_citations("10.1038/nature12373", save_to="citations.json")
        # Saves to specified path
        >>> len(citations) if citations else 0
        150
        >>> citations[0]['title'] if citations else None
        'Citing paper title'
    """
    try:
        citations = CitationUtils.get_citations_crossref(doi)

        # Save to file if requested
        if citations:
            try:
                clean_doi = IdentifierUtils.normalize_doi(doi, "raw")  # type: ignore[arg-type]
            except IdentifierError:
                clean_doi = doi.replace("/", "_").replace(":", "_")

            saved_path = file_manager.handle_file_save(
                content=citations,
                base_name="citations",
                identifier=clean_doi,
                file_format="json",
                save_file=save_file,
                save_to=save_to,
                use_temp_dir=True,
            )
            if saved_path:
                logger.info(f"Paper citations saved to: {saved_path}")

        return citations
    except Exception as e:
        logger.warning(f"Error getting citations for DOI: {doi} - {e}")
        return None


def get_citation_network(
    doi: str, save_file: bool = False, save_to: str | None = None
) -> dict | None:
    """Get comprehensive citation network information from OpenAlex.

    Args:
        doi: The DOI of the paper (supports all DOI formats)
        save_file: Whether to save citation network to temp directory with
            auto-generated filename
        save_to: Specific path to save citation network (overrides save_file if
            provided)

    Returns:
        Dictionary with citation counts, concepts, referenced works, etc. or
        None if fails
        If save_to is provided or save_file is True, also saves the citation network
        to that file.

    Examples:
        >>> network = get_citation_network("10.1038/nature12373")
        >>> get_citation_network("10.1038/nature12373", save_file=True)
        # Saves with auto-generated filename in temp directory
        >>> get_citation_network("10.1038/nature12373", save_to="network.json")
        # Saves to specified path
        >>> network['cited_by_count'] if network else 0
        245
        >>> network['concepts'][0]['display_name'] if network else None
        'Genetics'
    """
    try:
        citation_network = CitationUtils.get_citation_network_openalex(doi)

        # Save to file if requested
        if citation_network:
            try:
                clean_doi = IdentifierUtils.normalize_doi(doi, "raw")  # type: ignore[arg-type]
            except IdentifierError:
                clean_doi = doi.replace("/", "_").replace(":", "_")

            saved_path = file_manager.handle_file_save(
                content=citation_network,
                base_name="citation_network",
                identifier=clean_doi,
                file_format="json",
                save_file=save_file,
                save_to=save_to,
                use_temp_dir=True,
            )
            if saved_path:
                logger.info(f"Citation network saved to: {saved_path}")

        return citation_network
    except Exception as e:
        logger.warning(f"Error getting citation network for DOI: {doi} - {e}")
        return None


def find_related_papers(
    doi: str, max_results: int = 10, save_file: bool = False, save_to: str | None = None
) -> list[dict] | None:
    """Find papers related to a given paper through citations and references.

    Args:
        doi: The DOI of the reference paper (supports all DOI formats)
        max_results: Maximum number of related papers to return (default: 10)
        save_file: Whether to save related papers to temp directory with
            auto-generated filename
        save_to: Specific path to save related papers (overrides save_file if provided)

    Returns:
        List of related paper dictionaries or None if fails
        If save_to is provided or save_file is True, also saves the related papers
        to that file.

    Examples:
        >>> related = find_related_papers("10.1038/nature12373", 5)
        >>> find_related_papers("10.1038/nature12373", 5, save_file=True)
        # Saves with auto-generated filename in temp directory
        >>> find_related_papers("10.1038/nature12373", 5, save_to="related.json")
        # Saves to specified path
        >>> len(related) if related else 0
        5
        >>> related[0]['relationship'] if related else None
        'cites_this_paper'
    """
    try:
        related_papers = CitationUtils.find_related_papers(doi, max_results)

        # Save to file if requested
        if related_papers:
            try:
                clean_doi = IdentifierUtils.normalize_doi(doi, "raw")  # type: ignore[arg-type]
            except IdentifierError:
                clean_doi = doi.replace("/", "_").replace(":", "_")

            saved_path = file_manager.handle_file_save(
                content=related_papers,
                base_name="related_papers",
                identifier=clean_doi,
                file_format="json",
                save_file=save_file,
                save_to=save_to,
                use_temp_dir=True,
            )
            if saved_path:
                logger.info(f"Related papers saved to: {saved_path}")

        return related_papers
    except Exception as e:
        logger.warning(f"Error finding related papers for DOI: {doi} - {e}")
        return None


def get_comprehensive_citation_info(
    doi: str, save_file: bool = False, save_to: str | None = None
) -> dict[str, str | dict | list | None]:
    """Get comprehensive citation information from multiple sources.

    Retrieves data from CrossRef, OpenAlex, and Semantic Scholar APIs.

    Args:
        doi: The DOI of the paper (supports all DOI formats)
        save_file: Whether to save comprehensive citation info to temp directory with
            auto-generated filename
        save_to: Specific path to save comprehensive citation info (overrides
            save_file if provided)

    Returns:
        Dictionary with data from all sources
        If save_to is provided or save_file is True, also saves the comprehensive
        citation info to that file.

    Examples:
        >>> info = get_comprehensive_citation_info("10.1038/nature12373")
        >>> get_comprehensive_citation_info("10.1038/nature12373", save_file=True)
        # Saves with auto-generated filename in temp directory
        >>> get_comprehensive_citation_info(
        ...     "10.1038/nature12373", save_to="comprehensive.json"
        ... )
        # Saves to specified path
        >>> info.keys()
        dict_keys(['crossref_references', 'crossref_citations',
                   'openalex_network', 'semantic_scholar'])
    """
    try:
        comprehensive_info = CitationUtils.get_comprehensive_citation_info(doi)

        # Save to file if requested
        if comprehensive_info and "error" not in comprehensive_info:
            try:
                clean_doi = IdentifierUtils.normalize_doi(doi, "raw")  # type: ignore[arg-type]
            except IdentifierError:
                clean_doi = doi.replace("/", "_").replace(":", "_")

            saved_path = file_manager.handle_file_save(
                content=comprehensive_info,
                base_name="comprehensive_citation_info",
                identifier=clean_doi,
                file_format="json",
                save_file=save_file,
                save_to=save_to,
                use_temp_dir=True,
            )
            if saved_path:
                logger.info(f"Comprehensive citation info saved to: {saved_path}")

        return comprehensive_info
    except Exception as e:
        logger.warning(
            f"Error getting comprehensive citation info for DOI: {doi} - {e}"
        )
        return {"error": str(e)}


def convert_identifier_format(
    identifier: str,
    output_format: str = "raw",
    save_file: bool = False,
    save_to: str | None = None,
) -> dict[str, str | None]:
    """Convert an identifier to different formats.

    Supports format conversion for DOIs, PMIDs, and PMCIDs:
    - DOI formats: raw (10.1234/example), curie (doi:10.1234/example),
      url (https://doi.org/10.1234/example)
    - PMID formats: raw (23851394), prefixed (PMID:23851394),
      curie (pmid:23851394)
    - PMCID formats: raw (PMC3737249), prefixed (PMC3737249),
      curie (pmcid:PMC3737249)

    Args:
        identifier: Any scientific identifier in any supported format
        output_format: Desired output format ("raw", "curie", "url", "prefixed")
        save_file: Whether to save conversion result to temp directory with
            auto-generated filename
        save_to: Specific path to save conversion result (overrides save_file if
            provided)

    Returns:
        Dictionary with conversion results and metadata
        If save_to is provided or save_file is True, also saves the conversion result
        to that file.

    Examples:
        >>> convert_identifier_format("10.1038/nature12373", "curie")
        >>> convert_identifier_format("10.1038/nature12373", "curie", save_file=True)
        # Saves with auto-generated filename in temp directory
        >>> convert_identifier_format(
        ...     "10.1038/nature12373", "curie", save_to="conversion.json"
        ... )
        # Saves to specified path
        {'input': '10.1038/nature12373', 'output': 'doi:10.1038/nature12373',
         'input_type': 'doi', 'output_format': 'curie'}
        >>> convert_identifier_format("doi:10.1038/nature12373", "url")
        {'input': 'doi:10.1038/nature12373',
         'output': 'https://doi.org/10.1038/nature12373',
         'input_type': 'doi', 'output_format': 'url'}
    """
    try:
        # First identify and normalize the input
        id_info = IdentifierUtils.normalize_identifier(identifier)
        id_type = id_info["type"]

        # Convert to desired format
        if id_type == "doi":
            converted = IdentifierUtils.normalize_doi(identifier, output_format)  # type: ignore[arg-type]
        elif id_type == "pmid":
            converted = IdentifierUtils.normalize_pmid(identifier, output_format)  # type: ignore[arg-type]
        elif id_type == "pmcid":
            converted = IdentifierUtils.normalize_pmcid(identifier, output_format)  # type: ignore[arg-type]
        else:
            return {
                "input": identifier,
                "output": None,
                "input_type": id_type,
                "output_format": output_format,
                "error": f"Unsupported identifier type: {id_type}",
            }

        conversion_result: dict[str, str | None] = {
            "input": identifier,
            "output": converted,
            "input_type": id_type,
            "output_format": output_format,
        }

        # Save to file if requested
        if (
            conversion_result
            and "error" not in conversion_result
            and (save_file or save_to)
        ):
            clean_identifier = str(identifier).replace("/", "_").replace(":", "_")
            saved_path = file_manager.handle_file_save(
                content=conversion_result,
                base_name="conversion",
                identifier=f"{clean_identifier}_to_{output_format}",
                file_format="json",
                save_file=save_file,
                save_to=save_to,
                use_temp_dir=True,
            )
            if saved_path:
                logger.info(f"Identifier conversion saved to: {saved_path}")

        return conversion_result

    except IdentifierError as e:
        logger.warning(f"Error converting identifier format: {identifier} - {e}")
        return {
            "input": identifier,
            "output": None,
            "input_type": "unknown",
            "output_format": output_format,
            "error": str(e),
        }
