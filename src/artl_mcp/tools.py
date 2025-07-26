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


def _apply_content_limits(
    content: str, saved_path: str | None = None, max_size: int = 100 * 1024
) -> tuple[str, bool]:
    """Apply content size limits for LLM responses.

    Args:
        content: Original content
        saved_path: Path where full content is saved (for messaging)
        max_size: Maximum content size in characters

    Returns:
        Tuple of (limited_content, was_truncated)
    """
    content_length = len(content)

    if content_length > max_size:
        truncate_point = max_size - 200
        file_msg = (
            f"Full content saved to: {saved_path}"
            if saved_path
            else "file not saved - use save_file=True or save_to=path"
        )
        truncation_msg = (
            f"\n\n[CONTENT TRUNCATED - Showing first {truncate_point:,} "
            f"of {content_length:,} characters. {file_msg}]"
        )
        limited_content = content[:truncate_point] + truncation_msg
        logger.info(
            f"Large content ({content_length:,} chars) truncated for LLM response"
        )
        return limited_content, True
    elif content_length > 50 * 1024:  # 50KB warning threshold
        logger.warning(
            f"Large content ({content_length:,} characters) may approach token limits"
        )
        return content, False
    else:
        return content, False


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
        Dictionary containing article metadata from CrossRef API with save info,
        or None if retrieval fails. When file saving is requested, includes
        'saved_to' key with the file path.

    Examples:
        >>> metadata = get_doi_metadata("10.1038/nature12373")
        >>> metadata["message"]["title"][0]  # Access CrossRef data
        'Article title here'
        >>> result = get_doi_metadata("10.1038/nature12373", save_file=True)
        >>> result["saved_to"]  # Path where file was saved
        '/Users/.../Documents/artl-mcp/metadata_....json'
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
        saved_path = None
        if save_file or save_to:
            try:
                saved_path = file_manager.handle_file_save(
                    content=data,
                    base_name="metadata",
                    identifier=clean_doi,
                    file_format="json",
                    save_file=save_file,
                    save_to=save_to,
                    use_temp_dir=False,
                )
                if saved_path:
                    logger.info(f"Metadata saved to: {saved_path}")
            except Exception as e:
                logger.warning(f"Failed to save metadata file: {e}")

        # Return API response with save path info if file was saved
        if saved_path:
            data["saved_to"] = str(saved_path)

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
        Dictionary containing search results with save info if successful,
        None otherwise.
        When file saving is requested, includes 'saved_to' key with the file path.
        Format matches habanero.Crossref().works(query=query)

    Examples:
        >>> results = search_papers_by_keyword("CRISPR")
        >>> results["message"]["items"]  # Access search results
        >>> results = search_papers_by_keyword("CRISPR", save_file=True)
        >>> results["saved_to"]  # Path where file was saved
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
        saved_path = None
        if save_file or save_to:
            try:
                saved_path = file_manager.handle_file_save(
                    content=data,
                    base_name="search",
                    identifier=query.replace(" ", "_"),
                    file_format="json",
                    save_file=save_file,
                    save_to=save_to,
                    use_temp_dir=False,
                )
                if saved_path:
                    logger.info(f"Search results saved to: {saved_path}")
            except Exception as e:
                logger.warning(f"Failed to save search results file: {e}")

        # Return search results with save path info if file was saved
        if saved_path:
            data["saved_to"] = str(saved_path)

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
        Dictionary containing search results with save info if successful,
        None otherwise.
        When file saving is requested, includes 'saved_to' key with the file path.

    Examples:
        >>> results = search_recent_papers("CRISPR", years_back=3)
        >>> results["message"]["items"]  # Access search results
        >>> results = search_recent_papers("CRISPR", save_file=True)
        >>> results["saved_to"]  # Path where file was saved
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
) -> dict[str, str | bool | None] | None:
    """Get formatted abstract text from a PubMed ID.

    Returns title, abstract text, and PMID in a formatted structure with
    normalized whitespace. This is a wrapper around get_abstract_from_pubmed.

    Args:
        pmid: The PubMed ID of the article.
        save_file: Whether to save abstract to temp directory with
            auto-generated filename
        save_to: Specific path to save abstract (overrides save_file if provided)

    Returns:
        Dictionary with 'content' and 'saved_to' keys if successful, None otherwise.
        - content: The formatted abstract text
        - saved_to: Path where file was saved (None if not saved)

    Examples:
        >>> result = get_abstract_from_pubmed_id("31653696")
        >>> result['content']  # The abstract text
        >>> result = get_abstract_from_pubmed_id("31653696", save_file=True)
        >>> result['saved_to']  # Path where file was saved
    """
    abstract_from_pubmed = aupu.get_abstract_from_pubmed(pmid)
    if not abstract_from_pubmed:
        # Return structured response even when no abstract is available
        return {
            "content": "",
            "saved_to": None,
            "truncated": False,
        }

    saved_path = None
    # Save to file if requested
    if save_file or save_to:
        try:
            saved_path = file_manager.handle_file_save(
                content=abstract_from_pubmed,
                base_name="abstract",
                identifier=pmid,
                file_format="txt",
                save_file=save_file,
                save_to=save_to,
                use_temp_dir=False,
            )
            if saved_path:
                logger.info(f"Abstract saved to: {saved_path}")
        except Exception as e:
            logger.warning(f"Failed to save abstract file: {e}")

    # Apply content size limits for return to LLM (abstracts can be large)
    limited_content, was_truncated = _apply_content_limits(
        abstract_from_pubmed, str(saved_path) if saved_path else None
    )

    return {
        "content": limited_content,
        "saved_to": str(saved_path) if saved_path else None,
        "truncated": was_truncated,
    }


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
        Dictionary containing article metadata with save info if successful,
        None otherwise.
        When file saving is requested, includes 'saved_to' key with the file path.

    Examples:
        >>> result = get_doi_fetcher_metadata("10.1038/nature12373", "user@email.com")
        >>> result['saved_to']  # None if not saved
        >>> result = get_doi_fetcher_metadata(
        ...     "10.1038/nature12373", "user@email.com", save_file=True
        ... )
        >>> result['saved_to']  # Path where file was saved
    """
    try:
        em = get_email_manager()
        validated_email = em.validate_for_api("crossref", email)
        dfr = DOIFetcher(email=validated_email)
        metadata = dfr.get_metadata(doi)

        # Save to file if requested
        saved_path = None
        if metadata and (save_file or save_to):
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
                use_temp_dir=False,
            )
            if saved_path:
                logger.info(f"DOI Fetcher metadata saved to: {saved_path}")

        # Return metadata with save path info if file was saved
        if saved_path and metadata:
            metadata["saved_to"] = str(saved_path)

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
        Dictionary containing Unpaywall information with save info if successful,
        None otherwise.
        When file saving is requested, includes 'saved_to' key with the file path.

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
        saved_path = None
        if unpaywall_info and (save_file or save_to):
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
                use_temp_dir=False,
            )
            if saved_path:
                logger.info(f"Unpaywall info saved to: {saved_path}")

        # Return unpaywall info with save path info if file was saved
        if saved_path and unpaywall_info:
            unpaywall_info["saved_to"] = str(saved_path)

        return unpaywall_info
    except Exception as e:
        print(f"Error retrieving Unpaywall info for DOI {doi}: {e}")
        return None


def get_full_text_from_doi(
    doi: str, email: str, save_file: bool = False, save_to: str | None = None
) -> dict[str, str | bool | None] | None:
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
        Dictionary with 'content', 'saved_to', and 'truncated' keys if successful,
        None otherwise.
        Large content (>100KB) is automatically truncated for LLM response.

    Examples:
        >>> result = get_full_text_from_doi("10.1038/nature12373", "user@example.com")
        >>> result['content']  # The full text (truncated if large)
        >>> result['saved_to']  # Path where file was saved
        >>> result['truncated']  # True if content was truncated
        >>> get_full_text_from_doi(
        ...     "10.1038/nature12373", "user@example.com", save_file=True
        ... )
        # Full content saved to file, truncated version returned to LLM
    """
    try:
        em = get_email_manager()
        validated_email = em.validate_for_api("unpaywall", email)
        dfr = DOIFetcher(email=validated_email)
        full_text = dfr.get_full_text(doi)

        saved_path = None
        # Save to file if requested
        if full_text and (save_file or save_to):
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
                use_temp_dir=False,
            )
            if saved_path:
                logger.info(f"Full text saved to: {saved_path}")

        # Apply content size limits for return to LLM
        if full_text:
            limited_content, was_truncated = _apply_content_limits(
                full_text, str(saved_path) if saved_path else None
            )
        else:
            limited_content, was_truncated = "", False

        return {
            "content": limited_content,
            "saved_to": str(saved_path) if saved_path else None,
            "truncated": was_truncated,
        }
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
        Dictionary containing full text availability info with save path if successful,
        None otherwise.
        When file saving is requested, includes 'saved_to' key with the file path.

    Examples:
        >>> result = get_full_text_info("10.1038/nature12373", "user@email.com")
        >>> result['success']  # Full text availability status
        >>> result = get_full_text_info(
        ...     "10.1038/nature12373", "user@email.com", save_file=True
        ... )
        >>> result['saved_to']  # Path where file was saved
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

        saved_path = None
        # Save to file if requested
        if full_text_info and (save_file or save_to):
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
                use_temp_dir=False,
            )
            if saved_path:
                logger.info(f"Full text info saved to: {saved_path}")

        # Return full text info with save path info if file was saved
        if saved_path:
            full_text_info["saved_to"] = str(saved_path)

        return full_text_info
    except Exception as e:
        print(f"Error retrieving full text info for DOI {doi}: {e}")
        return None


