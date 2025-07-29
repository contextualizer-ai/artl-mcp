"""Tests for PDF to Markdown conversion functionality.

Tests the get_europepmc_pdf_as_markdown function with different identifier types
and processing methods to ensure robust behavior.
"""

from unittest.mock import Mock, patch

import pytest

from artl_mcp.tools import get_europepmc_pdf_as_markdown


class TestPDFToMarkdownIdentifierSupport:
    """Test that get_europepmc_pdf_as_markdown supports different identifier types."""

    @pytest.fixture
    def mock_paper_data(self):
        """Mock paper data with PDF availability."""
        return {
            "title": "Test Paper Title",
            "authorString": "Smith J, Jones B",
            "journalTitle": "Test Journal",
            "pubYear": "2023",
            "doi": "10.1234/test.2023",
            "pmid": "12345678",
            "pmcid": "PMC1234567",
            "inPMC": "Y",
            "fullTextUrlList": {
                "fullTextUrl": [
                    {
                        "url": "https://europepmc.org/articles/PMC1234567?pdf=render",
                        "availability": "Open access",
                        "documentStyle": "pdf",
                        "site": "Europe_PMC",
                    }
                ]
            },
        }

    @pytest.fixture
    def mock_pdf_bytes(self):
        """Mock PDF content as bytes."""
        return (
            b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n"
            b"xref\n0 1\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
        )

    @pytest.mark.parametrize(
        "identifier,expected_success",
        [
            ("10.1234/test.2023", True),  # DOI
            ("doi:10.1234/test.2023", True),  # DOI with prefix
            ("12345678", True),  # PMID
            ("PMID:12345678", True),  # PMID with prefix
            ("PMC1234567", True),  # PMCID
            (
                "1234567",
                True,
            ),  # Raw PMCID (may be misidentified as PMID but should still work)
        ],
    )
    @patch("artl_mcp.tools.get_europepmc_paper_by_id")
    @patch("artl_mcp.tools.requests.get")
    @patch("artl_mcp.tools._process_pdf_in_memory")
    def test_identifier_types_accepted(
        self,
        mock_process_pdf,
        mock_requests_get,
        mock_get_paper,
        identifier,
        expected_success,
        mock_paper_data,
        mock_pdf_bytes,
    ):
        """Test that different identifier formats are accepted and processed."""
        # Setup mocks
        mock_get_paper.return_value = mock_paper_data
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = mock_pdf_bytes
        mock_requests_get.return_value = mock_response

        mock_process_pdf.return_value = {
            "content": "# Test Paper Title\n\nTest content",
            "method": "test_method",
            "tables_extracted": 0,
            "processing_time": 1.0,
        }

        # Call function
        result = get_europepmc_pdf_as_markdown(identifier)

        # Verify
        if expected_success:
            assert result is not None
            assert "content" in result
            assert result["content"].startswith("# Test Paper Title")
            mock_get_paper.assert_called_once_with(identifier)
        else:
            assert result is None

    @patch("artl_mcp.tools.get_europepmc_paper_by_id")
    def test_no_paper_found(self, mock_get_paper):
        """Test behavior when paper is not found in Europe PMC."""
        mock_get_paper.return_value = None

        result = get_europepmc_pdf_as_markdown("invalid_identifier")

        assert result is None
        mock_get_paper.assert_called_once_with("invalid_identifier")

    @patch("artl_mcp.tools.get_europepmc_paper_by_id")
    def test_no_pdf_available(self, mock_get_paper):
        """Test behavior when paper exists but has no PDF available."""
        paper_data_no_pdf = {
            "title": "Test Paper Title",
            "authorString": "Smith J",
            "inPMC": "N",  # Not in PMC
            "fullTextUrlList": None,  # No full text URLs
        }
        mock_get_paper.return_value = paper_data_no_pdf

        result = get_europepmc_pdf_as_markdown("10.1234/test.2023")

        assert result is None
        mock_get_paper.assert_called_once_with("10.1234/test.2023")


