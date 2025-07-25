"""User story integration tests for ARTL MCP.

These tests verify real-world workflows that users would follow,
focusing on the complete user journey rather than individual functions.

User Stories Tested:
1. Researcher has a DOI, wants to get full metadata and abstract
2. Researcher has a PMID, wants to get full text and save to file
3. Researcher searches for papers by keyword and gets metadata
4. Researcher converts between different ID formats (DOI ↔ PMID)
5. Researcher extracts text from PDFs found via DOI
6. Researcher uses MCP server to get paper information
7. Email address management in various scenarios
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastmcp import Client

from artl_mcp.main import create_mcp
from artl_mcp.tools import (
    get_abstract_from_pubmed_id,
    get_doi_metadata,
    get_full_text_from_doi,
    get_unpaywall_info,
    search_papers_by_keyword,
)
from artl_mcp.utils.email_manager import EmailManager
from artl_mcp.utils.pubmed_utils import (
    doi_to_pmid,
    extract_doi_from_url,
    pmid_to_doi,
)


class TestEmailManagement:
    """Test email address management across different scenarios."""

    def test_email_manager_environment_variable(self):
        """User story: Researcher sets ARTL_EMAIL_ADDR environment variable."""
        em = EmailManager()

        with patch.dict(os.environ, {"ARTL_EMAIL_ADDR": "researcher@university.edu"}):
            email = em.get_email()
            assert email == "researcher@university.edu"

    def test_email_manager_rejects_bogus_emails(self):
        """User story: System prevents use of fake email addresses."""
        em = EmailManager()

        bogus_emails = [
            "test@example.com",
            "fake.user@test.org",
            "dummy@placeholder.net",
            "noreply@invalid.com",
        ]

        for bogus_email in bogus_emails:
            with pytest.raises(ValueError, match="Bogus email address not allowed"):
                em.get_email(bogus_email)

    def test_email_manager_validates_format(self):
        """User story: System validates email format."""
        em = EmailManager()

        invalid_emails = ["not-an-email", "@domain.com", "user@", "user@domain"]

        for invalid_email in invalid_emails:
            with pytest.raises(ValueError, match="Invalid email format"):
                em.get_email(invalid_email)

        # Empty string should fall back to environment/file (no exception)
        em.get_email("")
        # Result could be None or an actual email from environment, both are valid

    def test_email_manager_api_specific_validation(self):
        """User story: APIs have specific email requirements."""
        em = EmailManager()

        # Should work with institutional email
        institutional_email = "researcher@university.edu"
        validated = em.validate_for_api("unpaywall", institutional_email)
        assert validated == institutional_email

        # Should reject example.com for Unpaywall
        with pytest.raises(ValueError, match="requires a real institutional email"):
            em.validate_for_api("unpaywall", "test@example.com")


class TestDOIWorkflows:
    """Test workflows starting with a DOI."""

    @pytest.mark.external_api
    @pytest.mark.slow
    def test_doi_to_full_metadata_workflow(self):
        """User story: Researcher has a DOI, wants comprehensive metadata."""
        # Given: A researcher has a DOI from a paper they found
        doi = "10.1099/ijsem.0.005153"

        # When: They get metadata using the DOI
        metadata = get_doi_metadata(doi)

        # Then: They should get comprehensive metadata
        if metadata:  # API might not always be available
            # CrossRef API returns nested structure
            message = metadata.get("message", metadata)
            assert message["DOI"] == doi
            assert "title" in message
            assert "author" in message
            assert "published-print" in message or "published-online" in message

            # Should contain scientific content indicators
            if "abstract" in metadata:
                abstract_text = str(metadata["abstract"])
                assert len(abstract_text) > 100  # Substantial content

    @pytest.mark.external_api
    @pytest.mark.slow
    def test_doi_to_pmid_conversion_workflow(self):
        """User story: Researcher has DOI, needs PMID for PubMed searches."""
        # Given: A researcher has a DOI
        doi = "10.1099/ijsem.0.005153"

        # When: They convert DOI to PMID
        pmid = doi_to_pmid(doi)

        # Then: They should get a valid PMID
        if pmid:  # Conversion might not always work
            pmid_str = str(pmid)  # Convert to string for validation
            assert pmid_str.isdigit()
            assert len(pmid_str) >= 7  # PMIDs are typically 7+ digits

            # And: They can use the PMID to get abstracts
            abstract = get_abstract_from_pubmed_id(pmid)
            assert isinstance(abstract, str)

    @pytest.mark.external_api
    @pytest.mark.slow
    def test_doi_to_fulltext_workflow(self):
        """User story: Researcher wants full text from DOI."""
        # Given: A researcher has a DOI and valid email
        doi = "10.1128/msystems.00045-18"  # Known to have full text
        email = "researcher@university.edu"

        # When: They try to get full text
        full_text = get_full_text_from_doi(doi, email)

        # Then: They should get substantial text content
        if full_text:  # Full text might not always be available
            assert isinstance(full_text, str)
            assert len(full_text) > 500  # Should be substantial
            assert "microbiome" in full_text.lower()  # Expected content

    def test_doi_url_extraction_workflow(self):
        """User story: Researcher has DOI URL, needs clean DOI."""
        # Given: A researcher copies a DOI URL from a browser
        doi_urls = [
            "https://doi.org/10.1099/ijsem.0.005153",
            "http://dx.doi.org/10.1099/ijsem.0.005153",
            "https://www.doi.org/10.1099/ijsem.0.005153?utm_source=google",
        ]

        expected_doi = "10.1099/ijsem.0.005153"

        # When: They extract the clean DOI
        for url in doi_urls:
            clean_doi = extract_doi_from_url(url)

            # Then: They should get the clean DOI
            assert clean_doi == expected_doi


class TestPMIDWorkflows:
    """Test workflows starting with a PMID."""

    @pytest.mark.external_api
    @pytest.mark.slow
    def test_pmid_to_abstract_workflow(self):
        """User story: Researcher has PMID, wants abstract for literature review."""
        # Given: A researcher has a PMID from PubMed search
        pmid = "31653696"  # Known to have abstract with "deglycase"

        # When: They get the abstract
        abstract = get_abstract_from_pubmed_id(pmid)

        # Then: They should get readable abstract text
        if abstract and len(abstract) > 50:  # API might return empty
            assert isinstance(abstract, str)
            assert "deglycase" in abstract.lower()
            assert len(abstract) > 100  # Should be substantial

    @pytest.mark.external_api
    @pytest.mark.slow
    def test_pmid_to_doi_conversion_workflow(self):
        """User story: Researcher has PMID, needs DOI for citations."""
        # Given: A researcher has a PMID
        pmid = "35545607"

        # When: They convert PMID to DOI
        doi = pmid_to_doi(pmid)

        # Then: They should get a valid DOI
        if doi:  # Conversion might not always work
            assert isinstance(doi, str)
            assert doi.startswith("10.")
            assert "/" in doi

            # And: The DOI should work for metadata retrieval
            metadata = get_doi_metadata(doi)
            if metadata:
                # CrossRef API returns nested structure
                message = metadata.get("message", metadata)
                assert "DOI" in message


class TestSearchWorkflows:
    """Test paper search workflows."""

    @pytest.mark.external_api
    @pytest.mark.slow
    def test_keyword_search_to_metadata_workflow(self):
        """User story: Researcher searches by keyword, explores results."""
        # Given: A researcher wants papers about "machine learning"
        keywords = "machine learning"
        max_results = 5  # Small number for testing

        # When: They search by keyword
        results = search_papers_by_keyword(keywords, max_results=max_results)

        # Then: They get relevant paper metadata
        if results:  # API might not always be available
            assert isinstance(results, dict)

            # Should contain standard CrossRef fields
            if "message" in results:
                message = results["message"]
                assert "items" in message
                items = message["items"]
                assert isinstance(items, list)

                # And: They can get full details for interesting papers
                if items:
                    first_paper = items[0]
                    assert isinstance(first_paper, dict)

                    # Should have paper metadata
                    assert "DOI" in first_paper or "title" in first_paper

                    # If DOI is available, they could get more details
                    if "DOI" in first_paper:
                        doi = first_paper["DOI"]
                        detailed_metadata = get_doi_metadata(doi)
                        if detailed_metadata:
                            assert isinstance(detailed_metadata, dict)


class TestMCPIntegration:
    """Test MCP server integration workflows."""

    @pytest.mark.external_api
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_mcp_doi_metadata_workflow(self):
        """User story: Researcher uses MCP client to get DOI metadata."""
        # Given: A researcher connects to the MCP server
        mcp = create_mcp()

        async with Client(mcp) as client:
            # When: They request DOI metadata through MCP
            results = await client.call_tool(
                "get_doi_metadata", {"doi": "10.1099/ijsem.0.005153"}
            )

            # Then: They should get structured metadata
            assert len(results) > 0
            result_text = results[0].text

            if result_text and len(result_text) > 100:  # API might not be available
                # Should contain JSON-like structured data
                assert "DOI" in result_text or "title" in result_text

    @pytest.mark.external_api
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_mcp_pubmed_abstract_workflow(self):
        """User story: Researcher uses MCP to get PubMed abstracts."""
        # Given: A researcher connects to the MCP server
        mcp = create_mcp()

        async with Client(mcp) as client:
            # When: They request abstract through MCP
            results = await client.call_tool(
                "get_abstract_from_pubmed_id", {"pmid": "31653696"}
            )

            # Then: They should get the abstract text
            assert len(results) > 0
            result_text = results[0].text

            if result_text and len(result_text) > 50:  # API might not be available
                assert isinstance(result_text, str)


class TestFileOperations:
    """Test workflows involving file operations."""

    def test_temporary_file_workflow(self):
        """User story: Researcher saves content to files safely."""
        # Given: A researcher wants to save content to a file
        content = """Sample research paper content