def get_text_from_pdf_url(
    pdf_url: str, email: str, save_file: bool = False, save_to: str | None = None
) -> dict[str, str | bool | None] | None:
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
        Dictionary with 'content', 'saved_to', and 'truncated' keys if successful,
        None otherwise.
        Large content (>100KB) is automatically truncated for LLM response.

    Examples:
        >>> result = get_text_from_pdf_url(
        ...     "https://example.com/paper.pdf", "user@email.com"
        ... )
        >>> result['content']  # The extracted text (truncated if large)
        >>> result['saved_to']  # Path where file was saved
        >>> result['truncated']  # True if content was truncated
        >>> get_text_from_pdf_url(
        ...     "https://example.com/paper.pdf", "user@email.com", save_file=True
        ... )
        # Full content saved to file, truncated version returned to LLM
    """
    try:
        em = get_email_manager()
        validated_email = em.validate_for_api("unpaywall", email)
        dfr = DOIFetcher(email=validated_email)
        extracted_text = dfr.text_from_pdf_url(pdf_url)

        saved_path = None
        # Save to file if requested
        if extracted_text and (save_file or save_to):
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
                use_temp_dir=False,
            )
            if saved_path:
                logger.info(f"PDF URL text saved to: {saved_path}")

        # Apply content size limits for return to LLM
        if extracted_text:
            limited_content, was_truncated = _apply_content_limits(
                extracted_text, str(saved_path) if saved_path else None
            )
        else:
            limited_content, was_truncated = "", False

        return {
            "content": limited_content,
            "saved_to": str(saved_path) if saved_path else None,
            "truncated": was_truncated,
        }
    except Exception as e:
        print(f"Error extracting text from PDF URL {pdf_url}: {e}")
        return None


def extract_pdf_text(
    pdf_url: str,
    save_file: bool = False,
    save_to: str | None = None,
    stream_large_files: bool = True,
    max_content_size: int = 100 * 1024,  # 100KB default
) -> dict[str, str | int | bool | None] | None:
    """
    Extract text from a PDF URL using the standalone pdf_fetcher.

    Args:
        pdf_url: URL of the PDF to extract text from.
        save_file: Whether to save extracted text to temp directory with
            auto-generated filename
        save_to: Specific path to save extracted text (overrides save_file if provided)
        stream_large_files: If True, attempt to stream large PDFs directly to disk
        max_content_size: Maximum size (in characters) to return in 'content'.
                         Larger content is truncated with instructions.

    Returns:
        Dictionary with extraction results and file info, or None if failed.
        Contains 'content', 'saved_to', 'content_length', 'streamed', and
        'truncated' keys.
        Large content (>100KB) is automatically truncated to prevent token overflow.

    Examples:
        >>> result = extract_pdf_text("https://example.com/paper.pdf")
        >>> result['content']  # The extracted text (truncated if >100KB)
        >>> result['content_length']  # Original character count
        >>> result['truncated']  # True if content was truncated
        >>> extract_pdf_text("https://example.com/paper.pdf", save_file=True)
        # Full content saved to file, truncated version returned to LLM
    """
    try:
        result = extract_text_from_pdf(pdf_url)
        # Check if result is an error message
        if result and "Error extracting PDF text:" in str(result):
            print(f"Error extracting text from PDF URL {pdf_url}: {result}")
            return None

        if not result:
            return None

        content_length = len(result)
        saved_path = None
        was_streamed = False
        was_truncated = False

        # Always save full content to file if requested (before truncation)
        if save_file or save_to:
            url_identifier = (
                pdf_url.split("/")[-1].replace(".pdf", "")
                if "/" in pdf_url
                else "pdf_extract"
            )

            saved_path = file_manager.handle_file_save(
                content=result,  # Save full content
                base_name="pdf_text",
                identifier=url_identifier,
                file_format="txt",
                save_file=save_file,
                save_to=save_to,
                use_temp_dir=False,
            )
            if saved_path:
                logger.info(f"PDF text saved to: {saved_path}")

        # Apply content size limits for return to LLM
        return_content = result
        if content_length > max_content_size:
            was_truncated = True
            truncate_point = max_content_size - 200  # Leave room for truncation message

            save_msg = (
                f"{saved_path}"
                if saved_path
                else "file not saved - use save_file=True or save_to=path"
            )
            truncation_msg = (
                f"\n\n[CONTENT TRUNCATED - Showing first {truncate_point:,} "
                f"of {content_length:,} characters. Full content saved to: {save_msg}]"
            )
            return_content = result[:truncate_point] + truncation_msg

            logger.info(
                f"Large PDF content ({content_length:,} chars) "
                f"truncated for LLM response"
            )
        elif content_length > 50 * 1024:  # 50KB warning threshold
            logger.warning(
                f"Large content ({content_length:,} characters) "
                f"may approach token limits"
            )

        return {
            "content": return_content,
            "saved_to": str(saved_path) if saved_path else None,
            "content_length": content_length,
            "streamed": was_streamed,
            "truncated": was_truncated,
        }
    except Exception as e:
        print(f"Error extracting text from PDF URL {pdf_url}: {e}")
        return None


def clean_text(
    text: str | None, email: str, save_file: bool = False, save_to: str | None = None
) -> dict[str, str | bool | None] | None:
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
        Dictionary with 'content', 'saved_to', and 'truncated' keys.
        Large content (>100KB) is automatically truncated for LLM response.

    Examples:
        >>> result = clean_text("messy text", "user@email.com")
        >>> result['content']  # The cleaned text (truncated if large)
        >>> result['saved_to']  # Path where file was saved
        >>> result['truncated']  # True if content was truncated
        >>> clean_text("messy text", "user@email.com", save_file=True)
        # Full content saved to file, truncated version returned to LLM
        >>> clean_text("messy text", "user@email.com", save_to="cleaned.txt")
        # Saves to specified path
    """
    # Handle None input
    if text is None:
        return None

    try:
        em = get_email_manager()
        validated_email = em.validate_for_api("crossref", email)
        dfr = DOIFetcher(email=validated_email)
        cleaned_text = dfr.clean_text(text)

        saved_path = None
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
                use_temp_dir=False,
            )
            if saved_path:
                logger.info(f"Cleaned text saved to: {saved_path}")

        # Apply content size limits for return to LLM
        if cleaned_text:
            limited_content, was_truncated = _apply_content_limits(
                cleaned_text, str(saved_path) if saved_path else None
            )
        else:
            limited_content, was_truncated = "", False

        return {
            "content": limited_content,
            "saved_to": str(saved_path) if saved_path else None,
            "truncated": was_truncated,
        }
    except Exception as e:
        print(f"Error cleaning text: {e}")
        # Return original text in structured format on error
        limited_content, was_truncated = _apply_content_limits(text, None)
        return {
            "content": limited_content,
            "saved_to": None,
            "truncated": was_truncated,
        }


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
) -> dict[str, str | bool | None] | None:
    """
    Get full text from a DOI.

    Args:
        doi: The Digital Object Identifier.
        save_file: Whether to save full text to temp directory with
            auto-generated filename
        save_to: Specific path to save full text (overrides save_file if provided)

    Returns:
        Dictionary with 'content' and 'saved_to' keys if successful, None otherwise.
        - content: The full text content
        - saved_to: Path where file was saved (None if not saved)

    Examples:
        >>> result = get_doi_text("10.1038/nature12373")
        >>> result['content']  # The full text
        >>> result = get_doi_text("10.1038/nature12373", save_file=True)
        >>> result['saved_to']  # Path where file was saved
        >>> get_doi_text("10.1038/nature12373", save_to="paper_text.txt")
        # Saves to specified path and returns save location
    """
    try:
        full_text = aupu.get_doi_text(doi)
        if not full_text:
            return None

        saved_path = None
        # Save to file if requested
        if save_file or save_to:
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
                use_temp_dir=False,
            )
            if saved_path:
                logger.info(f"Full text saved to: {saved_path}")

        # Apply content size limits for return to LLM
        limited_content, was_truncated = _apply_content_limits(
            full_text, str(saved_path) if saved_path else None
        )

        return {
            "content": limited_content,
            "saved_to": str(saved_path) if saved_path else None,
            "truncated": was_truncated,
        }
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
) -> dict[str, str | bool | None] | None:
    """
    Get full text from a PMC ID.

    Args:
        pmcid: The PMC ID (e.g., 'PMC1234567').
        save_file: Whether to save full text to temp directory with
            auto-generated filename
        save_to: Specific path to save full text (overrides save_file if provided)

    Returns:
        Dictionary with 'content' and 'saved_to' keys if successful, None otherwise.
        - content: The full text content
        - saved_to: Path where file was saved (None if not saved)

    Examples:
        >>> result = get_pmcid_text("PMC1234567")
        >>> result['content']  # The full text
        >>> result = get_pmcid_text("PMC1234567", save_file=True)
        >>> result['saved_to']  # Path where file was saved
    """
    try:
        full_text = aupu.get_pmcid_text(pmcid)
        if not full_text:
            return None

        saved_path = None
        # Save to file if requested
        if save_file or save_to:
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
                use_temp_dir=False,
            )
            if saved_path:
                logger.info(f"PMC text saved to: {saved_path}")

        # Apply content size limits for return to LLM
        limited_content, was_truncated = _apply_content_limits(
            full_text, str(saved_path) if saved_path else None
        )

        return {
            "content": limited_content,
            "saved_to": str(saved_path) if saved_path else None,
            "truncated": was_truncated,
        }
    except Exception as e:
        print(f"Error getting text for PMCID {pmcid}: {e}")
        return None


