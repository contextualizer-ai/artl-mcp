"""Enhanced identifier conversion utilities for scientific literature.

Provides comprehensive conversion between DOI, PMID, and PMCID formats,
including missing functionality like DOI to PMCID conversion and
comprehensive identifier mapping.
"""

import json
import logging

import requests

from .identifier_utils import IdentifierError, IdentifierUtils

logger = logging.getLogger(__name__)

# Default headers for API requests (following crawl-first best practices)
DEFAULT_HEADERS = {
    "User-Agent": "ARTL-MCP/1.0 (https://github.com/contextualizer-ai/artl-mcp)"
}

# API endpoints
NCBI_ID_CONVERTER_URL = "https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/"
PUBMED_ESUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"


class ConversionError(Exception):
    """Exception raised for identifier conversion errors."""

    pass


class IdentifierConverter:
    """Enhanced identifier conversion utilities."""

    @staticmethod
    def _make_api_request(url: str, params: dict, timeout: int = 10) -> dict | None:
        """Make API request with proper error handling.

        Args:
            url: API endpoint URL
            params: Request parameters
            timeout: Request timeout in seconds

        Returns:
            JSON response data or None on error
        """
        try:
            response = requests.get(
                url, params=params, headers=DEFAULT_HEADERS, timeout=timeout
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
    def doi_to_pmid(cls, doi: str, timeout: int = 10) -> str | None:
        """Convert DOI to PMID using NCBI ID Converter API.

        Args:
            doi: DOI in any supported format
            timeout: Request timeout in seconds

        Returns:
            PMID as string or None if conversion fails

        Examples:
            >>> IdentifierConverter.doi_to_pmid("10.1038/nature12373")
            '23851394'
            >>> IdentifierConverter.doi_to_pmid("doi:10.1038/nature12373")
            '23851394'
        """
        try:
            # Normalize DOI to raw format
            normalized_doi = IdentifierUtils.normalize_doi(doi, "raw")
        except IdentifierError as e:
            logger.warning(f"Invalid DOI for conversion: {doi} - {e}")
            return None

        params = {"ids": normalized_doi, "format": "json"}
        data = cls._make_api_request(NCBI_ID_CONVERTER_URL, params, timeout)

        if not data:
            return None

        try:
            records = data.get("records", [])
            if records:
                pmid = records[0].get("pmid")
                if pmid:
                    return IdentifierUtils.normalize_pmid(pmid, "raw")
        except (KeyError, IndexError, IdentifierError) as e:
            logger.warning(f"Error extracting PMID from response for DOI {doi}: {e}")

        return None

    @classmethod
    def doi_to_pmcid(cls, doi: str, timeout: int = 10) -> str | None:
        """Convert DOI to PMCID using NCBI ID Converter API.

        Args:
            doi: DOI in any supported format
            timeout: Request timeout in seconds

        Returns:
            PMCID as string or None if conversion fails

        Examples:
            >>> IdentifierConverter.doi_to_pmcid("10.1038/nature12373")
            'PMC3737249'
        """
        try:
            # Normalize DOI to raw format
            normalized_doi = IdentifierUtils.normalize_doi(doi, "raw")
        except IdentifierError as e:
            logger.warning(f"Invalid DOI for conversion: {doi} - {e}")
            return None

        params = {"ids": normalized_doi, "format": "json"}
        data = cls._make_api_request(NCBI_ID_CONVERTER_URL, params, timeout)

        if not data:
            return None

        try:
            records = data.get("records", [])
            if records:
                pmcid = records[0].get("pmcid")
                if pmcid:
                    return IdentifierUtils.normalize_pmcid(pmcid, "raw")
        except (KeyError, IndexError, IdentifierError) as e:
            logger.warning(f"Error extracting PMCID from response for DOI {doi}: {e}")

        return None

    @classmethod
    def pmid_to_doi(cls, pmid: str | int, timeout: int = 10) -> str | None:
        """Convert PMID to DOI using PubMed E-utilities.

        Args:
            pmid: PMID in any supported format
            timeout: Request timeout in seconds

        Returns:
            DOI as string or None if conversion fails

        Examples:
            >>> IdentifierConverter.pmid_to_doi("23851394")
            '10.1038/nature12373'
            >>> IdentifierConverter.pmid_to_doi("PMID:23851394")
            '10.1038/nature12373'
        """
        try:
            # Normalize PMID to raw format
            normalized_pmid = IdentifierUtils.normalize_pmid(pmid, "raw")
        except IdentifierError as e:
            logger.warning(f"Invalid PMID for conversion: {pmid} - {e}")
            return None

        params = {"db": "pubmed", "id": normalized_pmid, "retmode": "json"}
        data = cls._make_api_request(PUBMED_ESUMMARY_URL, params, timeout)

        if not data:
            return None

        try:
            article_info = data["result"][normalized_pmid]

            # Check articleids for DOI
            for aid in article_info.get("articleids", []):
                if aid.get("idtype") == "doi":
                    doi = aid.get("value")
                    if doi:
                        return IdentifierUtils.normalize_doi(doi, "raw")

            # Check elocationid for DOI (fallback)
            elocationid = article_info.get("elocationid", "")
            if elocationid and elocationid.startswith("10."):
                return IdentifierUtils.normalize_doi(elocationid, "raw")

        except (KeyError, IdentifierError) as e:
            logger.warning(f"Error extracting DOI from response for PMID {pmid}: {e}")

        return None

    @classmethod
    def pmid_to_pmcid(cls, pmid: str | int, timeout: int = 10) -> str | None:
        """Convert PMID to PMCID using PubMed E-utilities.

        Args:
            pmid: PMID in any supported format
            timeout: Request timeout in seconds

        Returns:
            PMCID as string or None if conversion fails

        Examples:
            >>> IdentifierConverter.pmid_to_pmcid("23851394")
            'PMC3737249'
        """
        try:
            # Normalize PMID to raw format
            normalized_pmid = IdentifierUtils.normalize_pmid(pmid, "raw")
        except IdentifierError as e:
            logger.warning(f"Invalid PMID for conversion: {pmid} - {e}")
            return None

        params = {"db": "pubmed", "id": normalized_pmid, "retmode": "json"}
        data = cls._make_api_request(PUBMED_ESUMMARY_URL, params, timeout)

        if not data:
            return None

        try:
            article_info = data["result"][normalized_pmid]

            # Check articleids for PMCID
            for aid in article_info.get("articleids", []):
                if aid.get("idtype") == "pmc":
                    pmcid = aid.get("value")
                    if pmcid:
                        return IdentifierUtils.normalize_pmcid(pmcid, "raw")

        except (KeyError, IdentifierError) as e:
            logger.warning(f"Error extracting PMCID from response for PMID {pmid}: {e}")

        return None

    @classmethod
    def pmcid_to_pmid(cls, pmcid: str | int, timeout: int = 10) -> str | None:
        """Convert PMCID to PMID using Entrez E-utilities.

        Args:
            pmcid: PMCID in any supported format
            timeout: Request timeout in seconds

        Returns:
            PMID as string or None if conversion fails

        Examples:
            >>> IdentifierConverter.pmcid_to_pmid("PMC3737249")
            '23851394'
            >>> IdentifierConverter.pmcid_to_pmid("3737249")
            '23851394'
        """
        try:
            # Normalize PMCID and extract numeric part
            normalized_pmcid = IdentifierUtils.normalize_pmcid(pmcid, "raw")
            numeric_pmcid = normalized_pmcid.replace("PMC", "")
        except IdentifierError as e:
            logger.warning(f"Invalid PMCID for conversion: {pmcid} - {e}")
            return None

        params = {"db": "pmc", "id": numeric_pmcid, "retmode": "json"}
        data = cls._make_api_request(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
            params,
            timeout,
        )

        if not data:
            return None

        try:
            uid = data["result"]["uids"][0]
            article_ids = data["result"][uid]["articleids"]

            for item in article_ids:
                if item.get("idtype") == "pmid":
                    pmid = item.get("value")
                    if pmid:
                        return IdentifierUtils.normalize_pmid(pmid, "raw")

        except (KeyError, IndexError, IdentifierError) as e:
            logger.warning(
                f"Error extracting PMID from response for PMCID {pmcid}: {e}"
            )

        return None

    @classmethod
    def pmcid_to_doi(cls, pmcid: str | int, timeout: int = 10) -> str | None:
        """Convert PMCID to DOI via PMID.

        Args:
            pmcid: PMCID in any supported format
            timeout: Request timeout in seconds

        Returns:
            DOI as string or None if conversion fails

        Examples:
            >>> IdentifierConverter.pmcid_to_doi("PMC3737249")
            '10.1038/nature12373'
        """
        # First convert PMCID to PMID
        pmid = cls.pmcid_to_pmid(pmcid, timeout)
        if not pmid:
            return None

        # Then convert PMID to DOI
        return cls.pmid_to_doi(pmid, timeout)

    @classmethod
    def get_comprehensive_ids(
        cls, identifier: str, timeout: int = 10
    ) -> dict[str, str | None]:
        """Get all available identifiers for a given identifier.

        Args:
            identifier: Any supported identifier (DOI, PMID, or PMCID)
            timeout: Request timeout in seconds

        Returns:
            Dictionary with all available identifiers

        Examples:
            >>> IdentifierConverter.get_comprehensive_ids("10.1038/nature12373")
            {
                'doi': '10.1038/nature12373',
                'pmid': '23851394',
                'pmcid': 'PMC3737249',
                'input_type': 'doi'
            }
        """
        try:
            # Identify and normalize input
            id_info = IdentifierUtils.normalize_identifier(identifier)
            id_type = id_info["type"]
            normalized_id = id_info["value"]
        except IdentifierError as e:
            logger.warning(f"Cannot identify input identifier: {identifier} - {e}")
            return {
                "doi": None,
                "pmid": None,
                "pmcid": None,
                "input_type": "unknown",
                "error": str(e),
            }

        result = {"doi": None, "pmid": None, "pmcid": None, "input_type": id_type}

        # Set the input identifier
        result[id_type] = normalized_id

        # Convert to other formats
        if id_type == "doi":
            result["pmid"] = cls.doi_to_pmid(normalized_id, timeout)
            result["pmcid"] = cls.doi_to_pmcid(normalized_id, timeout)
        elif id_type == "pmid":
            result["doi"] = cls.pmid_to_doi(normalized_id, timeout)
            result["pmcid"] = cls.pmid_to_pmcid(normalized_id, timeout)
        elif id_type == "pmcid":
            result["pmid"] = cls.pmcid_to_pmid(normalized_id, timeout)
            result["doi"] = cls.pmcid_to_doi(normalized_id, timeout)

        return result

    @classmethod
    def batch_convert_ids(
        cls, identifiers: list[str], target_type: str, timeout: int = 10
    ) -> dict[str, str | None]:
        """Convert multiple identifiers to a target type.

        Args:
            identifiers: List of identifiers to convert
            target_type: Target identifier type ('doi', 'pmid', or 'pmcid')
            timeout: Request timeout in seconds per request

        Returns:
            Dictionary mapping input identifiers to converted identifiers

        Examples:
            >>> IdentifierConverter.batch_convert_ids(
            ...     ["10.1038/nature12373", "PMC3737249"],
            ...     "pmid"
            ... )
            {
                '10.1038/nature12373': '23851394',
                'PMC3737249': '23851394'
            }
        """
        if target_type not in ["doi", "pmid", "pmcid"]:
            raise ConversionError(f"Invalid target type: {target_type}")

        results = {}

        for identifier in identifiers:
            try:
                comprehensive = cls.get_comprehensive_ids(identifier, timeout)
                results[identifier] = comprehensive.get(target_type)
            except Exception as e:
                logger.warning(f"Error converting {identifier}: {e}")
                results[identifier] = None

        return results


# Convenience functions for backward compatibility and simpler usage
def doi_to_pmid(doi: str, timeout: int = 10) -> str | None:
    """Convert DOI to PMID."""
    return IdentifierConverter.doi_to_pmid(doi, timeout)


def doi_to_pmcid(doi: str, timeout: int = 10) -> str | None:
    """Convert DOI to PMCID."""
    return IdentifierConverter.doi_to_pmcid(doi, timeout)


def pmid_to_doi(pmid: str | int, timeout: int = 10) -> str | None:
    """Convert PMID to DOI."""
    return IdentifierConverter.pmid_to_doi(pmid, timeout)


def pmid_to_pmcid(pmid: str | int, timeout: int = 10) -> str | None:
    """Convert PMID to PMCID."""
    return IdentifierConverter.pmid_to_pmcid(pmid, timeout)


def pmcid_to_pmid(pmcid: str | int, timeout: int = 10) -> str | None:
    """Convert PMCID to PMID."""
    return IdentifierConverter.pmcid_to_pmid(pmcid, timeout)


def pmcid_to_doi(pmcid: str | int, timeout: int = 10) -> str | None:
    """Convert PMCID to DOI."""
    return IdentifierConverter.pmcid_to_doi(pmcid, timeout)


def get_all_ids(identifier: str, timeout: int = 10) -> dict[str, str | None]:
    """Get all available identifiers for a given identifier."""
    return IdentifierConverter.get_comprehensive_ids(identifier, timeout)
