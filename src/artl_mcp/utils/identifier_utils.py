"""Identifier utilities for scientific literature.

This module provides comprehensive handling of scientific literature identifiers:
- DOI (Digital Object Identifier): 10.1234/example
- PMID (PubMed ID): 12345678
- PMCID (PubMed Central ID): PMC1234567

Supports multiple input formats and provides standardized output.
"""

import re
from typing import Literal
from urllib.parse import quote, unquote

# Type definitions
IDType = Literal["doi", "pmid", "pmcid", "unknown"]
IDFormat = Literal["raw", "curie", "url", "prefixed"]


class IdentifierError(Exception):
    """Exception raised for identifier validation or conversion errors."""

    pass


class IdentifierUtils:
    """Utilities for handling scientific literature identifiers."""

    # DOI patterns
    DOI_PATTERN = re.compile(r"^10\.\d{4,9}/[^\s]+$")
    DOI_URL_PATTERNS = [
        re.compile(r"https?://(?:dx\.)?doi\.org/(10\.\d{4,9}/[^\s?#]+)"),
        re.compile(r"https?://(?:www\.)?doi\.org/(10\.\d{4,9}/[^\s?#]+)"),
        re.compile(r"/(10\.\d{4,9}/[^\s?#/]+)/?$"),  # From URLs with DOI path
    ]
    DOI_CURIE_PATTERN = re.compile(r"^doi:(10\.\d{4,9}/[^\s]+)$")

    # PMID patterns
    PMID_PATTERN = re.compile(r"^\d{7,9}$")  # PMIDs are typically 7-9 digits
    PMID_PREFIXED_PATTERN = re.compile(r"^(?:PMID:?)(\d{7,9})$", re.IGNORECASE)

    # PMCID patterns
    PMCID_PATTERN = re.compile(r"^PMC\d+$")
    PMCID_PREFIXED_PATTERN = re.compile(r"^(?:PMC:?)?(PMC?\d+)$", re.IGNORECASE)
    PMCID_RAW_PATTERN = re.compile(r"^\d+$")  # Raw numeric PMCID

    @classmethod
    def identify_type(cls, identifier: str) -> IDType:
        """Identify the type of a scientific identifier.

        Args:
            identifier: The identifier string to analyze

        Returns:
            The identified type: 'doi', 'pmid', 'pmcid', or 'unknown'

        Examples:
            >>> IdentifierUtils.identify_type("10.1038/nature12373")
            'doi'
            >>> IdentifierUtils.identify_type("doi:10.1038/nature12373")
            'doi'
            >>> IdentifierUtils.identify_type("23851394")
            'pmid'
            >>> IdentifierUtils.identify_type("PMID:23851394")
            'pmid'
            >>> IdentifierUtils.identify_type("PMC3737249")
            'pmcid'
        """
        if not identifier or not isinstance(identifier, str):
            return "unknown"

        identifier = identifier.strip()

        # Check DOI patterns
        if cls.DOI_PATTERN.match(identifier):
            return "doi"
        if cls.DOI_CURIE_PATTERN.match(identifier):
            return "doi"
        for pattern in cls.DOI_URL_PATTERNS:
            if pattern.search(identifier):
                return "doi"

        # Check PMCID patterns (before PMID since PMC can contain digits)
        if cls.PMCID_PATTERN.match(identifier):
            return "pmcid"
        if cls.PMCID_PREFIXED_PATTERN.match(identifier.upper()):
            return "pmcid"

        # Check PMID patterns
        if cls.PMID_PATTERN.match(identifier):
            return "pmid"
        if cls.PMID_PREFIXED_PATTERN.match(identifier):
            return "pmid"

        return "unknown"

    @classmethod
    def normalize_doi(cls, doi: str, output_format: IDFormat = "raw") -> str:
        """Normalize a DOI to standard format.

        Args:
            doi: DOI in any supported format
            output_format: Desired output format

        Returns:
            Normalized DOI string

        Raises:
            IdentifierError: If DOI is invalid or cannot be normalized

        Examples:
            >>> IdentifierUtils.normalize_doi("https://doi.org/10.1038/nature12373")
            '10.1038/nature12373'
            >>> IdentifierUtils.normalize_doi("doi:10.1038/nature12373")
            '10.1038/nature12373'
            >>> IdentifierUtils.normalize_doi("10.1038/nature12373", "curie")
            'doi:10.1038/nature12373'
        """
        if not doi or not isinstance(doi, str):
            raise IdentifierError(f"Invalid DOI input: {doi}")

        doi = doi.strip()
        raw_doi = None

        # Extract raw DOI from various formats
        if cls.DOI_PATTERN.match(doi):
            raw_doi = doi
        elif cls.DOI_CURIE_PATTERN.match(doi):
            match = cls.DOI_CURIE_PATTERN.match(doi)
            if match:
                raw_doi = match.group(1)
        else:
            # Try URL patterns
            for pattern in cls.DOI_URL_PATTERNS:
                match = pattern.search(doi)
                if match:
                    raw_doi = unquote(match.group(1))
                    break

        if not raw_doi:
            raise IdentifierError(f"Could not extract valid DOI from: {doi}")

        # Validate extracted DOI
        if not cls.DOI_PATTERN.match(raw_doi):
            raise IdentifierError(f"Extracted DOI is invalid: {raw_doi}")

        # Format output
        if output_format == "raw":
            return raw_doi
        elif output_format == "curie":
            return f"doi:{raw_doi}"
        elif output_format == "url":
            return f"https://doi.org/{quote(raw_doi, safe='/')}"
        else:
            raise IdentifierError(f"Unsupported output format: {output_format}")

    @classmethod
    def normalize_pmid(cls, pmid: str | int, output_format: IDFormat = "raw") -> str:
        """Normalize a PMID to standard format.

        Args:
            pmid: PMID in any supported format
            output_format: Desired output format

        Returns:
            Normalized PMID string

        Raises:
            IdentifierError: If PMID is invalid or cannot be normalized

        Examples:
            >>> IdentifierUtils.normalize_pmid("PMID:23851394")
            '23851394'
            >>> IdentifierUtils.normalize_pmid(23851394)
            '23851394'
            >>> IdentifierUtils.normalize_pmid("23851394", "prefixed")
            'PMID:23851394'
        """
        if pmid is None:
            raise IdentifierError("PMID cannot be None")

        # Convert to string and strip
        pmid_str = str(pmid).strip()
        raw_pmid = None

        # Extract raw PMID
        if cls.PMID_PATTERN.match(pmid_str):
            raw_pmid = pmid_str
        else:
            # Check for prefixed format
            match = cls.PMID_PREFIXED_PATTERN.match(pmid_str)
            if match:
                raw_pmid = match.group(1)
            # Handle colon-separated format
            elif ":" in pmid_str:
                parts = pmid_str.split(":", 1)
                if len(parts) == 2 and cls.PMID_PATTERN.match(parts[1]):
                    raw_pmid = parts[1]

        if not raw_pmid:
            raise IdentifierError(f"Could not extract valid PMID from: {pmid}")

        # Validate
        if not cls.PMID_PATTERN.match(raw_pmid):
            raise IdentifierError(f"Invalid PMID format: {raw_pmid}")

        # Format output
        if output_format == "raw":
            return raw_pmid
        elif output_format == "prefixed":
            return f"PMID:{raw_pmid}"
        elif output_format == "curie":
            return f"pmid:{raw_pmid}"
        else:
            raise IdentifierError(f"Unsupported output format: {output_format}")

    @classmethod
    def normalize_pmcid(cls, pmcid: str | int, output_format: IDFormat = "raw") -> str:
        """Normalize a PMCID to standard format.

        Args:
            pmcid: PMCID in any supported format
            output_format: Desired output format

        Returns:
            Normalized PMCID string

        Raises:
            IdentifierError: If PMCID is invalid or cannot be normalized

        Examples:
            >>> IdentifierUtils.normalize_pmcid("PMC3737249")
            'PMC3737249'
            >>> IdentifierUtils.normalize_pmcid("3737249")
            'PMC3737249'
            >>> IdentifierUtils.normalize_pmcid("PMC:3737249")
            'PMC3737249'
        """
        if pmcid is None:
            raise IdentifierError("PMCID cannot be None")

        pmcid_str = str(pmcid).strip()
        raw_pmcid = None

        # Extract PMCID
        if cls.PMCID_PATTERN.match(pmcid_str.upper()):
            raw_pmcid = pmcid_str.upper()
        else:
            # Handle prefixed formats
            match = cls.PMCID_PREFIXED_PATTERN.match(pmcid_str)
            if match:
                extracted = match.group(1).upper()
                if not extracted.startswith("PMC"):
                    extracted = f"PMC{extracted}"
                raw_pmcid = extracted
            # Handle colon-separated format
            elif ":" in pmcid_str:
                parts = pmcid_str.split(":", 1)
                if len(parts) == 2:
                    candidate = parts[1].strip()
                    if candidate.upper().startswith("PMC"):
                        raw_pmcid = candidate.upper()
                    elif candidate.isdigit():
                        raw_pmcid = f"PMC{candidate}"
            # Handle raw numeric
            elif cls.PMCID_RAW_PATTERN.match(pmcid_str):
                raw_pmcid = f"PMC{pmcid_str}"

        if not raw_pmcid:
            raise IdentifierError(f"Could not extract valid PMCID from: {pmcid}")

        # Validate final format
        if not cls.PMCID_PATTERN.match(raw_pmcid):
            raise IdentifierError(f"Invalid PMCID format: {raw_pmcid}")

        # Format output
        if output_format == "raw":
            return raw_pmcid
        elif output_format == "prefixed":
            return raw_pmcid  # Already has PMC prefix
        elif output_format == "curie":
            return f"pmcid:{raw_pmcid}"
        else:
            raise IdentifierError(f"Unsupported output format: {output_format}")

    @classmethod
    def normalize_identifier(
        cls,
        identifier: str,
        id_type: IDType | None = None,
        output_format: IDFormat = "raw",
    ) -> dict[str, str]:
        """Normalize any scientific identifier to standard format.

        Args:
            identifier: The identifier to normalize
            id_type: Optional explicit type (auto-detected if None)
            output_format: Desired output format

        Returns:
            Dictionary with 'type', 'value', and 'format' keys

        Raises:
            IdentifierError: If identifier cannot be normalized

        Examples:
            >>> IdentifierUtils.normalize_identifier("doi:10.1038/nature12373")
            {'type': 'doi', 'value': '10.1038/nature12373', 'format': 'raw'}
            >>> IdentifierUtils.normalize_identifier(
            ...     "PMID:23851394", output_format="curie"
            ... )
            {'type': 'pmid', 'value': 'pmid:23851394', 'format': 'curie'}
        """
        if not identifier:
            raise IdentifierError("Identifier cannot be empty")

        # Auto-detect type if not provided
        detected_type = id_type or cls.identify_type(identifier)

        if detected_type == "unknown":
            raise IdentifierError(f"Cannot identify type of identifier: {identifier}")

        # Normalize based on type
        if detected_type == "doi":
            normalized = cls.normalize_doi(identifier, output_format)
        elif detected_type == "pmid":
            normalized = cls.normalize_pmid(identifier, output_format)
        elif detected_type == "pmcid":
            normalized = cls.normalize_pmcid(identifier, output_format)
        else:
            raise IdentifierError(f"Unsupported identifier type: {detected_type}")

        return {"type": detected_type, "value": normalized, "format": output_format}

    @classmethod
    def validate_identifier(
        cls, identifier: str, expected_type: IDType | None = None
    ) -> bool:
        """Validate if an identifier is properly formatted.

        Args:
            identifier: The identifier to validate
            expected_type: Optional expected type for validation

        Returns:
            True if valid, False otherwise

        Examples:
            >>> IdentifierUtils.validate_identifier("10.1038/nature12373", "doi")
            True
            >>> IdentifierUtils.validate_identifier("invalid-doi", "doi")
            False
        """
        try:
            detected_type = cls.identify_type(identifier)
            if expected_type and detected_type != expected_type:
                return False
            if detected_type == "unknown":
                return False
            # Try to normalize - if it fails, it's invalid
            cls.normalize_identifier(identifier)
            return True
        except IdentifierError:
            return False


# Convenience functions for backward compatibility
def normalize_doi(doi: str, output_format: IDFormat = "raw") -> str:
    """Normalize a DOI to standard format."""
    return IdentifierUtils.normalize_doi(doi, output_format)


def normalize_pmid(pmid: str | int, output_format: IDFormat = "raw") -> str:
    """Normalize a PMID to standard format."""
    return IdentifierUtils.normalize_pmid(pmid, output_format)


def normalize_pmcid(pmcid: str | int, output_format: IDFormat = "raw") -> str:
    """Normalize a PMCID to standard format."""
    return IdentifierUtils.normalize_pmcid(pmcid, output_format)


def identify_type(identifier: str) -> IDType:
    """Identify the type of a scientific identifier."""
    return IdentifierUtils.identify_type(identifier)


def validate_identifier(identifier: str, expected_type: IDType | None = None) -> bool:
    """Validate if an identifier is properly formatted."""
    return IdentifierUtils.validate_identifier(identifier, expected_type)