def get_pmid_text(
    pmid: str, save_file: bool = False, save_to: str | None = None
) -> dict[str, str | bool | None] | None:
    """
    Get full text from a PubMed ID.

    Args:
        pmid: The PubMed ID.
        save_file: Whether to save full text to temp directory with
            auto-generated filename
        save_to: Specific path to save full text (overrides save_file if provided)

    Returns:
        Dictionary with 'content' and 'saved_to' keys if successful, None otherwise.
        - content: The full text content
        - saved_to: Path where file was saved (None if not saved)

    Examples:
        >>> result = get_pmid_text("23851394")
        >>> result['content']  # The full text
        >>> result = get_pmid_text("23851394", save_file=True)
        >>> result['saved_to']  # Path where file was saved
    """
    try:
        full_text = aupu.get_pmid_text(pmid)
        if not full_text:
            return None

        saved_path = None
        # Save to file if requested
        if save_file or save_to:
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
                use_temp_dir=False,
            )
            if saved_path:
                logger.info(f"PMID text saved to: {saved_path}")

        # Apply content size limits for return to LLM
        limited_content, was_truncated = _apply_content_limits(
            full_text, str(saved_path) if saved_path else None
        )

        return {
            "content": limited_content,
            "saved_to": str(saved_path) if saved_path else None,
            "truncated": was_truncated,
        }
    except Exception as e:
        print(f"Error getting text for PMID {pmid}: {e}")
        return None