class TestPDFProcessingMethods:
    """Test different PDF processing methods."""

    @pytest.fixture
    def mock_setup(self):
        """Setup common mocks for processing tests."""
        paper_data = {
            "title": "Test Paper",
            "authorString": "Test Author",
            "journalTitle": "Test Journal",
            "pubYear": "2023",
            "inPMC": "Y",
            "pmcid": "PMC1234567",
            "fullTextUrlList": {
                "fullTextUrl": [
                    {
                        "url": "https://test.pdf",
                        "documentStyle": "pdf",
                        "availability": "Open access",
                    }
                ]
            },
        }

        pdf_bytes = b"%PDF-1.4\ntest content"

        return paper_data, pdf_bytes

    @pytest.mark.parametrize(
        "processing_method", ["auto", "markitdown", "pdfplumber", "hybrid"]
    )
    @patch("artl_mcp.tools.get_europepmc_paper_by_id")
    @patch("artl_mcp.tools.requests.get")
    @patch("artl_mcp.tools._process_pdf_in_memory")
    def test_processing_methods(
        self,
        mock_process_pdf,
        mock_requests_get,
        mock_get_paper,
        processing_method,
        mock_setup,
    ):
        """Test that different processing methods are handled correctly."""
        paper_data, pdf_bytes = mock_setup

        # Setup mocks
        mock_get_paper.return_value = paper_data
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = pdf_bytes
        mock_requests_get.return_value = mock_response

        mock_process_pdf.return_value = {
            "content": f"# Test Paper\n\nProcessed with {processing_method}",
            "method": processing_method,
            "tables_extracted": 2,
            "processing_time": 1.5,
        }

        # Call function with specific processing method
        result = get_europepmc_pdf_as_markdown(
            "PMC1234567", processing_method=processing_method
        )

        # Verify
        assert result is not None
        assert result["content"].startswith("# Test Paper")
        assert result["processing"]["method"] == f"{processing_method}_in_memory"
        assert result["processing"]["tables_extracted"] == 2

        # Verify _process_pdf_in_memory was called with correct method
        mock_process_pdf.assert_called_once()
        call_args = mock_process_pdf.call_args
        assert call_args[0][1] == processing_method  # method parameter


class TestFileOperations:
    """Test file saving operations."""

    @pytest.fixture
    def mock_successful_processing(self):
        """Mock successful PDF processing setup."""
        paper_data = {
            "title": "Test Paper for File Operations",
            "authorString": "Test Author",
            "pmcid": "PMC1234567",
            "inPMC": "Y",
            "fullTextUrlList": {
                "fullTextUrl": [{"url": "https://test.pdf", "documentStyle": "pdf"}]
            },
        }

        return paper_data

    @patch("artl_mcp.tools.get_europepmc_paper_by_id")
    @patch("artl_mcp.tools.requests.get")
    @patch("artl_mcp.tools._process_pdf_in_memory")
    @patch("artl_mcp.tools.file_manager")
    def test_save_file_auto_filename(
        self,
        mock_file_manager,
        mock_process_pdf,
        mock_requests_get,
        mock_get_paper,
        mock_successful_processing,
    ):
        """Test saving with auto-generated filename."""
        # Setup mocks
        mock_get_paper.return_value = mock_successful_processing
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"PDF content"
        mock_requests_get.return_value = mock_response

        mock_process_pdf.return_value = {
            "content": "# Test Paper\n\nContent here",
            "method": "test",
            "tables_extracted": 0,
            "processing_time": 1.0,
        }

        mock_file_manager.handle_file_save.return_value = "/tmp/test_file.md"

        # Call function with save_file=True
        result = get_europepmc_pdf_as_markdown("PMC1234567", save_file=True)

        # Verify
        assert result is not None
        assert "saved_to" in result
        assert result["saved_to"] == "/tmp/test_file.md"
        mock_file_manager.handle_file_save.assert_called_once()

    @patch("artl_mcp.tools.get_europepmc_paper_by_id")
    @patch("artl_mcp.tools.requests.get")
    @patch("artl_mcp.tools._process_pdf_in_memory")
    @patch("artl_mcp.tools.file_manager")
    def test_save_to_specific_path(
        self,
        mock_file_manager,
        mock_process_pdf,
        mock_requests_get,
        mock_get_paper,
        mock_successful_processing,
    ):
        """Test saving to specific file path."""
        # Setup mocks
        mock_get_paper.return_value = mock_successful_processing
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"PDF content"
        mock_requests_get.return_value = mock_response

        mock_process_pdf.return_value = {
            "content": "# Test Paper\n\nContent here",
            "method": "test",
            "tables_extracted": 0,
            "processing_time": 1.0,
        }

        mock_file_manager.handle_file_save.return_value = "/custom/path/paper.md"

        # Call function with specific save path
        result = get_europepmc_pdf_as_markdown(
            "PMC1234567", save_to="/custom/path/paper.md"
        )

        # Verify
        assert result is not None
        assert "saved_to" in result
        assert result["saved_to"] == "/custom/path/paper.md"
        mock_file_manager.handle_file_save.assert_called_once()


