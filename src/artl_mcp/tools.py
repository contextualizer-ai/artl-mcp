import io
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

import artl_mcp.utils.pubmed_utils as aupu
from artl_mcp.utils.citation_utils import CitationUtils
from artl_mcp.utils.config_manager import (
    get_email_manager,
    should_use_alternative_sources,
)
from artl_mcp.utils.conversion_utils import IdentifierConverter
from artl_mcp.utils.doi_fetcher import DOIFetcher
from artl_mcp.utils.file_manager import FileFormat, file_manager
from artl_mcp.utils.identifier_utils import IdentifierError, IdentifierUtils, IDType
from artl_mcp.utils.pdf_fetcher import extract_text_from_pdf

logger = logging.getLogger(__name__)


def _apply_content_windowing(
    content: str,
    saved_path: str | None = None,
    offset: int = 0,
    limit: int | None = None,
) -> tuple[str, bool]:
    """Apply optional content windowing for large texts.

    Args:
        content: Original content
        saved_path: Path where full content is saved (for messaging)
        offset: Starting character position (0-based)
        limit: Maximum number of characters to return (None = no limit)

    Returns:
        Tuple of (windowed_content, was_windowed)
    """
    content_length = len(content)

    # Handle offset
    if offset > 0:
        if offset >= content_length:
            return "", True
        content = content[offset:]
        was_windowed = True
        windowing_msg_parts = [f"Starting from character {offset:,}"]
    else:
        was_windowed = False
        windowing_msg_parts = []

    # Handle limit
    if limit is not None and limit > 0:
        if len(content) > limit:
            content = content[:limit]
            was_windowed = True
            end_pos = offset + limit
            windowing_msg_parts.append(
                f"showing {limit:,} characters (ends at {end_pos:,})"
            )

    # Add windowing message if content was windowed
    if was_windowed and windowing_msg_parts:
        file_msg = (
            f"Full content saved to: {saved_path}"
            if saved_path
            else "file not saved - use save_file=True or save_to=path"
        )
        windowing_msg = (
            f"\n\n[CONTENT WINDOWED - {', '.join(windowing_msg_parts)} "
            f"of {content_length:,} total characters. {file_msg}]"
        )
        content = content + windowing_msg
        logger.info(f"Large content ({content_length:,} chars) windowed for response")

    return content, was_windowed


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
            "windowed": False,
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

    # Apply content windowing for return to LLM if requested
    limited_content, was_truncated = _apply_content_windowing(
        abstract_from_pubmed, str(saved_path) if saved_path else None
    )

    return {
        "content": limited_content,
        "saved_to": str(saved_path) if saved_path else None,
        "windowed": was_truncated,
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

        # Apply content windowing for return to LLM if requested
        if full_text:
            limited_content, was_truncated = _apply_content_windowing(
                full_text, str(saved_path) if saved_path else None
            )
        else:
            limited_content, was_truncated = "", False

        return {
            "content": limited_content,
            "saved_to": str(saved_path) if saved_path else None,
            "windowed": was_truncated,
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
            limited_content, was_truncated = _apply_content_windowing(
                extracted_text, str(saved_path) if saved_path else None
            )
        else:
            limited_content, was_truncated = "", False

        return {
            "content": limited_content,
            "saved_to": str(saved_path) if saved_path else None,
            "windowed": was_truncated,
        }
    except Exception as e:
        print(f"Error extracting text from PDF URL {pdf_url}: {e}")
        return None


def extract_pdf_text(
    pdf_url: str,
    save_file: bool = False,
    save_to: str | None = None,
    stream_large_files: bool = True,
) -> dict[str, str | int | bool | None] | None:
    """
    Extract text from a PDF URL using the standalone pdf_fetcher.

    Args:
        pdf_url: URL of the PDF to extract text from.
        save_file: Whether to save extracted text to temp directory with
            auto-generated filename
        save_to: Specific path to save extracted text (overrides save_file if provided)
        stream_large_files: If True, attempt to stream large PDFs directly to disk

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

        # Apply content windowing for return to LLM if requested
        return_content, was_truncated = _apply_content_windowing(
            result, str(saved_path) if saved_path else None
        )

        return {
            "content": return_content,
            "saved_to": str(saved_path) if saved_path else None,
            "content_length": content_length,
            "streamed": was_streamed,
            "windowed": was_truncated,
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
            limited_content, was_truncated = _apply_content_windowing(
                cleaned_text, str(saved_path) if saved_path else None
            )
        else:
            limited_content, was_truncated = "", False

        return {
            "content": limited_content,
            "saved_to": str(saved_path) if saved_path else None,
            "windowed": was_truncated,
        }
    except Exception as e:
        print(f"Error cleaning text: {e}")
        # Return original text in structured format on error
        limited_content, was_truncated = _apply_content_windowing(text, None)
        return {
            "content": limited_content,
            "saved_to": None,
            "windowed": was_truncated,
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
        limited_content, was_truncated = _apply_content_windowing(
            full_text, str(saved_path) if saved_path else None
        )

        return {
            "content": limited_content,
            "saved_to": str(saved_path) if saved_path else None,
            "windowed": was_truncated,
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
        limited_content, was_truncated = _apply_content_windowing(
            full_text, str(saved_path) if saved_path else None
        )

        return {
            "content": limited_content,
            "saved_to": str(saved_path) if saved_path else None,
            "windowed": was_truncated,
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
        limited_content, was_truncated = _apply_content_windowing(
            full_text, str(saved_path) if saved_path else None
        )

        return {
            "content": limited_content,
            "saved_to": str(saved_path) if saved_path else None,
            "windowed": was_truncated,
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

        return {
            "content": bioc_text,
            "saved_to": str(saved_path) if saved_path else None,
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


def download_pdf_from_url(
    pdf_url: str,
    save_to: str | None = None,
    filename: str | None = None,
) -> dict[str, str | int | bool | None]:
    """Download a PDF file from URL and save it without any conversion.

    Downloads the raw PDF binary data and saves it as a .pdf file. No text
    extraction or content processing is performed. No content is returned to
    avoid streaming large data to the LLM agent.

    Args:
        pdf_url: Direct URL to the PDF file
        save_to: Specific path to save PDF (overrides filename if provided)
        filename: Custom filename for the PDF (will add .pdf extension if missing)

    Returns:
        Dictionary with download results and file info.
        Contains 'saved_to', 'file_size_bytes', 'success' keys.
        Deliberately excludes 'content' to avoid streaming PDF data to LLM.

    Examples:
        >>> result = download_pdf_from_url("https://example.com/paper.pdf")
        >>> result['saved_to']  # Path where PDF was saved
        '/Users/.../Documents/artl-mcp/paper.pdf'
        >>> result['file_size_bytes']  # Size of downloaded PDF
        1048576
    """
    # urlparse is already imported at the top of the file

    try:
        # Generate filename if not provided
        if not filename and not save_to:
            # Extract filename from URL
            parsed_url = urlparse(pdf_url)
            url_filename = parsed_url.path.split("/")[-1]
            if url_filename and url_filename.endswith(".pdf"):
                filename = url_filename
            else:
                # Generate generic filename
                filename = (
                    f"downloaded_pdf_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                )
        elif filename and not filename.endswith(".pdf"):
            filename = f"{filename}.pdf"

        # Use file_manager's stream download to save directly to disk
        if save_to:
            # Save to specific path
            save_path = Path(save_to)
            if not save_path.is_absolute():
                save_path = file_manager.output_dir / save_path

            # Ensure .pdf extension
            if not save_path.name.endswith(".pdf"):
                save_path = save_path.with_suffix(".pdf")

            final_path, file_size = file_manager.stream_download_to_file(
                url=pdf_url,
                filename=save_path.name,
                file_format="pdf",
                output_dir=save_path.parent,
            )
        else:
            # Use auto-generated filename in output directory
            final_path, file_size = file_manager.stream_download_to_file(
                url=pdf_url,
                filename=filename or "download.pdf",
                file_format="pdf",
                output_dir=file_manager.output_dir,
            )

        logger.info(f"PDF downloaded and saved to: {final_path}")

        return {
            "saved_to": str(final_path),
            "file_size_bytes": file_size,
            "success": True,
            "url": pdf_url,
        }

    except requests.exceptions.RequestException as e:
        logger.error(f"Error downloading PDF from {pdf_url}: {e}")
        return {
            "saved_to": None,
            "file_size_bytes": 0,
            "success": False,
            "url": pdf_url,
            "error": f"Download failed: {e}",
        }
    except Exception as e:
        logger.error(f"Unexpected error downloading PDF from {pdf_url}: {e}")
        return {
            "saved_to": None,
            "file_size_bytes": 0,
            "success": False,
            "url": pdf_url,
            "error": f"Unexpected error: {e}",
        }


def download_pdf_from_doi(
    doi: str,
    email: str,
    save_to: str | None = None,
    filename: str | None = None,
) -> dict[str, str | int | bool | None]:
    """Download PDF for a DOI using Unpaywall and save without conversion.

    Uses Unpaywall API to find open access PDF URLs, then downloads and saves
    the PDF file directly. No text extraction or content streaming to LLM.

    IMPORTANT: This tool requires an email address. If the user hasn't provided one,
    please ask them for their email address before calling this tool.

    Args:
        doi: The Digital Object Identifier of the article
        email: Email address for API requests (required - ask user if not provided)
        save_to: Specific path to save PDF (overrides filename if provided)
        filename: Custom filename for the PDF (will add .pdf extension if missing)

    Returns:
        Dictionary with download results and file info.
        Contains 'saved_to', 'file_size_bytes', 'success', 'pdf_url' keys.
        Deliberately excludes 'content' to avoid streaming PDF data to LLM.

    Examples:
        >>> result = download_pdf_from_doi(
        ...     "10.1371/journal.pone.0123456", "user@email.com"
        ... )
        >>> result['saved_to']  # Path where PDF was saved
        '/Users/.../Documents/artl-mcp/unpaywall_pdf_10_1371_journal_pone_0123456.pdf'
        >>> download_pdf_from_doi(
        ...     "10.1371/journal.pone.0123456",
        ...     "user@email.com",
        ...     filename="my_paper.pdf"
        ... )
    """
    try:
        # First get Unpaywall info to find PDF URL
        unpaywall_info = get_unpaywall_info(doi, email, strict=False)

        if not unpaywall_info:
            return {
                "saved_to": None,
                "file_size_bytes": 0,
                "success": False,
                "pdf_url": None,
                "error": "Could not retrieve Unpaywall information",
                "doi": doi,
            }

        # Look for open access PDF URL
        pdf_url = None

        # Check for best OA location
        if "best_oa_location" in unpaywall_info and unpaywall_info["best_oa_location"]:
            best_oa = unpaywall_info["best_oa_location"]
            if best_oa.get("url_for_pdf"):
                pdf_url = best_oa["url_for_pdf"]

        # Fallback: check all OA locations
        if not pdf_url and "oa_locations" in unpaywall_info:
            for location in unpaywall_info.get("oa_locations", []):
                if location.get("url_for_pdf"):
                    pdf_url = location["url_for_pdf"]
                    break

        if not pdf_url:
            return {
                "saved_to": None,
                "file_size_bytes": 0,
                "success": False,
                "pdf_url": None,
                "error": "No open access PDF found in Unpaywall data",
                "doi": doi,
            }

        # Generate filename if not provided
        if not filename and not save_to:
            try:
                if not isinstance(doi, str):
                    raise ValueError(
                        f"Expected DOI to be of type str, but got {type(doi).__name__}"
                    )
                clean_doi = IdentifierUtils.normalize_doi(doi, "raw")
                clean_doi = clean_doi.replace("/", "_").replace(":", "_")
            except IdentifierError:
                clean_doi = doi.replace("/", "_").replace(":", "_")
            filename = f"unpaywall_pdf_{clean_doi}.pdf"

        # Download the PDF
        result = download_pdf_from_url(pdf_url, save_to, filename)
        result["pdf_url"] = pdf_url
        result["doi"] = doi

        return result

    except Exception as e:
        logger.error(f"Error downloading PDF from DOI {doi}: {e}")
        return {
            "saved_to": None,
            "file_size_bytes": 0,
            "success": False,
            "pdf_url": None,
            "doi": doi,
            "error": f"Unexpected error: {e}",
        }


# Europe PMC search functions
def _search_europepmc_flexible(
    query: str,
    page_size: int = 25,
    synonym: bool = True,
    sort: str = "RELEVANCE",
    result_type: str = "core",
    source_filters: list[str] | None = None,
    auto_paginate: bool = False,
    max_results: int = 100,
    cursor_mark: str = "*",
) -> dict[str, Any] | None:
    """
    Flexible Europe PMC search with comprehensive parameter support.

    This is an internal function that provides full access to Europe PMC API parameters.
    For simple keyword searches, use search_keywords_for_ids() instead.

    Args:
        query: Search query/keywords
        page_size: Results per page (max 1000)
        synonym: Include synonyms in search (recommended: True)
        sort: Sort order - RELEVANCE, DATE, CITED
        result_type: core (full metadata), lite (minimal), idlist (IDs only)
        source_filters: List of sources to include (e.g., ["med", "pmc"])
        auto_paginate: Automatically retrieve all results up to max_results
        max_results: Maximum total results when auto_paginate=True
        cursor_mark: Pagination cursor (use "*" for first page)

    Returns:
        Dictionary containing search results from Europe PMC API
        None if search fails

    Note:
        This function determines whether to use Europe PMC or PubMed based on the
        should_use_alternative_sources() function, which considers multiple factors
        including USE_ALTERNATIVE_SOURCES and PUBMED_OFFLINE environment variables,
        as well as automatic NCBI service availability detection. If alternative
        sources are preferred, Europe PMC is used; otherwise, PubMed may be used.
    """
    try:
        # Check if we should use alternative sources
        if not should_use_alternative_sources():
            logger.info(
                "NCBI services available, consider using search_pubmed_for_pmids "
                "instead"
            )

        # Build URL and parameters
        base_url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"

        params: dict[str, str] = {
            "query": query,
            "format": "json",
            "pageSize": str(min(page_size, 1000)),  # API max is 1000
            "synonym": "true" if synonym else "false",
            "resultType": result_type,
            "cursorMark": cursor_mark,
        }

        # Add sort if specified
        if sort and sort != "RELEVANCE":
            params["sort"] = sort

        # Add source filters
        if source_filters:
            source_query = " OR ".join([f"src:{src}" for src in source_filters])
            params["query"] = f"({query}) AND ({source_query})"

        # Set headers
        headers = {
            "Accept": "application/json",
            "User-Agent": "ARTL-MCP/1.0 (https://github.com/contextualizer-ai/artl-mcp)",
        }

        # Make request
        response = requests.get(base_url, params=params, headers=headers, timeout=30)
        response.raise_for_status()

        data = response.json()

        # Handle auto-pagination
        if auto_paginate and result_type == "core":
            all_results = data.get("resultList", {}).get("result", [])
            next_cursor = data.get("nextCursorMark")

            while (
                next_cursor
                and len(all_results) < max_results
                and len(all_results) < data.get("hitCount", 0)
            ):
                # Get next page
                params["cursorMark"] = next_cursor
                params["pageSize"] = str(
                    min(page_size, max_results - len(all_results), 1000)
                )

                response = requests.get(
                    base_url, params=params, headers=headers, timeout=30
                )
                response.raise_for_status()

                page_data = response.json()
                page_results = page_data.get("resultList", {}).get("result", [])

                if not page_results:
                    break

                all_results.extend(page_results)
                next_cursor = page_data.get("nextCursorMark")

                # Prevent infinite loops
                if next_cursor == params["cursorMark"]:
                    break

            # Update data with all results
            if "resultList" in data:
                data["resultList"]["result"] = all_results[:max_results]
                data["returnedCount"] = len(data["resultList"]["result"])

        logger.info(
            f"Europe PMC search returned {data.get('hitCount', 0)} total matches, "
            f"{len(data.get('resultList', {}).get('result', []))} results retrieved"
        )

        return data

    except requests.exceptions.RequestException as e:
        logger.error(f"Error searching Europe PMC for query '{query}': {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error searching Europe PMC for query '{query}': {e}")
        return None


def search_europepmc_papers(
    keywords: str,
    max_results: int = 10,
    result_type: str = "lite",
    save_file: bool = False,
    save_to: str | None = None,
) -> dict[str, Any]:
    """
    Search Europe PMC for papers and return comprehensive paper information.

    This tool searches Europe PMC database using keywords and returns comprehensive
    information including complete metadata, abstracts, and access information.
    It ONLY uses Europe PMC - no PubMed or NCBI APIs are accessed.

    What it does:
    1. Searches Europe PMC database with your keywords
    2. Returns complete paper metadata (not just IDs)
    3. Provides direct links to papers, PDFs, and full text
    4. Includes abstracts, keywords, author affiliations (in core mode)
    5. Indicates full text and PDF availability

    Args:
        keywords: Search query using Europe PMC syntax. Supports:
            Basic searches:
            - Simple terms: "CRISPR", "machine learning", "cancer immunotherapy"
            - Phrases: "rhizosphere microbiome", "gene editing"

            Advanced syntax:
            - Boolean operators: "CRISPR AND gene editing", "microbiome OR microbiota"
            - Field searches: title:"CRISPR", author:"Smith", journal:"Nature"
            - Wildcards: "bacteri*" (matches bacteria, bacterial, etc.)
            - Negation: "CRISPR NOT review"
            - Parentheses: "(CRISPR OR gene editing) AND therapy"

            Specialized filters:
            - Source: src:med (PubMed), src:pmc (PMC), src:ppr (preprints)
            - Publication type: PUB_TYPE:"Review", PUB_TYPE:"Clinical Trial"
            - Date ranges: first_pdate:[2020-01-01 TO 2024-12-31]
            - Open access: OPEN_ACCESS:Y
            - Language: LANG:eng

            Examples:
            - "title:microbiome AND src:pmc" - PMC papers with microbiome in title
            - "author:smith AND first_pdate:[2020 TO 2024]" - Smith papers 2020-2024
            - "CRISPR AND PUB_TYPE:Review AND OPEN_ACCESS:Y" - Open access reviews

        max_results: Number of papers to return (default: 10, max: 100)
        result_type: Level of detail to return - "lite" or "core"
            - "lite": Basic metadata, titles, authors, access flags (faster, smaller)
            - "core": Full metadata including abstracts, keywords, affiliations,
                     MeSH terms, grants, full text URLs (richer, larger)

    Result Type Comparison:
        "lite" mode returns:
        - Basic identifiers (PMID, PMCID, DOI)
        - Title, author string, journal, publication year
        - Access flags (isOpenAccess, hasPDF, inPMC)
        - Publication type and basic metadata
        - ~8KB for 10 papers

        "core" mode additionally includes:
        - Complete abstract text
        - Individual author details with affiliations
        - Keywords and MeSH terms
        - Grant/funding information
        - Multiple full text URLs with access types
        - Journal details and publication status
        - ~64KB for 10 papers (8x larger)

        Neither mode includes citation lists - those require separate API calls.

    Returns:
        Dictionary with complete paper information:
        {
            "papers": [                                   # Complete paper objects
                {
                    "id": "40603217",                     # Europe PMC ID
                    "source": "MED",                      # Source database
                    "pmid": "40603217",                   # PubMed ID
                    "pmcid": "PMC12241448",              # PMC ID (if available)
                    "doi": "10.1016/j.tplants.2025.06.001", # DOI
                    "title": "The chemical interaction...", # Full title
                    "authorString": "Bouwmeester H, ...",    # Author string
                    "journalTitle": "Trends Plant Sci",      # Journal name
                    "pubYear": "2025",                       # Publication year
                    "isOpenAccess": "Y",                     # Open access flag
                    "inEPMC": "Y",                          # In Europe PMC
                    "inPMC": "Y",                           # In PMC
                    "hasPDF": "Y",                          # PDF available
                    "hasSuppl": "Y",                        # Supplementary materials
                    "pubType": "review; journal article",   # Publication type

                    # Additional fields in "core" mode:
                    "abstractText": "Research into...",     # Full abstract
                    "authorList": {...},                    # Detailed author info
                    "keywordList": {...},                   # Keywords
                    "meshHeadingList": {...},              # MeSH terms
                    "grantsList": {...},                   # Funding info
                    "fullTextUrlList": {...},             # Full text URLs
                }
            ],
            "pmids": ["40603217", "40635331"],           # Extracted PubMed IDs
            "pmcids": ["PMC12241448"],                   # Extracted PMC IDs
            "dois": ["10.1016/j.tplants.2025.06.001"],   # Extracted DOIs
            "total_count": 9832,                         # Total matches in Europe PMC
            "returned_count": 10,                        # Papers in this response
            "result_type": "lite",                       # Mode used for this search
            "source": "europepmc",                       # Always Europe PMC
            "query": "rhizosphere microbiome"            # Your search terms
        }

    Examples:
        # Basic search with lite mode (default)
        >>> result = search_europepmc_papers("rhizosphere microbiome")
        >>> len(result["papers"])  # Number of papers returned
        10
        >>> result["papers"][0]["title"]  # Paper title
        'The chemical interaction between plants and the rhizosphere microbiome.'
        >>> result["papers"][0]["isOpenAccess"]  # Check access
        'Y'

        # Rich search with core mode for detailed analysis
        >>> result = search_europepmc_papers(
        ...     "CRISPR", max_results=5, result_type="core"
        ... )
        >>> result["papers"][0]["abstractText"]  # Full abstract text
        'CRISPR-Cas9 technology has revolutionized...'
        >>> result["papers"][0]["keywordList"]["keyword"]  # Keywords
        ['CRISPR', 'Gene editing', 'Cas9']

        # Advanced query examples
        >>> result = search_europepmc_papers('title:"machine learning" AND src:pmc')
        >>> result = search_europepmc_papers(
        ...     'author:"Smith" AND first_pdate:[2020 TO 2024]'
        ... )
        >>> result = search_europepmc_papers(
        ...     'CRISPR AND PUB_TYPE:"Review" AND OPEN_ACCESS:Y'
        ... )

        # Filter by access type
        >>> open_access = [p for p in result["papers"] if p["isOpenAccess"] == "Y"]
        >>> with_pdfs = [p for p in result["papers"] if p["hasPDF"] == "Y"]

    Perfect for:
    - Literature discovery and analysis
    - Finding papers with specific access requirements (open access, PDFs)
    - Getting abstracts and keywords for content analysis
    - Building citation databases and literature reviews
    - Accessing papers through multiple URL types
    - Research planning with author and affiliation information
    """
    try:
        # Use Europe PMC exclusively - no PubMed fallback
        europepmc_result = _search_europepmc_flexible(
            query=keywords,
            page_size=max_results,
            synonym=True,
            sort="RELEVANCE",
            result_type=result_type,
            auto_paginate=False,
            max_results=max_results,
        )

        if not europepmc_result:
            return {
                "pmids": [],
                "pmcids": [],
                "dois": [],
                "papers": [],
                "total_count": 0,
                "returned_count": 0,
                "result_type": result_type,
                "source": "europepmc",
                "query": keywords,
                "error": "Search failed",
            }

        # Extract comprehensive information from Europe PMC results
        results = europepmc_result.get("resultList", {}).get("result", [])

        pmids = []
        pmcids = []
        dois = []
        papers = []

        for paper in results:
            # Extract basic identifiers
            pmid = paper.get("pmid")
            pmcid = paper.get("pmcid")
            doi = paper.get("doi")

            # Start with the complete paper object from Europe PMC
            paper_info = dict(paper)  # Copy all fields from Europe PMC response

            # Collect identifiers for summary lists
            if pmid:
                pmids.append(pmid)
            if pmcid:
                pmcids.append(pmcid)
            if doi:
                dois.append(doi)

            papers.append(paper_info)

        search_results = {
            "pmids": pmids,
            "pmcids": pmcids,
            "dois": dois,
            "papers": papers,
            "total_count": europepmc_result.get("hitCount", 0),
            "returned_count": len(results),
            "result_type": result_type,
            "source": "europepmc",
            "query": keywords,
        }

        # Save to file if requested
        saved_path = None
        if save_file or save_to:
            try:
                saved_path = file_manager.handle_file_save(
                    content=search_results,
                    base_name="europepmc_search",
                    identifier=keywords.replace(" ", "_").replace(":", "_"),
                    file_format="json",
                    save_file=save_file,
                    save_to=save_to,
                    use_temp_dir=False,
                )
                if saved_path:
                    logger.info(f"Europe PMC search results saved to: {saved_path}")
            except Exception as e:
                logger.warning(f"Failed to save Europe PMC search results: {e}")

        # Add save path info if file was saved
        if saved_path:
            search_results["saved_to"] = str(saved_path)

        return search_results

    except Exception as e:
        logger.error(f"Error in search_europepmc_papers for query '{keywords}': {e}")
        return {
            "pmids": [],
            "pmcids": [],
            "dois": [],
            "papers": [],
            "total_count": 0,
            "returned_count": 0,
            "result_type": result_type,
            "source": "error",
            "query": keywords,
            "error": str(e),
        }


def get_europepmc_paper_by_id(
    identifier: str, save_file: bool = False, save_to: str | None = None
) -> dict[str, Any] | None:
    """Get full Europe PMC metadata for any scientific identifier.

    Automatically detects identifier type (DOI, PMID, PMCID) and retrieves complete
    paper metadata from Europe PMC using core mode for maximum detail.

    Args:
        identifier: Any scientific identifier - DOI, PMID, or PMCID in any format:
            - DOI: "10.1038/nature12373", "doi:10.1038/nature12373"
            - PMID: "23851394", "PMID:23851394", "pmid:23851394"
            - PMCID: "PMC3737249", "3737249", "PMC:3737249"
        save_file: Whether to save metadata to temp directory with
            auto-generated filename
        save_to: Specific path to save metadata (overrides save_file if provided)

    Returns:
        Dictionary with complete Europe PMC paper metadata including:
        - All identifiers (PMID, PMCID, DOI, Europe PMC ID)
        - Complete metadata (title, authors, journal, abstract, keywords)
        - Full text availability and access information
        - Publication details and citation data
        - File save information if requested

        Returns None if no paper found or identifier invalid.

    Examples:
        # Using DOI
        >>> paper = get_europepmc_paper_by_id("10.1038/nature12373")
        >>> paper["title"]
        'CRISPR-Cas systems: RNA-mediated adaptive immunity in bacteria and archaea'
        >>> paper["abstractText"][:50]
        'Clustered regularly interspaced short palindromic...'

        # Using PMID
        >>> paper = get_europepmc_paper_by_id("23851394")
        >>> paper["authorList"]["author"][0]["fullName"]
        'Sorek R'

        # Save to file
        >>> result = get_europepmc_paper_by_id("PMC3737249", save_file=True)
        >>> result["saved_to"]
        '/Users/.../Documents/artl-mcp/europepmc_paper_PMC3737249.json'

    Perfect for:
    - Getting complete paper information from any identifier type
    - Research analysis requiring full metadata and abstracts
    - Converting between identifier types while getting full data
    - Building comprehensive literature databases
    """
    try:
        # Use IdentifierUtils to detect and normalize the identifier
        id_info = IdentifierUtils.normalize_identifier(identifier)
        id_type = id_info["type"]
        normalized_id = id_info["value"]

        logger.info(f"Detected identifier type: {id_type} for input: {identifier}")

        # Construct appropriate Europe PMC query based on identifier type
        if id_type == "doi":
            # DOI queries in Europe PMC
            query = f'doi:"{normalized_id}"'
        elif id_type == "pmid":
            # PMID queries need special handling - search as external ID in MED source
            query = f"ext_id:{normalized_id} AND src:med"
        elif id_type == "pmcid":
            # PMCID queries can use the PMC ID directly
            pmc_number = (
                normalized_id.replace("PMC", "")
                if normalized_id.startswith("PMC")
                else normalized_id
            )
            query = f"pmcid:PMC{pmc_number}"
        else:
            logger.warning(f"Unsupported identifier type: {id_type}")
            return None

        logger.info(f"Using Europe PMC query: {query}")

        # Search Europe PMC using core mode for full metadata
        result = _search_europepmc_flexible(
            query=query,
            page_size=1,  # We only want one result
            synonym=False,  # Don't expand for exact ID matches
            sort="RELEVANCE",
            result_type="core",  # Use core for full metadata including abstracts
            auto_paginate=False,
            max_results=1,
        )

        if not result or not result.get("resultList", {}).get("result"):
            logger.warning(f"No paper found in Europe PMC for identifier: {identifier}")
            return None

        papers = result["resultList"]["result"]
        if not papers:
            return None

        # Get the first (and should be only) paper
        paper_data = papers[0]

        # Save to file if requested
        saved_path = None
        if save_file or save_to:
            try:
                # Create clean identifier for filename
                clean_id = str(identifier).replace("/", "_").replace(":", "_")
                saved_path = file_manager.handle_file_save(
                    content=paper_data,
                    base_name="europepmc_paper",
                    identifier=clean_id,
                    file_format="json",
                    save_file=save_file,
                    save_to=save_to,
                    use_temp_dir=False,
                )
                if saved_path:
                    logger.info(f"Europe PMC paper metadata saved to: {saved_path}")
            except Exception as e:
                logger.warning(f"Failed to save paper metadata: {e}")

        # Add metadata about the search
        paper_data["_search_info"] = {
            "input_identifier": identifier,
            "detected_type": id_type,
            "normalized_identifier": normalized_id,
            "query_used": query,
            "source": "europepmc",
            "result_type": "core",
        }

        # Add save info if file was saved
        if saved_path:
            paper_data["saved_to"] = str(saved_path)

        return paper_data

    except Exception as e:
        logger.error(
            f"Error getting Europe PMC paper for identifier '{identifier}': {e}"
        )
        return None


def get_all_identifiers_from_europepmc(
    identifier: str, save_file: bool = False, save_to: str | None = None
) -> dict[str, Any] | None:
    """Get all available identifiers and links for a paper from Europe PMC.

    **BEST FOR**: Identifier translation, cross-referencing, finding all access points
    **INPUT**: ONE specific identifier (DOI, PMID, or PMCID)
    **OUTPUT**: All available IDs + direct URLs + access status for that ONE paper

    This is the OPTIMAL tool when you have ONE paper identifier and need:
    - All other identifiers for the same paper (PMID ↔ DOI ↔ PMCID translation)
    - Direct access URLs (PubMed, PMC, DOI, Europe PMC links)
    - Access status (open access, PDF availability, etc.)

    Use this instead of search when you have a specific paper identifier.

    Args:
        identifier: Any scientific identifier - DOI, PMID, or PMCID in any format:
            - DOI: "10.1038/nature12373", "doi:10.1038/nature12373"
            - PMID: "23851394", "PMID:23851394", "pmid:23851394"
            - PMCID: "PMC3737249", "3737249", "PMC:3737249"
        save_file: Whether to save identifiers to temp directory with
            auto-generated filename
        save_to: Specific path to save identifiers (overrides save_file if provided)

    Returns:
        Dictionary with all available identifiers and access information:
        {
            "identifiers": {
                "pmid": "23851394",           # PubMed ID
                "pmcid": "PMC3737249",        # PMC ID
                "doi": "10.1038/nature12373", # DOI
                "europepmc_id": "23851394",   # Europe PMC internal ID
                "source": "MED"               # Source database
            },
            "urls": {
                "pubmed": "https://pubmed.ncbi.nlm.nih.gov/23851394",
                "pmc": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3737249/",
                "doi": "https://doi.org/10.1038/nature12373",
                "europepmc": "https://europepmc.org/article/MED/23851394",
                "full_text_urls": [...]       # Additional full text URLs if available
            },
            "access": {
                "is_open_access": True,
                "has_pdf": True,
                "in_pmc": True,
                "in_europepmc": True,
                "has_full_text": True,
                "has_supplementary": False
            },
            "basic_info": {
                "title": "Paper title...",
                "journal": "Nature",
                "year": "2013",
                "authors": "Author list..."
            }
        }

        Returns None if no paper found or identifier invalid.

    Examples:
        # Get all IDs and links for a DOI
        >>> result = get_all_identifiers_from_europepmc("10.1038/nature12373")
        >>> result["identifiers"]["pmid"]
        '23851394'
        >>> result["urls"]["pmc"]
        'https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3737249/'
        >>> result["access"]["is_open_access"]
        True

        # Get identifiers from PMID
        >>> result = get_all_identifiers_from_europepmc("23851394")
        >>> result["identifiers"]["doi"]
        '10.1038/nature12373'

        # Save results to file
        >>> result = get_all_identifiers_from_europepmc("PMC3737249", save_file=True)
        >>> result["saved_to"]
        '/Users/.../Documents/artl-mcp/europepmc_identifiers_PMC3737249.json'

    Perfect for:
    - ID translation and cross-referencing
    - Finding all access points for a paper
    - Checking open access availability
    - Building comprehensive paper databases with all identifiers
    - Creating direct links to papers in multiple databases
    """
    try:
        # Use IdentifierUtils to detect and normalize the identifier
        id_info = IdentifierUtils.normalize_identifier(identifier)
        id_type = id_info["type"]
        normalized_id = id_info["value"]

        logger.info(f"Detected identifier type: {id_type} for input: {identifier}")

        # Construct appropriate Europe PMC query based on identifier type
        if id_type == "doi":
            query = f'doi:"{normalized_id}"'
        elif id_type == "pmid":
            query = f"ext_id:{normalized_id} AND src:med"
        elif id_type == "pmcid":
            pmc_number = (
                normalized_id.replace("PMC", "")
                if normalized_id.startswith("PMC")
                else normalized_id
            )
            query = f"pmcid:PMC{pmc_number}"
        else:
            logger.warning(f"Unsupported identifier type: {id_type}")
            return None

        logger.info(f"Using Europe PMC query: {query}")

        # Search Europe PMC using lite mode (sufficient for identifier extraction)
        result = _search_europepmc_flexible(
            query=query,
            page_size=1,
            synonym=False,
            sort="RELEVANCE",
            result_type="lite",  # Lite mode has all the identifiers we need
            auto_paginate=False,
            max_results=1,
        )

        if not result or not result.get("resultList", {}).get("result"):
            logger.warning(f"No paper found in Europe PMC for identifier: {identifier}")
            return None

        papers = result["resultList"]["result"]
        if not papers:
            return None

        paper = papers[0]

        # Extract all available identifiers
        identifiers = {
            "pmid": paper.get("pmid"),
            "pmcid": paper.get("pmcid"),
            "doi": paper.get("doi"),
            "europepmc_id": paper.get("id"),
            "source": paper.get("source"),
        }

        # Remove None values
        identifiers = {k: v for k, v in identifiers.items() if v is not None}

        # Build URLs for all available identifiers
        urls: dict[str, str | list[dict[str, Any]]] = {}

        if identifiers.get("pmid"):
            urls["pubmed"] = f"https://pubmed.ncbi.nlm.nih.gov/{identifiers['pmid']}"

        if identifiers.get("pmcid"):
            urls["pmc"] = (
                f"https://www.ncbi.nlm.nih.gov/pmc/articles/{identifiers['pmcid']}/"
            )

        if identifiers.get("doi"):
            urls["doi"] = f"https://doi.org/{identifiers['doi']}"

        if identifiers.get("europepmc_id") and identifiers.get("source"):
            urls["europepmc"] = (
                f"https://europepmc.org/article/{identifiers['source']}/{identifiers['europepmc_id']}"
            )

        # Extract full text URLs if available in core mode data
        full_text_urls = []
        if "fullTextUrlList" in paper and paper["fullTextUrlList"]:
            for url_entry in paper["fullTextUrlList"].get("fullTextUrl", []):
                full_text_urls.append(
                    {
                        "url": url_entry.get("url"),
                        "availability": url_entry.get("availability"),
                        "document_style": url_entry.get("documentStyle"),
                        "site": url_entry.get("site"),
                    }
                )

        if full_text_urls:
            urls["full_text_urls"] = full_text_urls

        # Extract access information
        access = {
            "is_open_access": paper.get("isOpenAccess") == "Y",
            "has_pdf": paper.get("hasPDF") == "Y",
            "in_pmc": paper.get("inPMC") == "Y",
            "in_europepmc": paper.get("inEPMC") == "Y",
            "has_full_text": bool(full_text_urls) or paper.get("inEPMC") == "Y",
            "has_supplementary": paper.get("hasSuppl") == "Y",
        }

        # Extract basic paper information
        basic_info = {
            "title": paper.get("title"),
            "journal": paper.get("journalTitle"),
            "year": paper.get("pubYear"),
            "authors": paper.get("authorString"),
            "publication_type": paper.get("pubType"),
        }

        # Remove None values from basic_info
        basic_info = {k: v for k, v in basic_info.items() if v is not None}

        # Compile final result
        result_data: dict[str, Any] = {
            "identifiers": identifiers,
            "urls": urls,
            "access": access,
            "basic_info": basic_info,
            "_search_info": {
                "input_identifier": identifier,
                "detected_type": id_type,
                "normalized_identifier": normalized_id,
                "query_used": query,
                "source": "europepmc",
            },
        }

        # Save to file if requested
        saved_path = None
        if save_file or save_to:
            try:
                clean_id = str(identifier).replace("/", "_").replace(":", "_")
                saved_path = file_manager.handle_file_save(
                    content=result_data,
                    base_name="europepmc_identifiers",
                    identifier=clean_id,
                    file_format="json",
                    save_file=save_file,
                    save_to=save_to,
                    use_temp_dir=False,
                )
                if saved_path:
                    logger.info(f"Europe PMC identifiers saved to: {saved_path}")
            except Exception as e:
                logger.warning(f"Failed to save identifiers: {e}")

        # Add save info if file was saved
        if saved_path:
            result_data["saved_to"] = str(saved_path)

        return result_data

    except Exception as e:
        logger.error(
            f"Error getting identifiers from Europe PMC for '{identifier}': {e}"
        )
        return None


def get_europepmc_full_text(
    identifier: str,
    save_file: bool = False,
    save_to: str | None = None,
    offset: int = 0,
    limit: int | None = None,
) -> dict[str, Any] | None:
    """Get LLM-friendly full text content from Europe PMC in Markdown format.

    Retrieves full text XML from Europe PMC and converts it to clean, structured
    Markdown optimized for LLM consumption. Handles tables, figures, equations,
    and section structure while applying content limits to prevent token overflow.

    **BEST FOR**: Getting complete paper content for LLM analysis
    **INPUT**: ONE specific identifier (DOI, PMID, or PMCID)
    **OUTPUT**: Clean Markdown with preserved structure, tables, and figures

    Args:
        identifier: Any scientific identifier - DOI, PMID, or PMCID in any format:
            - DOI: "10.1038/nature12373", "doi:10.1038/nature12373"
            - PMID: "23851394", "PMID:23851394", "pmid:23851394"
            - PMCID: "PMC3737249", "3737249", "PMC:3737249"
        save_file: Whether to save full text to temp directory with
            auto-generated filename
        save_to: Specific path to save full text (overrides save_file if provided)
        offset: Starting character position for content windowing (0-based, default: 0).
            Allows viewing specific portions of large documents.
            Use with limit for pagination.
        limit: Maximum number of characters to return (None = no limit, default: None).
            When combined with offset, enables windowing through large content.
            Full content is always saved to file
            when save_file=True or save_to is provided.

    Returns:
        Dictionary with clean Markdown content and metadata:
        {
            "content": "# Title\n\n## Abstract\n...",  # LLM-ready Markdown
            "sections": {                               # Structured sections
                "abstract": "...",
                "introduction": "...",
                "methods": "...",
                "results": "...",
                "discussion": "...",
                "references": "..."
            },
            "metadata": {                               # Paper metadata
                "title": "...",
                "authors": "...",
                "journal": "...",
                "year": "..."
            },
            "source_info": {                           # Technical details
                "xml_source": "europe_pmc",
                "conversion_method": "jats_to_markdown",
                "original_format": "xml"
            },
            "saved_to": "/path/to/file",               # If saved
            "windowed": bool,                          # If content was windowed
            "content_length": 45000                    # Character count
        }

        Returns None if no full text found or identifier invalid.

    Examples:
        # Get full text as Markdown
        >>> result = get_europepmc_full_text("10.1038/nature12373")
        >>> result["content"][:100]
        '# CRISPR-Cas systems: RNA-mediated adaptive immunity\\n\\n## Abstract\\n...'
        >>> result["sections"]["abstract"]
        'Clustered regularly interspaced short palindromic...'

        # Save to file
        >>> result = get_europepmc_full_text("PMC3737249", save_file=True)
        >>> result["saved_to"]
        '/Users/.../Documents/artl-mcp/europepmc_fulltext_PMC3737249.md'

        # Check if content was truncated
        >>> if result["windowed"]:
        ...     print(f"Full content saved to: {result['saved_to']}")

    Perfect for:
    - LLM analysis of complete scientific papers
    - Converting papers to readable Markdown format
    - Extracting structured content (methods, results, etc.)
    - Research requiring full paper content with preserved formatting
    """
    try:
        # First, get paper metadata to find the Europe PMC ID
        paper_data = get_europepmc_paper_by_id(identifier)
        if not paper_data:
            logger.warning(f"No paper found in Europe PMC for identifier: {identifier}")
            return None

        # Extract PMCID for full text XML endpoint
        # (only PMC articles have full text XML)
        pmcid = paper_data.get("pmcid")

        if not pmcid:
            logger.info(
                f"No PMCID found for {identifier} - "
                f"full text XML only available for PMC articles"
            )
            return None

        # Construct Europe PMC full text XML URL using PMCID
        xml_url = (
            f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML"
        )

        logger.info(f"Fetching full text XML from: {xml_url}")

        # Set headers for Europe PMC API
        headers = {
            "Accept": "application/xml",
            "User-Agent": "ARTL-MCP/1.0 (https://github.com/contextualizer-ai/artl-mcp)",
        }

        # Fetch XML content
        response = requests.get(xml_url, headers=headers, timeout=30)

        if response.status_code == 404:
            logger.info(
                f"No full text XML available for {identifier} (PMCID: {pmcid}) - "
                f"Europe PMC returned 404"
            )
            return None

        response.raise_for_status()
        xml_content = response.text

        if not xml_content.strip():
            logger.warning(f"Empty XML response for {identifier}")
            return None

        # Convert XML to Markdown using lxml
        markdown_content, sections = _convert_jats_xml_to_markdown(xml_content)

        if not markdown_content:
            logger.warning(f"Failed to convert XML to Markdown for {identifier}")
            return None

        # Extract basic metadata from paper_data
        metadata = {
            "title": paper_data.get("title", ""),
            "authors": paper_data.get("authorString", ""),
            "journal": paper_data.get("journalTitle", ""),
            "year": paper_data.get("pubYear", ""),
            "doi": paper_data.get("doi", ""),
            "pmid": paper_data.get("pmid", ""),
            "pmcid": paper_data.get("pmcid", ""),
        }

        # Remove None values from metadata
        metadata = {k: v for k, v in metadata.items() if v}

        # Source information
        source_info = {
            "xml_source": "europe_pmc",
            "conversion_method": "jats_to_markdown",
            "original_format": "xml",
            "xml_url": xml_url,
            "europepmc_id": pmcid,
            "source_database": "PMC",
        }

        # Save to file if requested
        saved_path = None
        if save_file or save_to:
            try:
                clean_id = str(identifier).replace("/", "_").replace(":", "_")
                saved_path = file_manager.handle_file_save(
                    content=markdown_content,
                    base_name="europepmc_fulltext",
                    identifier=clean_id,
                    file_format="md",  # Save as Markdown
                    save_file=save_file,
                    save_to=save_to,
                    use_temp_dir=False,
                )
                if saved_path:
                    logger.info(f"Europe PMC full text saved to: {saved_path}")
            except Exception as e:
                logger.warning(f"Failed to save full text: {e}")

        # Apply content windowing for return to LLM if requested
        windowed_content, was_windowed = _apply_content_windowing(
            markdown_content, str(saved_path) if saved_path else None, offset, limit
        )

        result_data = {
            "content": windowed_content,
            "sections": sections,
            "metadata": metadata,
            "source_info": source_info,
            "saved_to": str(saved_path) if saved_path else None,
            "content_length": len(markdown_content),
            "windowed": was_windowed,
        }

        return result_data

    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching full text XML for {identifier}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error getting Europe PMC full text for '{identifier}': {e}")
        return None


def _convert_jats_xml_to_markdown(xml_content: str) -> tuple[str, dict[str, str]]:
    """Convert JATS XML to clean Markdown format.

    Parses scientific article XML (JATS format) and converts to LLM-friendly
    Markdown with preserved structure, tables, and figures.

    Args:
        xml_content: Raw XML content from Europe PMC

    Returns:
        Tuple of (markdown_content, sections_dict)
        - markdown_content: Complete article as Markdown string
        - sections_dict: Dictionary of individual sections
    """
    import re

    from lxml import etree

    try:
        # Parse XML with lxml
        root = etree.fromstring(xml_content.encode("utf-8"))

        markdown_parts = []
        sections = {}

        # Extract article title
        title_elem = root.find(".//article-title")
        if title_elem is not None:
            title = _get_text_content(title_elem)
            markdown_parts.append(f"# {title}\n")
            sections["title"] = title

        # Extract authors
        authors = []
        for contrib in root.findall(".//contrib[@contrib-type='author']"):
            given_names = contrib.find(".//given-names")
            surname = contrib.find(".//surname")
            if given_names is not None and surname is not None:
                full_name = (
                    f"{_get_text_content(given_names)} {_get_text_content(surname)}"
                )
                authors.append(full_name)

        if authors:
            authors_str = ", ".join(authors)
            markdown_parts.append(f"**Authors:** {authors_str}\n")
            sections["authors"] = authors_str

        # Extract abstract
        abstract_elem = root.find(".//abstract")
        if abstract_elem is not None:
            abstract_md = _convert_element_to_markdown(abstract_elem, level=2)
            if abstract_md.strip():
                markdown_parts.append(f"## Abstract\n\n{abstract_md}\n")
                sections["abstract"] = _get_text_content(abstract_elem)

        # Extract body sections
        body_elem = root.find(".//body")
        if body_elem is not None:
            for sec in body_elem.findall(".//sec"):
                section_md = _convert_section_to_markdown(sec, level=2)
                if section_md.strip():
                    markdown_parts.append(f"{section_md}\n")

                    # Try to identify section type
                    title_elem = sec.find(".//title")
                    if title_elem is not None:
                        title = _get_text_content(title_elem).lower()
                        # Map common section titles
                        if "introduction" in title:
                            sections["introduction"] = _get_text_content(sec)
                        elif "method" in title or "material" in title:
                            sections["methods"] = _get_text_content(sec)
                        elif "result" in title:
                            sections["results"] = _get_text_content(sec)
                        elif "discussion" in title or "conclusion" in title:
                            sections["discussion"] = _get_text_content(sec)

        # Extract references
        ref_list = root.find(".//ref-list")
        if ref_list is not None:
            refs_md = _convert_references_to_markdown(ref_list)
            if refs_md.strip():
                markdown_parts.append(f"## References\n\n{refs_md}\n")
                sections["references"] = _get_text_content(ref_list)

        # Combine all parts
        full_markdown = "\n".join(markdown_parts)

        # Clean up extra whitespace
        full_markdown = re.sub(r"\n{3,}", "\n\n", full_markdown)

        return full_markdown, sections

    except etree.XMLSyntaxError as e:
        logger.error(f"XML parsing error: {e}")
        return "", {}
    except Exception as e:
        logger.error(f"Error converting XML to Markdown: {e}")
        return "", {}


def _convert_element_to_markdown(elem, level: int = 1) -> str:
    """Convert an XML element to Markdown format."""
    if elem is None:
        return ""

    markdown_parts = []

    # Handle different element types
    tag = elem.tag

    if tag == "p":
        # Paragraph
        text = _get_text_content(elem)
        if text.strip():
            markdown_parts.append(f"{text}\n")

    elif tag == "title":
        # Section title
        text = _get_text_content(elem)
        if text.strip():
            heading = "#" * level
            markdown_parts.append(f"{heading} {text}\n")

    elif tag == "table-wrap":
        # Table
        table_md = _convert_table_to_markdown(elem)
        if table_md:
            markdown_parts.append(f"{table_md}\n")

    elif tag == "fig":
        # Figure
        fig_md = _convert_figure_to_markdown(elem)
        if fig_md:
            markdown_parts.append(f"{fig_md}\n")

    elif tag in ["list", "list-item"]:
        # Lists
        list_md = _convert_list_to_markdown(elem)
        if list_md:
            markdown_parts.append(f"{list_md}\n")

    else:
        # Process child elements
        for child in elem:
            child_md = _convert_element_to_markdown(child, level)
            if child_md:
                markdown_parts.append(child_md)

    return "".join(markdown_parts)


def _convert_section_to_markdown(sec_elem, level: int = 2) -> str:
    """Convert a section element to Markdown."""
    markdown_parts = []

    # Section title
    title_elem = sec_elem.find(".//title")
    if title_elem is not None:
        title = _get_text_content(title_elem)
        if title.strip():
            heading = "#" * level
            markdown_parts.append(f"{heading} {title}\n\n")

    # Section content
    for child in sec_elem:
        if child.tag != "title":  # Skip title, already processed
            if child.tag == "sec":
                # Nested section
                nested_md = _convert_section_to_markdown(child, level + 1)
                if nested_md:
                    markdown_parts.append(nested_md)
            elif child.tag == "p":
                # Paragraph
                text = _get_text_content(child)
                if text.strip():
                    markdown_parts.append(f"{text}\n\n")
            elif child.tag == "table-wrap":
                # Table
                table_md = _convert_table_to_markdown(child)
                if table_md:
                    markdown_parts.append(f"{table_md}\n\n")
            elif child.tag == "fig":
                # Figure
                fig_md = _convert_figure_to_markdown(child)
                if fig_md:
                    markdown_parts.append(f"{fig_md}\n\n")

    return "".join(markdown_parts)


def _convert_table_to_markdown(table_elem) -> str:
    """Convert a table element to Markdown table format."""
    try:
        table = table_elem.find(".//table")
        if table is None:
            return ""

        markdown_rows = []

        # Process table rows
        rows = table.findall(".//tr")
        if not rows:
            return ""

        for i, row in enumerate(rows):
            cells = row.findall(".//td") + row.findall(".//th")
            if cells:
                cell_texts = [_get_text_content(cell).strip() for cell in cells]
                markdown_row = "| " + " | ".join(cell_texts) + " |"
                markdown_rows.append(markdown_row)

                # Add header separator after first row
                if i == 0:
                    separator = (
                        "| "
                        + " | ".join(["-" * max(3, len(text)) for text in cell_texts])
                        + " |"
                    )
                    markdown_rows.append(separator)

        if markdown_rows:
            # Add table caption if available
            caption_elem = table_elem.find(".//caption")
            if caption_elem is not None:
                caption = _get_text_content(caption_elem)
                if caption.strip():
                    return f"**Table:** {caption}\n\n" + "\n".join(markdown_rows)

            return "\n".join(markdown_rows)

        return ""

    except Exception as e:
        logger.warning(f"Error converting table to Markdown: {e}")
        return ""


def _convert_figure_to_markdown(fig_elem) -> str:
    """Convert a figure element to Markdown format."""
    try:
        # Get figure caption
        caption_elem = fig_elem.find(".//caption")
        if caption_elem is not None:
            caption = _get_text_content(caption_elem)
            if caption.strip():
                return f"![Figure: {caption}](figure_description)"

        # Fallback to figure label
        label_elem = fig_elem.find(".//label")
        if label_elem is not None:
            label = _get_text_content(label_elem)
            if label.strip():
                return f"![{label}](figure_description)"

        return "![Figure](figure_description)"

    except Exception as e:
        logger.warning(f"Error converting figure to Markdown: {e}")
        return ""


def _convert_list_to_markdown(list_elem) -> str:
    """Convert a list element to Markdown format."""
    try:
        items = []
        for item in list_elem.findall(".//list-item"):
            text = _get_text_content(item)
            if text.strip():
                items.append(f"- {text}")

        return "\n".join(items) if items else ""

    except Exception as e:
        logger.warning(f"Error converting list to Markdown: {e}")
        return ""


def _convert_references_to_markdown(ref_list_elem) -> str:
    """Convert references to Markdown format."""
    try:
        refs = []
        for ref in ref_list_elem.findall(".//ref"):
            # Try to get citation text
            citation = ref.find(".//mixed-citation") or ref.find(".//citation")
            if citation is not None:
                ref_text = _get_text_content(citation)
                if ref_text.strip():
                    refs.append(f"- {ref_text}")

        return "\n".join(refs) if refs else ""

    except Exception as e:
        logger.warning(f"Error converting references to Markdown: {e}")
        return ""


def _get_text_content(elem) -> str:
    """Extract clean text content from an XML element."""
    if elem is None:
        return ""

    # Get all text including from child elements
    text_parts = []

    # Add element's direct text
    if elem.text:
        text_parts.append(elem.text)

    # Recursively add text from child elements
    for child in elem:
        child_text = _get_text_content(child)
        if child_text:
            text_parts.append(child_text)

        # Add tail text after child element
        if child.tail:
            text_parts.append(child.tail)

    # Join and clean up
    full_text = "".join(text_parts)

    # Clean up whitespace
    import re

    full_text = re.sub(r"\s+", " ", full_text)

    return full_text.strip()


def get_europepmc_pdf(
    identifier: str, save_to: str | None = None, filename: str | None = None
) -> dict[str, Any] | None:
    """Download PDF from Europe PMC for any scientific identifier.

    Searches Europe PMC for the paper, finds available PDF URLs from the paper's
    full text URL list, and downloads the PDF file directly. Works with DOI, PMID,
    or PMCID identifiers.

    **BEST FOR**: Downloading PDF files from Europe PMC
    **INPUT**: ONE specific identifier (DOI, PMID, or PMCID)
    **OUTPUT**: Downloaded PDF file with metadata about the download

    Args:
        identifier: Any scientific identifier - DOI, PMID, or PMCID in any format:
            - DOI: "10.1038/nature12373", "doi:10.1038/nature12373"
            - PMID: "23851394", "PMID:23851394", "pmid:23851394"
            - PMCID: "PMC3737249", "3737249", "PMC:3737249"
        save_to: Specific path to save PDF (overrides filename if provided)
        filename: Custom filename for the PDF (will add .pdf extension if missing)

    Returns:
        Dictionary with download results and file info:
        {
            "saved_to": "/path/to/file.pdf",        # Path where PDF was saved
            "file_size_bytes": 1048576,             # Size of downloaded PDF
            "success": True,                        # Download success status
            "pdf_url": "https://...",               # URL used for download
            "identifier": "10.1038/nature12373",   # Input identifier
            "paper_info": {                         # Basic paper metadata
                "title": "...",
                "authors": "...",
                "journal": "...",
                "year": "..."
            }
        }

        Returns None if no PDF found or identifier invalid.

    Examples:
        # Download PDF for a DOI
        >>> result = get_europepmc_pdf("10.1038/nature12373")
        >>> result["saved_to"]
        '/Users/.../Documents/artl-mcp/europepmc_pdf_10_1038_nature12373.pdf'
        >>> result["success"]
        True

        # Download with custom filename
        >>> result = get_europepmc_pdf("PMC3737249", filename="my_paper.pdf")
        >>> result["saved_to"]
        '/Users/.../Documents/artl-mcp/my_paper.pdf'

        # Download to specific path
        >>> result = get_europepmc_pdf(
        ...     "23851394", save_to="/path/to/paper.pdf"
        ... )

    Perfect for:
    - Downloading open access PDFs from Europe PMC
    - Getting PDF files for papers found through Europe PMC search
    - Building PDF archives from scientific literature
    - Accessing full-text papers in PDF format
    """
    try:
        # First, get paper metadata from Europe PMC
        paper_data = get_europepmc_paper_by_id(identifier)
        if not paper_data:
            logger.warning(f"No paper found in Europe PMC for identifier: {identifier}")
            return None

        # Extract basic paper information for metadata
        paper_info = {
            "title": paper_data.get("title", ""),
            "authors": paper_data.get("authorString", ""),
            "journal": paper_data.get("journalTitle", ""),
            "year": paper_data.get("pubYear", ""),
            "doi": paper_data.get("doi", ""),
            "pmid": paper_data.get("pmid", ""),
            "pmcid": paper_data.get("pmcid", ""),
        }

        # Remove None values from paper_info
        paper_info = {k: v for k, v in paper_info.items() if v}

        # Look for PDF URLs in the full text URL list
        pdf_url = None
        full_text_urls = []

        if "fullTextUrlList" in paper_data and paper_data["fullTextUrlList"]:
            for url_entry in paper_data["fullTextUrlList"].get("fullTextUrl", []):
                url = url_entry.get("url", "")
                availability = url_entry.get("availability", "")
                document_style = url_entry.get("documentStyle", "")
                site = url_entry.get("site", "")

                full_text_urls.append(
                    {
                        "url": url,
                        "availability": availability,
                        "document_style": document_style,
                        "site": site,
                    }
                )

                # Look for PDF URLs - prioritize different types
                if url and (
                    url.lower().endswith(".pdf") or "pdf" in document_style.lower()
                ):
                    if not pdf_url:  # Take the first PDF found
                        pdf_url = url
                    # Prefer Open Access PDFs
                    elif availability.lower() == "open access":
                        pdf_url = url

        # If no direct PDF found, check if paper has PMC full text access
        if not pdf_url and paper_data.get("inPMC") == "Y" and paper_data.get("pmcid"):
            # Try Europe PMC's PDF endpoint (if it exists)
            pmcid = paper_data.get("pmcid")
            potential_pdf_url = (
                f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/pdf"
            )

            # Test if the PDF endpoint exists
            try:
                test_response = requests.head(potential_pdf_url, timeout=10)
                if test_response.status_code == 200:
                    pdf_url = potential_pdf_url
            except requests.exceptions.RequestException:
                pass  # PDF endpoint doesn't exist or isn't accessible

        if not pdf_url:
            logger.info(f"No PDF URL found for {identifier} in Europe PMC")
            return {
                "saved_to": None,
                "file_size_bytes": 0,
                "success": False,
                "pdf_url": None,
                "identifier": identifier,
                "paper_info": paper_info,
                "error": "No PDF URL found in Europe PMC data",
                "available_urls": full_text_urls,
            }

        logger.info(f"Found PDF URL for {identifier}: {pdf_url}")

        # Generate filename if not provided
        if not filename and not save_to:
            clean_id = str(identifier).replace("/", "_").replace(":", "_")
            filename = f"europepmc_pdf_{clean_id}.pdf"

        # Download the PDF using existing functionality
        download_result = download_pdf_from_url(pdf_url, save_to, filename)

        # Enhance the result with Europe PMC specific information
        if download_result:
            # Create enhanced result with proper typing
            enhanced_result: dict[str, Any] = dict(download_result)
            enhanced_result["identifier"] = identifier
            enhanced_result["paper_info"] = paper_info
            enhanced_result["available_urls"] = full_text_urls
            enhanced_result["source"] = "europe_pmc"
            return enhanced_result

        return download_result

    except Exception as e:
        logger.error(f"Error getting PDF from Europe PMC for '{identifier}': {e}")
        return {
            "saved_to": None,
            "file_size_bytes": 0,
            "success": False,
            "pdf_url": None,
            "identifier": identifier,
            "paper_info": {},
            "error": f"Unexpected error: {e}",
        }


def get_europepmc_pdf_as_markdown(
    identifier: str,
    save_file: bool = False,
    save_to: str | None = None,
    extract_tables: bool = True,
    processing_method: str = "auto",
    offset: int = 0,
    limit: int | None = None,
) -> dict[str, Any] | None:
    """Download PDF from Europe PMC and convert to LLM-friendly Markdown in memory.

    Streams PDF content directly from Europe PMC, converts to structured Markdown
    using advanced PDF processing libraries (MarkItDown + pdfplumber), with no
    temporary disk files. Optimized for academic papers with tables and structure.

    **BEST FOR**: Getting PDF content as structured Markdown for LLM analysis
    **INPUT**: ONE specific identifier (DOI, PMID, or PMCID)
    **OUTPUT**: Clean Markdown content with preserved structure, tables, and metadata

    Args:
        identifier: Any scientific identifier - DOI, PMID, or PMCID in any format:
            - DOI: "10.1038/nature12373", "doi:10.1038/nature12373"
            - PMID: "23851394", "PMID:23851394", "pmid:23851394"
            - PMCID: "PMC3737249", "3737249", "PMC:3737249"
        save_file: Whether to save Markdown to temp directory with
            auto-generated filename
        save_to: Specific path to save Markdown (overrides save_file if provided)
        extract_tables: Whether to use table-aware processing for better
            structured data extraction
        processing_method: Method to use - "auto", "markitdown", "pdfplumber",
            or "hybrid"
        offset: Starting character position for content windowing (0-based, default: 0).
            Allows viewing specific portions of large documents.
            Use with limit for pagination.
        limit: Maximum number of characters to return (None = no limit, default: None).
            When combined with offset, enables windowing through large content.
            Full content is always saved to file when save_file=True
            or save_to is provided.

    Returns:
        Dictionary with Markdown content and metadata:
        {
            "content": "# Title\n\n## Abstract\n...",  # LLM-ready Markdown
            "format": "markdown",
            "processing": {
                "method": "hybrid_in_memory",          # Processing approach used
                "tables_extracted": 3,               # Number of tables found
                "in_memory": True,                    # No disk I/O performed
                "processing_time": 2.45              # Seconds taken
            },
            "paper_info": {                          # Basic paper metadata
                "title": "...",
                "authors": "...",
                "journal": "...",
                "year": "..."
            },
            "pdf_info": {
                "pdf_url": "https://...",            # PDF source URL
                "file_size_bytes": 1048576,          # PDF size in memory
                "page_count": 12                     # Number of pages processed
            },
            "saved_to": "/path/to/file.md",          # If saved to file
            "windowed": bool,                        # If content was windowed
            "content_length": 45000                  # Character count
        }

        Returns None if no PDF found or identifier invalid.

    Examples:
        # Quick Markdown conversion
        >>> result = get_europepmc_pdf_as_markdown("10.1038/nature12373")
        >>> result["content"][:100]
        '# CRISPR-Cas systems: RNA-mediated adaptive immunity\\n\\n## Abstract\\n...'
        >>> result["processing"]["tables_extracted"]
        3

        # Table-focused processing for data-heavy papers
        >>> result = get_europepmc_pdf_as_markdown(
        ...     "PMC3737249", extract_tables=True, processing_method="pdfplumber"
        ... )
        >>> result["processing"]["method"]
        'pdfplumber_in_memory'

        # Save Markdown to file
        >>> result = get_europepmc_pdf_as_markdown(
        ...     "23851394", save_file=True
        ... )
        >>> result["saved_to"]
        '/Users/.../Documents/artl-mcp/europepmc_pdf_markdown_23851394.md'

    Perfect for:
    - LLM analysis of complete scientific papers in structured format
    - Extracting tables and data from academic PDFs
    - Converting PDFs to readable Markdown without disk I/O
    - Research workflows requiring structured paper content
    - High-throughput PDF processing with memory efficiency
    """
    import time

    try:
        start_time = time.time()

        # Step 1: Get PDF URL from Europe PMC (reuse existing logic)
        paper_data = get_europepmc_paper_by_id(identifier)
        if not paper_data:
            logger.warning(f"No paper found in Europe PMC for identifier: {identifier}")
            return None

        # Extract basic paper information for metadata
        paper_info = {
            "title": paper_data.get("title", ""),
            "authors": paper_data.get("authorString", ""),
            "journal": paper_data.get("journalTitle", ""),
            "year": paper_data.get("pubYear", ""),
            "doi": paper_data.get("doi", ""),
            "pmid": paper_data.get("pmid", ""),
            "pmcid": paper_data.get("pmcid", ""),
        }
        paper_info = {k: v for k, v in paper_info.items() if v}

        # Step 2: Find PDF URL using existing logic from get_europepmc_pdf
        pdf_url = None
        full_text_urls = []

        if "fullTextUrlList" in paper_data and paper_data["fullTextUrlList"]:
            for url_entry in paper_data["fullTextUrlList"].get("fullTextUrl", []):
                url = url_entry.get("url", "")
                availability = url_entry.get("availability", "")
                document_style = url_entry.get("documentStyle", "")

                full_text_urls.append(url_entry)

                # Look for PDF URLs - prioritize different types
                if url and (
                    url.lower().endswith(".pdf") or "pdf" in document_style.lower()
                ):
                    if not pdf_url:  # Take the first PDF found
                        pdf_url = url
                    # Prefer Open Access PDFs
                    elif availability.lower() == "open access":
                        pdf_url = url

        # Fallback: try Europe PMC PDF endpoint
        if not pdf_url and paper_data.get("inPMC") == "Y" and paper_data.get("pmcid"):
            pmcid = paper_data.get("pmcid")
            potential_pdf_url = (
                f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/pdf"
            )
            try:
                test_response = requests.head(potential_pdf_url, timeout=10)
                if test_response.status_code == 200:
                    pdf_url = potential_pdf_url
            except requests.exceptions.RequestException:
                pass

        if not pdf_url:
            logger.info(f"No PDF URL found for {identifier} in Europe PMC")
            return None

        logger.info(f"Found PDF URL for {identifier}: {pdf_url}")

        # Step 3: Download PDF to memory (streaming)
        response = requests.get(pdf_url, timeout=60)
        response.raise_for_status()

        pdf_size = len(response.content)
        pdf_bytes = io.BytesIO(response.content)

        # Step 4: Process PDF in memory using the selected method
        processing_result = _process_pdf_in_memory(
            pdf_bytes, processing_method, extract_tables
        )

        processing_time = time.time() - start_time

        # Step 5: Save to file if requested
        saved_path = None
        if save_file or save_to:
            try:
                clean_id = str(identifier).replace("/", "_").replace(":", "_")
                saved_path = file_manager.handle_file_save(
                    content=processing_result["content"],
                    base_name="europepmc_pdf_markdown",
                    identifier=clean_id,
                    file_format="md",
                    save_file=save_file,
                    save_to=save_to,
                    use_temp_dir=False,
                )
                if saved_path:
                    logger.info(f"PDF Markdown saved to: {saved_path}")
            except Exception as e:
                logger.warning(f"Failed to save PDF Markdown: {e}")

        # Step 6: Apply content windowing if requested
        windowed_content, was_windowed = _apply_content_windowing(
            processing_result["content"],
            str(saved_path) if saved_path else None,
            offset,
            limit,
        )

        # Step 7: Compile comprehensive result
        return {
            "content": windowed_content,
            "format": "markdown",
            "processing": {
                "method": f"{processing_result['method']}_in_memory",
                "tables_extracted": processing_result.get("tables_extracted", 0),
                "in_memory": True,
                "processing_time": round(processing_time, 2),
            },
            "paper_info": paper_info,
            "pdf_info": {
                "pdf_url": pdf_url,
                "file_size_bytes": pdf_size,
                "page_count": processing_result.get("page_count", 0),
            },
            "identifier": identifier,
            "saved_to": str(saved_path) if saved_path else None,
            "content_length": len(processing_result["content"]),
            "windowed": was_windowed,
            "source": "europe_pmc_pdf_streaming",
        }

    except requests.exceptions.RequestException as e:
        logger.error(f"Error downloading PDF for {identifier}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error processing PDF as Markdown for '{identifier}': {e}")
        return None


def _process_pdf_in_memory(
    pdf_bytes: io.BytesIO, method: str, extract_tables: bool
) -> dict[str, Any]:
    """Process PDF bytes in memory using the specified method.

    Args:
        pdf_bytes: PDF content as BytesIO object
        method: Processing method - "auto", "markitdown", "pdfplumber", or "hybrid"
        extract_tables: Whether to focus on table extraction

    Returns:
        Dictionary with processed content and metadata
    """

    # Determine the best method
    if method == "auto":
        method = "hybrid" if extract_tables else "markitdown"

    if method == "markitdown":
        return _process_with_markitdown(pdf_bytes)
    elif method == "pdfplumber":
        return _process_with_pdfplumber(pdf_bytes)
    elif method == "hybrid":
        return _process_with_hybrid(pdf_bytes)
    else:
        # Fallback to markitdown
        return _process_with_markitdown(pdf_bytes)


def _process_with_markitdown(pdf_bytes: io.BytesIO) -> dict[str, Any]:
    """Process PDF using MarkItDown for fast, structured Markdown conversion."""

    try:
        from markitdown import MarkItDown

        # Reset stream position
        pdf_bytes.seek(0)

        md = MarkItDown()
        result = md.convert(pdf_bytes)

        return {
            "content": result.text_content,
            "method": "markitdown",
            "tables_extracted": 0,  # MarkItDown doesn't provide table count
            "page_count": 0,  # MarkItDown doesn't provide page count
        }

    except Exception as e:
        logger.error(f"Error with MarkItDown processing: {e}")
        # Fallback to basic text extraction
        return _fallback_text_extraction(pdf_bytes)


def _process_with_pdfplumber(pdf_bytes: io.BytesIO) -> dict[str, Any]:
    """Process PDF using pdfplumber for excellent table extraction."""

    try:
        import pdfplumber

        # Reset stream position
        pdf_bytes.seek(0)

        with pdfplumber.open(pdf_bytes) as pdf:
            markdown_parts = []
            tables_found = 0

            for page_num, page in enumerate(pdf.pages):
                # Extract text
                page_text = page.extract_text() or ""

                # Extract tables
                page_tables = page.extract_tables()

                if page_tables:
                    for table in page_tables:
                        if table:  # Ensure table is not None/empty
                            table_md = _convert_table_to_markdown_simple(table)
                            # Insert table into text flow
                            page_text += f"\n\n{table_md}\n\n"
                            tables_found += 1

                if page_text.strip():
                    # Add page header if multi-page
                    if len(pdf.pages) > 1:
                        markdown_parts.append(f"## Page {page_num + 1}\n\n{page_text}")
                    else:
                        markdown_parts.append(page_text)

            content = "\n\n".join(markdown_parts)

            # Basic structure cleanup
            content = _clean_markdown_structure(content)

            return {
                "content": content,
                "method": "pdfplumber",
                "tables_extracted": tables_found,
                "page_count": len(pdf.pages),
            }

    except Exception as e:
        logger.error(f"Error with pdfplumber processing: {e}")
        return _fallback_text_extraction(pdf_bytes)


def _process_with_hybrid(pdf_bytes: io.BytesIO) -> dict[str, Any]:
    """Hybrid processing: try MarkItDown first, enhance with pdfplumber tables."""

    try:
        # First, try MarkItDown for structure
        markitdown_result = _process_with_markitdown(pdf_bytes)

        # Then extract tables separately with pdfplumber
        pdf_bytes.seek(0)  # Reset stream

        import pdfplumber

        with pdfplumber.open(pdf_bytes) as pdf:
            tables_found = 0
            table_sections = []

            for _page_num, page in enumerate(pdf.pages):
                page_tables = page.extract_tables()

                for table in page_tables:
                    if table:
                        table_md = _convert_table_to_markdown_simple(table)
                        table_sections.append(
                            f"### Table {tables_found + 1}\n\n{table_md}"
                        )
                        tables_found += 1

            # Combine MarkItDown content with extracted tables
            content = markitdown_result["content"]

            if table_sections:
                content += "\n\n## Extracted Tables\n\n" + "\n\n".join(table_sections)

            return {
                "content": content,
                "method": "hybrid",
                "tables_extracted": tables_found,
                "page_count": len(pdf.pages),
            }

    except Exception as e:
        logger.error(f"Error with hybrid processing: {e}")
        return _fallback_text_extraction(pdf_bytes)


def _convert_table_to_markdown_simple(table: list[list[str | None]]) -> str:
    """Convert a table (list of lists) to simple Markdown table format."""

    if not table or not table[0]:
        return ""

    markdown_rows = []

    # Process each row
    for i, row in enumerate(table):
        if row:  # Skip empty rows
            # Clean cell content
            cells = [str(cell).strip() if cell else "" for cell in row]

            # Create markdown row
            markdown_row = "| " + " | ".join(cells) + " |"
            markdown_rows.append(markdown_row)

            # Add separator after header row
            if i == 0 and len(cells) > 0:
                separator = (
                    "| "
                    + " | ".join(["-" * max(3, len(cell)) for cell in cells])
                    + " |"
                )
                markdown_rows.append(separator)

    return "\n".join(markdown_rows) if markdown_rows else ""


def _clean_markdown_structure(content: str) -> str:
    """Clean up and improve Markdown structure."""

    import re

    # Remove excessive whitespace
    content = re.sub(r"\n{3,}", "\n\n", content)

    # Ensure proper heading spacing
    content = re.sub(r"(\n#+[^\n]*)\n([^\n#])", r"\1\n\n\2", content)

    # Clean up table spacing
    content = re.sub(r"(\|[^\n]*\|)\n([^\|\n-])", r"\1\n\n\2", content)

    return content.strip()


def _fallback_text_extraction(pdf_bytes: io.BytesIO) -> dict[str, Any]:
    """
    Fallback to basic PDFMiner text extraction if advanced methods fail.

    Parameters:
        pdf_bytes (io.BytesIO): A BytesIO object containing the PDF file to
            extract text from.
    """
    try:
        from pdfminer.high_level import extract_text

        pdf_bytes.seek(0)
        text = extract_text(pdf_bytes)

        # Convert to basic Markdown
        content = text.strip()

        return {
            "content": content,
            "method": "fallback_pdfminer",
            "tables_extracted": 0,
            "page_count": 0,
        }

    except Exception as e:
        logger.error(f"Even fallback extraction failed: {e}")
        return {
            "content": "Error: Could not extract PDF content",
            "method": "error",
            "tables_extracted": 0,
            "page_count": 0,
        }