def get_full_text_from_bioc(
    pmid: str, save_file: bool = False, save_to: str | None = None
) -> dict[str, str | bool | None] | None:
    """
    Get full text from BioC format for a PubMed ID.

    Args:
        pmid: The PubMed ID.
        save_file: Whether to save BioC text to temp directory with
            auto-generated filename
        save_to: Specific path to save BioC text (overrides save_file if provided)

    Returns:
        Dictionary with 'content', 'saved_to', and 'truncated' keys if successful,
        None otherwise.
        Large content (>100KB) is automatically truncated for LLM response.

    Examples:
        >>> result = get_full_text_from_bioc("23851394")
        >>> result['content']  # The BioC text (truncated if large)
        >>> result['saved_to']  # Path where file was saved
        >>> result['truncated']  # True if content was truncated
    """
    try:
        bioc_text = aupu.get_full_text_from_bioc(pmid)
        if not bioc_text:
            return None

        saved_path = None
        # Save to file if requested
        if save_file or save_to:
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
                use_temp_dir=False,
            )
            if saved_path:
                logger.info(f"BioC text saved to: {saved_path}")

        # Apply content size limits for return to LLM
        limited_content, was_truncated = _apply_content_limits(
            bioc_text, str(saved_path) if saved_path else None
        )

        return {
            "content": limited_content,
            "saved_to": str(saved_path) if saved_path else None,
            "truncated": was_truncated,
        }
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
        Dictionary containing PMIDs list, total count, and query info with save info if
        successful, None otherwise. When file saving is requested, includes 'saved_to'
        key with the file path.

    Examples:
        >>> results = search_pubmed_for_pmids("CRISPR")
        >>> results["pmids"]  # List of PMIDs
        >>> results = search_pubmed_for_pmids("CRISPR", save_file=True)
        >>> results["saved_to"]  # Path where file was saved
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
        saved_path = None
        if search_results and (save_file or save_to):
            try:
                saved_path = file_manager.handle_file_save(
                    content=search_results,
                    base_name="pubmed_search",
                    identifier=query.replace(" ", "_"),
                    file_format="json",
                    save_file=save_file,
                    save_to=save_to,
                    use_temp_dir=False,
                )
                if saved_path:
                    logger.info(f"PubMed search results saved to: {saved_path}")
            except Exception as e:
                logger.warning(f"Failed to save PubMed search results file: {e}")

        # Add save path info if file was saved
        if saved_path:
            search_results["saved_to"] = str(saved_path)

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
                use_temp_dir=False,
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
) -> dict[str, list | str | None] | None:
    """Get list of references cited by a paper.

    Args:
        doi: The DOI of the paper (supports all DOI formats)
        save_file: Whether to save references to temp directory with
            auto-generated filename
        save_to: Specific path to save references (overrides save_file if provided)

    Returns:
        Dictionary with 'data' and 'saved_to' keys if successful, None if fails.
        - data: List of reference dictionaries with DOI, title, journal, etc.
        - saved_to: Path where file was saved (None if not saved)

    Examples:
        >>> result = get_paper_references("10.1038/nature12373")
        >>> result['data']  # List of reference dictionaries
        >>> result['saved_to']  # Path where file was saved
        >>> len(result['data']) if result else 0
        25
    """
    try:
        references = CitationUtils.get_references_crossref(doi)

        # Save to file if requested
        saved_path = None
        if references and (save_file or save_to):
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
                use_temp_dir=False,
            )
            if saved_path:
                logger.info(f"Paper references saved to: {saved_path}")

        return (
            {"data": references, "saved_to": str(saved_path) if saved_path else None}
            if references
            else None
        )
    except Exception as e:
        logger.warning(f"Error getting references for DOI: {doi} - {e}")
        return None