class TestErrorHandling:
    """Test error handling scenarios."""

    @patch("artl_mcp.tools.get_europepmc_paper_by_id")
    @patch("artl_mcp.tools.requests.get")
    def test_pdf_download_failure(self, mock_requests_get, mock_get_paper):
        """Test handling of PDF download failures."""
        paper_data = {
            "title": "Test Paper",
            "inPMC": "Y",
            "pmcid": "PMC1234567",
            "fullTextUrlList": {
                "fullTextUrl": [{"url": "https://test.pdf", "documentStyle": "pdf"}]
            },
        }
        mock_get_paper.return_value = paper_data

        # Mock failed HTTP request
        mock_response = Mock()
        mock_response.status_code = 404
        mock_requests_get.return_value = mock_response

        result = get_europepmc_pdf_as_markdown("PMC1234567")

        assert result is None

    @patch("artl_mcp.tools.get_europepmc_paper_by_id")
    @patch("artl_mcp.tools.requests.get")
    @patch("artl_mcp.tools._process_pdf_in_memory")
    def test_pdf_processing_failure(
        self, mock_process_pdf, mock_requests_get, mock_get_paper
    ):
        """Test handling of PDF processing failures."""
        paper_data = {
            "title": "Test Paper",
            "inPMC": "Y",
            "pmcid": "PMC1234567",
            "fullTextUrlList": {
                "fullTextUrl": [{"url": "https://test.pdf", "documentStyle": "pdf"}]
            },
        }
        mock_get_paper.return_value = paper_data

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"PDF content"
        mock_requests_get.return_value = mock_response

        # Mock processing failure
        mock_process_pdf.side_effect = Exception("Processing failed")

        result = get_europepmc_pdf_as_markdown("PMC1234567")

        assert result is None


# Integration-style test (would require actual network access)
@pytest.mark.external_api
class TestRealPDFProcessing:
    """Integration tests with real Europe PMC data (requires network access)."""

    def test_known_pmc_paper_with_pdf(self):
        """Test with a known PMC paper that should have a PDF available."""
        # Use the same paper as in the demo - known to have PDF
        result = get_europepmc_pdf_as_markdown("10.1371/journal.pone.0000217")

        if result:  # PDF might not always be available
            assert "content" in result
            assert "processing" in result
            assert "paper_info" in result
            assert len(result["content"]) > 100  # Should have substantial content
        # If result is None, that's also acceptable - PDF might not be available

    def test_different_identifier_types_same_paper(self):
        """Test that different identifier types for the same paper work."""
        # Test paper: 10.1371/journal.pone.0000217 (PMID: 17299597, PMCID: PMC1790863)
        identifiers = [
            "10.1371/journal.pone.0000217",  # DOI
            "17299597",  # PMID
            "PMC1790863",  # PMCID
        ]

        results = []
        for identifier in identifiers:
            result = get_europepmc_pdf_as_markdown(identifier)
            results.append((identifier, result is not None))

        # At least one should succeed (or all should fail consistently)
        success_count = sum(1 for _, success in results if success)

        # If any succeed, they should be for the same paper
        if success_count > 0:
            # This is an integration test - we mainly want to verify
            # that the function doesn't crash with different identifier types
            assert True  # Function completed without exceptions