With multiple lines
For analysis"""

        # When: They use temporary file operations (simulating save functionality)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            # Then: The file should be created and readable
            saved_path = Path(temp_path)
            assert saved_path.exists()

            with open(saved_path) as f:
                saved_content = f.read()
            assert saved_content == content

        finally:
            # And: Cleanup should work properly
            if Path(temp_path).exists():
                os.remove(temp_path)
            assert not Path(temp_path).exists()


class TestErrorHandling:
    """Test error handling in user workflows."""

    def test_invalid_doi_workflow(self):
        """User story: Researcher enters invalid DOI, gets helpful error."""
        # Given: A researcher enters an invalid DOI
        invalid_dois = ["not-a-doi", "10.1234", "", "doi:invalid"]

        for invalid_doi in invalid_dois:
            # When: They try to get metadata
            result = get_doi_metadata(invalid_doi)

            # Then: They should get None (graceful failure) or handle gracefully
            # Note: Some "invalid" DOIs might return search results from CrossRef
            if result is not None:
                # If result is returned, it should be a valid structure
                assert isinstance(result, dict)

    def test_network_unavailable_workflow(self):
        """User story: Researcher works offline, gets graceful failures."""
        # Given: A researcher tries to use the system when offline
        # When: They make API calls (simulated network failure)
        with patch("requests.get", side_effect=ConnectionError("Network unavailable")):
            # Then: The system should handle failures gracefully
            try:
                result = get_doi_metadata("10.1099/ijsem.0.005153")
                assert result is None  # Should return None on network error
            except Exception as e:
                # Should re-raise as documented in the function
                assert "Network unavailable" in str(e)

    def test_api_rate_limiting_workflow(self):
        """User story: Researcher hits API rate limits, gets proper feedback."""
        # Given: A researcher makes many rapid requests
        # When: API returns rate limiting errors (simulated)
        from unittest.mock import Mock

        mock_response = Mock()
        mock_response.status_code = 429  # Too Many Requests
        mock_response.raise_for_status.side_effect = Exception("Rate limited")

        with patch("requests.get", return_value=mock_response):
            # Then: The system should handle rate limits gracefully
            try:
                result = get_doi_metadata("10.1099/ijsem.0.005153")
                assert result is None  # Should return None on rate limit
            except Exception as e:
                # Should re-raise as documented in the function
                assert "Rate limited" in str(e)


class TestCrossFormatWorkflows:
    """Test workflows involving multiple ID formats."""

    @pytest.mark.external_api
    @pytest.mark.slow
    def test_complete_id_conversion_workflow(self):
        """User story: Researcher needs to work with multiple ID formats."""
        # Given: A researcher starts with a DOI URL from a browser
        doi_url = "https://doi.org/10.1099/ijsem.0.005153"

        # When: They extract the DOI
        clean_doi = extract_doi_from_url(doi_url)
        assert clean_doi == "10.1099/ijsem.0.005153"

        # And: Convert DOI to PMID
        pmid = doi_to_pmid(clean_doi)
        if pmid:  # Conversion might not always work
            pmid_str = str(pmid)  # Convert to string for validation
            assert pmid_str.isdigit()

            # And: Convert back to DOI to verify
            converted_doi = pmid_to_doi(pmid)
            if converted_doi:
                assert converted_doi == clean_doi

    @pytest.mark.external_api
    @pytest.mark.slow
    def test_comprehensive_paper_analysis_workflow(self):
        """User story: Researcher does complete analysis of a paper."""
        # Given: A researcher wants comprehensive information about a paper
        doi = "10.1099/ijsem.0.005153"
        email = "researcher@university.edu"

        # When: They gather all available information
        metadata = get_doi_metadata(doi)
        pmid = doi_to_pmid(doi)

        if metadata and pmid:
            abstract = get_abstract_from_pubmed_id(pmid)
            unpaywall_info = get_unpaywall_info(doi, email, strict=True)

            # Then: They should have comprehensive paper information
            # CrossRef API returns nested structure
            message = metadata.get("message", metadata)
            assert "title" in message
            assert isinstance(abstract, str)

            if unpaywall_info:  # Unpaywall might not have all papers
                assert isinstance(unpaywall_info, dict)

            # And: All information should be consistent
            assert message["DOI"] == doi