def get_paper_citations(
    doi: str, save_file: bool = False, save_to: str | None = None
) -> dict[str, list | str | None] | None:
    """Get list of papers that cite a given paper.

    Args:
        doi: The DOI of the paper (supports all DOI formats)
        save_file: Whether to save citations to temp directory with
            auto-generated filename
        save_to: Specific path to save citations (overrides save_file if provided)

    Returns:
        Dictionary with 'data' and 'saved_to' keys if successful, None if fails.
        - data: List of citing paper dictionaries with DOI, title, authors, etc.
        - saved_to: Path where file was saved (None if not saved)

    Examples:
        >>> result = get_paper_citations("10.1038/nature12373")
        >>> result['data']  # List of citing paper dictionaries
        >>> result['saved_to']  # Path where file was saved
        >>> len(result['data']) if result else 0
        150
    """
    try:
        citations = CitationUtils.get_citations_crossref(doi)

        # Save to file if requested
        saved_path = None
        if citations and (save_file or save_to):
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
                use_temp_dir=False,
            )
            if saved_path:
                logger.info(f"Paper citations saved to: {saved_path}")

        return (
            {"data": citations, "saved_to": str(saved_path) if saved_path else None}
            if citations
            else None
        )
    except Exception as e:
        logger.warning(f"Error getting citations for DOI: {doi} - {e}")
        return None


