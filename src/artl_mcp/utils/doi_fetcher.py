import re
from typing import Any

import requests
import os
from pydantic import BaseModel, Field


class FullTextInfo(BaseModel):
    """Data model for full text information."""

    success: bool = True
    abstract: str | None = Field(None, description="Abstract of the article")
    text: str | None = Field(None, description="Full text of the article")
    source: str | None = Field(None, description="Source of the full text")
    metadata: dict[str, Any] | None = Field(None, description="Metadata of the article")
    pdf_url: str | None = Field(
        None, description="URL to the PDF version of the article"
    )


class DOIFetcher:
    """Fetch metadata and full text for a DOI using various APIs."""

    def __init__(self, email: str):
        """Initialize the DOI fetcher with a contact email (required by some APIs).

        Args:
            email (str): Contact email for API access (required)

        """
        if not email:
            raise ValueError("Email is required for DOIFetcher")
        self.email = email
        self.headers = {
            "User-Agent": f"DOIFetcher/1.0 (mailto:{self.email})",
            "Accept": "application/json",
        }

    def clean_text(self, text: str) -> str:
        """Clean extracted text by removing extra whitespace and normalized characters.

        Args:
            text:

        Returns:
            str: The cleaned text

        """
        # Remove extra whitespace
        text = re.sub(r"\s+", " ", text)
        # Remove non-printable characters
        text = "".join(char for char in text if char.isprintable())
        return text.strip()

    def get_metadata(self, doi: str, strict=False) -> dict[str, Any] | None:
        """Fetch metadata for a DOI using the Crossref API.

        Args:
            doi (str): The DOI to look up
            strict (bool): Raise exceptions if API call fails

        Returns:
            Optional[Dict[str, Any]]: Metadata dictionary if successful, None otherwise

        """
        base_url = "https://api.crossref.org/works/"
        try:
            response = requests.get(f"{base_url}{doi}", headers=self.headers)
            response.raise_for_status()
            return response.json()["message"]
        except Exception as e:
            if strict:
                raise e
            print(f"Warning: Error fetching metadata: {e}")
            return None

    def get_unpaywall_info(self, doi: str, strict=False) -> dict[str, Any] | None:
        """Check Unpaywall for open access versions.

        Example:
            >>> fetcher = DOIFetcher()
            >>> doi = "10.1038/nature12373"
            >>> unpaywall_data = fetcher.get_unpaywall_info(doi)
            >>> assert unpaywall_data["doi"] == doi
            >>> unpaywall_data["best_oa_location"]["url_for_pdf"]
            'https://europepmc.org/articles/pmc4221854?pdf=render'

        Args:
            doi (str): The DOI to look up
            strict (bool): Raise exceptions if API call fails

        Returns:
            Optional[Dict[str, Any]]: Unpaywall data if successful, None otherwise

        """
        base_url = f"https://api.unpaywall.org/v2/{doi}"
        try:
            response = requests.get(f"{base_url}?email={self.email}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            if strict:
                raise e
            print(f"Warning: Error fetching Unpaywall data: {e}")
            return None

    def get_full_text(self, doi: str, fallback_to_abstract=True) -> str | None:
        """Get the full text of a paper using various methods.

        Example:
            >>> fetcher = DOIFetcher()
            >>> doi = "10.1128/msystems.00045-18"
            >>> full_text = fetcher.get_full_text(doi)
            >>> assert "Populus Microbiome" in full_text

        Args:
            doi:
            fallback_to_abstract:

        Returns:
            str: The full text if available, else abstract text if fallback_to_abstract,
              else None

        """
        info = self.get_full_text_info(doi)
        if not info:
            return None
        text = info.text
        if text:
            return self.clean_text(text)
        if info.pdf_url:
            text = self.text_from_pdf_url(info.pdf_url)
            if text:
                return self.clean_text(text)
        message = "FULL TEXT NOT AVAILABLE"
        if fallback_to_abstract:
            metadata = info.metadata or {}
            abstract = metadata.get("abstract")
            if abstract:
                return self.clean_text(abstract) + f"\n\n{message}"
        return message

    def get_full_text_info(self, doi: str) -> FullTextInfo | None:
        """Attempt to get the full text of a paper using various methods.

            >>> fetcher = DOIFetcher()
            >>> doi = "10.1128/msystems.00045-18"
            >>> info = fetcher.get_full_text_info(doi)
            >>> metadata = info.metadata
            >>> metadata["type"]
            'journal-article'
            >>> metadata["title"][0][0:20]
            'Exploration of the B'
            >>> assert info.pdf_url is not None
            >>> info.pdf_url
            'https://europepmc.org/articles/pmc6172771?pdf=render'

        Args:
            doi (str): The DOI to fetch

        Returns:
            FullTextInfo: Full text information

        """
        # Get metadata
        metadata = self.get_metadata(doi)

        # Check Unpaywall
        unpaywall_data = self.get_unpaywall_info(doi)
        if unpaywall_data and unpaywall_data.get("is_oa"):
            locations = unpaywall_data.get("oa_locations", [])
            if unpaywall_data.get("best_oa_location"):
                best_oa_location = unpaywall_data.get("best_oa_location")
                locations = [best_oa_location] + locations

            # Find best open access location
            for location in locations:
                pdf_url = location.get("url_for_pdf")
                if pdf_url:
                    return FullTextInfo(
                        abstract=None,
                        text=None,
                        pdf_url=pdf_url,
                        source="unpaywall",
                        metadata=metadata,
                    )

        # No fallback URL prefixes - rely on Unpaywall and metadata only

        # Return basic info even if no full text found
        return (
            FullTextInfo(
                abstract=None,
                text=None,
                source=None,
                pdf_url=None,
                metadata=metadata,
            )
            if metadata
            else None
        )

    def text_from_pdf_url(self, pdf_url: str, raise_for_status=False) -> str | None:
        """Extract text from a PDF URL.

        Example:
            >>> fetcher = DOIFetcher()
            >>> pdf_url = "https://ceur-ws.org/Vol-1747/IT201_ICBO2016.pdf"
            >>> text = fetcher.text_from_pdf_url(pdf_url)
            >>> assert "biosphere" in text

        Args:
            pdf_url:
            raise_for_status:

        Returns:

        """
        # Download the PDF
        response = requests.get(pdf_url)
        if raise_for_status:
            response.raise_for_status()
        if response.status_code != 200:
            return None

        # Use pdfminer to extract text instead of markitdown
        import tempfile

        from pdfminer.high_level import extract_text

        temp_pdf_path = None
        text_results = None

        try:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_pdf:
                temp_pdf.write(response.content)
                temp_pdf.flush()
                temp_pdf_path = temp_pdf.name
                text = extract_text(temp_pdf_path)
                text_results = text.strip() if text else None
        except Exception as e:
            print(f"Error extracting PDF text: {e} from {temp_pdf_path}")
            return None
        finally:
            if temp_pdf_path and os.path.exists(temp_pdf_path):
                os.remove(temp_pdf_path)

        return text_results