def get_citation_network(
    doi: str, save_file: bool = False, save_to: str | None = None
) -> dict[str, Any] | None:
    """Get comprehensive citation network information from OpenAlex.

    Args:
        doi: The DOI of the paper (supports all DOI formats)
        save_file: Whether to save citation network to temp directory with
            auto-generated filename
        save_to: Specific path to save citation network (overrides save_file if
            provided)

    Returns:
        Dictionary with citation network data and save info, or None if fails.
        Contains 'data' key with citation info and 'saved_to' key with file path.

    Examples:
        >>> result = get_citation_network("10.1038/nature12373")
        >>> result['data']['cited_by_count']  # Access citation data
        245
        >>> result = get_citation_network("10.1038/nature12373", save_file=True)
        >>> result['saved_to']  # Path where file was saved
        '/Users/.../Documents/artl-mcp/citation_network_....json'
    """
    try:
        citation_network = CitationUtils.get_citation_network_openalex(doi)
        if not citation_network:
            return None

        saved_path = None
        # Save to file if requested
        if save_file or save_to:
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
                use_temp_dir=False,
            )
            if saved_path:
                logger.info(f"Citation network saved to: {saved_path}")

        return {
            "data": citation_network,
            "saved_to": str(saved_path) if saved_path else None,
        }
    except Exception as e:
        logger.warning(f"Error getting citation network for DOI: {doi} - {e}")
        return None


def find_related_papers(
    doi: str, max_results: int = 10, save_file: bool = False, save_to: str | None = None
) -> dict[str, list | str | None] | None:
    """Find papers related to a given paper through citations and references.

    Args:
        doi: The DOI of the reference paper (supports all DOI formats)
        max_results: Maximum number of related papers to return (default: 10)
        save_file: Whether to save related papers to temp directory with
            auto-generated filename
        save_to: Specific path to save related papers (overrides save_file if provided)

    Returns:
        Dictionary with 'data' and 'saved_to' keys if successful, None if fails.
        - data: List of related paper dictionaries
        - saved_to: Path where file was saved (None if not saved)

    Examples:
        >>> result = find_related_papers("10.1038/nature12373", 5)
        >>> result['data']  # List of related paper dictionaries
        >>> result['saved_to']  # Path where file was saved
        >>> len(result['data']) if result else 0
        5
    """
    try:
        related_papers = CitationUtils.find_related_papers(doi, max_results)

        # Save to file if requested
        saved_path = None
        if related_papers and (save_file or save_to):
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
                use_temp_dir=False,
            )
            if saved_path:
                logger.info(f"Related papers saved to: {saved_path}")

        return (
            {
                "data": related_papers,
                "saved_to": str(saved_path) if saved_path else None,
            }
            if related_papers
            else None
        )
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
                use_temp_dir=False,
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
                use_temp_dir=False,
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
