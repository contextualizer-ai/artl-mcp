"""Tests for PDF download functions.

This module tests the new PDF download capabilities that save PDFs directly
without text extraction or content streaming to the LLM.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import requests

from artl_mcp.tools import download_pdf_from_doi, download_pdf_from_url


class TestDownloadPdfFromUrl:
    """Test direct PDF download from URL functionality."""

    @patch("artl_mcp.tools.file_manager.stream_download_to_file")
    def test_download_pdf_from_url_success(self, mock_stream_download):
        """Test successful PDF download from URL."""
        mock_stream_download.return_value = (Path("/test/path/test.pdf"), 1024)

        result = download_pdf_from_url(
            "https://example.com/test.pdf", filename="test_paper.pdf"
        )

        assert result["success"] is True
        assert result["saved_to"] == "/test/path/test.pdf"
        assert result["file_size_bytes"] == 1024
        assert result["url"] == "https://example.com/test.pdf"
        assert "content" not in result  # Key feature: no content streaming

    @patch("artl_mcp.tools.file_manager.stream_download_to_file")
    def test_download_pdf_from_url_with_save_to(self, mock_stream_download):
        """Test PDF download with specific save path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            save_path = Path(temp_dir) / "custom.pdf"
            mock_stream_download.return_value = (save_path, 2048)

            result = download_pdf_from_url(
                "https://example.com/paper.pdf", save_to=str(save_path)
            )

            assert result["success"] is True
            assert result["saved_to"] == str(save_path)
            assert result["file_size_bytes"] == 2048

    @patch("artl_mcp.tools.file_manager.stream_download_to_file")
    def test_download_pdf_auto_filename_generation(self, mock_stream_download):
        """Test automatic filename generation from URL."""
        mock_stream_download.return_value = (Path("/test/paper.pdf"), 512)

        download_pdf_from_url("https://example.com/research/paper.pdf")

        # Should have called stream_download with extracted filename
        mock_stream_download.assert_called_once()
        call_args = mock_stream_download.call_args
        assert call_args[1]["filename"] == "paper.pdf"

    @patch("artl_mcp.tools.file_manager.stream_download_to_file")
    def test_download_pdf_fallback_filename(self, mock_stream_download):
        """Test fallback filename generation for URLs without .pdf."""
        mock_stream_download.return_value = (Path("/test/downloaded.pdf"), 256)

        download_pdf_from_url("https://example.com/article/view/123")

        # Should generate a timestamped filename
        mock_stream_download.assert_called_once()
        call_args = mock_stream_download.call_args
        filename = call_args[1]["filename"]
        assert filename.startswith("downloaded_pdf_")
        assert filename.endswith(".pdf")

    @patch("artl_mcp.tools.file_manager.stream_download_to_file")
    def test_download_pdf_adds_extension(self, mock_stream_download):
        """Test that .pdf extension is added when missing."""
        mock_stream_download.return_value = (Path("/test/paper.pdf"), 1024)

        download_pdf_from_url(
            "https://example.com/test.pdf", filename="paper_without_extension"
        )

        # Should have added .pdf extension
        mock_stream_download.assert_called_once()
        call_args = mock_stream_download.call_args
        assert call_args[1]["filename"] == "paper_without_extension.pdf"

    @patch("artl_mcp.tools.file_manager.stream_download_to_file")
    def test_download_pdf_request_error(self, mock_stream_download):
        """Test handling of request errors."""
        mock_stream_download.side_effect = requests.exceptions.RequestException(
            "Connection failed"
        )

        result = download_pdf_from_url("https://example.com/test.pdf")

        assert result["success"] is False
        assert result["saved_to"] is None
        assert result["file_size_bytes"] == 0
        assert "Connection failed" in result["error"]

    @patch("artl_mcp.tools.file_manager.stream_download_to_file")
    def test_download_pdf_unexpected_error(self, mock_stream_download):
        """Test handling of unexpected errors."""
        mock_stream_download.side_effect = ValueError("Unexpected error")

        result = download_pdf_from_url("https://example.com/test.pdf")

        assert result["success"] is False
        assert result["saved_to"] is None
        assert result["file_size_bytes"] == 0
        assert "Unexpected error" in result["error"]

    def test_download_pdf_return_structure(self):
        """Test that returned data structure is correct."""
        with patch(
            "artl_mcp.tools.file_manager.stream_download_to_file"
        ) as mock_stream:
            mock_stream.return_value = (Path("/test.pdf"), 1024)

            result = download_pdf_from_url("https://example.com/test.pdf")

            # Verify required keys are present
            required_keys = {"success", "saved_to", "file_size_bytes", "url"}
            assert all(key in result for key in required_keys)

            # Verify content is NOT included (key feature)
            assert "content" not in result


class TestDownloadPdfFromDoi:
    """Test PDF download from DOI via Unpaywall functionality."""

    @patch("artl_mcp.tools.get_unpaywall_info")
    @patch("artl_mcp.tools.download_pdf_from_url")
    def test_download_pdf_from_doi_success(self, mock_download_url, mock_unpaywall):
        """Test successful PDF download from DOI."""
        # Mock Unpaywall response with PDF URL
        mock_unpaywall.return_value = {
            "best_oa_location": {"url_for_pdf": "https://example.com/open_access.pdf"}
        }

        # Mock URL download success
        mock_download_url.return_value = {
            "success": True,
            "saved_to": "/test/unpaywall_pdf_10_1234_test.pdf",
            "file_size_bytes": 2048,
            "url": "https://example.com/open_access.pdf",
        }

        result = download_pdf_from_doi(
            "10.1234/test", "markampa@upenn.edu", filename="test_paper.pdf"
        )

        assert result["success"] is True
        assert result["saved_to"] == "/test/unpaywall_pdf_10_1234_test.pdf"
        assert result["file_size_bytes"] == 2048
        assert result["pdf_url"] == "https://example.com/open_access.pdf"
        assert result["doi"] == "10.1234/test"
        assert "content" not in result  # Key feature: no content streaming

    @patch("artl_mcp.tools.get_unpaywall_info")
    def test_download_pdf_from_doi_no_unpaywall_info(self, mock_unpaywall):
        """Test handling when Unpaywall returns no data."""
        mock_unpaywall.return_value = None

        result = download_pdf_from_doi("10.1234/test", "markampa@upenn.edu")

        assert result["success"] is False
        assert result["saved_to"] is None
        assert result["pdf_url"] is None
        assert "Could not retrieve Unpaywall information" in result["error"]

    @patch("artl_mcp.tools.get_unpaywall_info")
    def test_download_pdf_from_doi_no_open_access(self, mock_unpaywall):
        """Test handling when no open access PDF is available."""
        # Mock Unpaywall response without PDF URL
        mock_unpaywall.return_value = {"best_oa_location": None, "oa_locations": []}

        result = download_pdf_from_doi("10.1234/test", "markampa@upenn.edu")

        assert result["success"] is False
        assert result["saved_to"] is None
        assert result["pdf_url"] is None
        assert "No open access PDF found" in result["error"]

    @patch("artl_mcp.tools.get_unpaywall_info")
    @patch("artl_mcp.tools.download_pdf_from_url")
    def test_download_pdf_from_doi_fallback_oa_locations(
        self, mock_download_url, mock_unpaywall
    ):
        """Test fallback to oa_locations when best_oa_location has no PDF."""
        # Mock Unpaywall response with PDF in oa_locations
        mock_unpaywall.return_value = {
            "best_oa_location": {"url_for_pdf": None},
            "oa_locations": [
                {"url_for_pdf": None},
                {"url_for_pdf": "https://example.com/fallback.pdf"},
            ],
        }

        mock_download_url.return_value = {
            "success": True,
            "saved_to": "/test/paper.pdf",
            "file_size_bytes": 1024,
            "url": "https://example.com/fallback.pdf",
        }

        result = download_pdf_from_doi("10.1234/test", "markampa@upenn.edu")

        assert result["success"] is True
        assert result["pdf_url"] == "https://example.com/fallback.pdf"

    @patch("artl_mcp.tools.get_unpaywall_info")
    @patch("artl_mcp.tools.download_pdf_from_url")
    def test_download_pdf_auto_filename_from_doi(
        self, mock_download_url, mock_unpaywall
    ):
        """Test automatic filename generation from DOI."""
        mock_unpaywall.return_value = {
            "best_oa_location": {"url_for_pdf": "https://example.com/test.pdf"}
        }

        mock_download_url.return_value = {
            "success": True,
            "saved_to": "/test/unpaywall_pdf_10_1234_test.pdf",
            "file_size_bytes": 1024,
            "url": "https://example.com/test.pdf",
        }

        download_pdf_from_doi("10.1234/test", "markampa@upenn.edu")

        # Should have called download_pdf_from_url with auto-generated filename
        mock_download_url.assert_called_once()
        call_args = mock_download_url.call_args
        # Function is called as download_pdf_from_url(pdf_url, save_to, filename)
        assert (
            call_args[0][2] == "unpaywall_pdf_10.1234_test.pdf"
        )  # Third positional argument is filename

    @patch("artl_mcp.tools.get_unpaywall_info")
    @patch("artl_mcp.tools.download_pdf_from_url")
    def test_download_pdf_from_doi_with_save_to(
        self, mock_download_url, mock_unpaywall
    ):
        """Test PDF download with specific save path."""
        mock_unpaywall.return_value = {
            "best_oa_location": {"url_for_pdf": "https://example.com/test.pdf"}
        }

        mock_download_url.return_value = {
            "success": True,
            "saved_to": "/custom/path/paper.pdf",
            "file_size_bytes": 2048,
            "url": "https://example.com/test.pdf",
        }

        download_pdf_from_doi(
            "10.1234/test",
            "markampa@upenn.edu",
            save_to="/custom/path/paper.pdf",
        )

        # Should have passed save_to to download_pdf_from_url
        mock_download_url.assert_called_once()
        call_args = mock_download_url.call_args
        # Function is called as download_pdf_from_url(pdf_url, save_to, filename)
        assert (
            call_args[0][1] == "/custom/path/paper.pdf"
        )  # Second positional argument is save_to

    @patch("artl_mcp.tools.get_unpaywall_info")
    def test_download_pdf_from_doi_unpaywall_error(self, mock_unpaywall):
        """Test handling of Unpaywall API errors."""
        mock_unpaywall.side_effect = Exception("API error")

        result = download_pdf_from_doi("10.1234/test", "markampa@upenn.edu")

        assert result["success"] is False
        assert result["saved_to"] is None
        assert "Unexpected error" in result["error"]

    def test_download_pdf_from_doi_return_structure(self):
        """Test that returned data structure is correct."""
        with patch("artl_mcp.tools.get_unpaywall_info") as mock_unpaywall:
            mock_unpaywall.return_value = None

            result = download_pdf_from_doi("10.1234/test", "markampa@upenn.edu")

            # Verify required keys are present
            required_keys = {"success", "saved_to", "file_size_bytes", "pdf_url", "doi"}
            assert all(key in result for key in required_keys)

            # Verify content is NOT included (key feature)
            assert "content" not in result


class TestPdfDownloadIntegration:
    """Test integration aspects of PDF download functions."""

    def test_email_requirement_documentation(self):
        """Test that download_pdf_from_doi requires email parameter."""
        # This is a documentation test - the function signature should require email
        import inspect

        sig = inspect.signature(download_pdf_from_doi)
        assert "email" in sig.parameters
        assert (
            sig.parameters["email"].default is inspect.Parameter.empty
        )  # Required parameter

    def test_url_download_no_email_requirement(self):
        """Test that download_pdf_from_url does not require email."""
        import inspect

        sig = inspect.signature(download_pdf_from_url)
        assert "email" not in sig.parameters

    @patch("artl_mcp.tools.file_manager.stream_download_to_file")
    def test_memory_efficiency_no_content_in_memory(self, mock_stream_download):
        """Test that PDF downloads don't load content into memory."""
        mock_stream_download.return_value = (Path("/test.pdf"), 1024 * 1024)  # 1MB file

        result = download_pdf_from_url("https://example.com/large.pdf")

        # Should use stream_download_to_file (memory efficient)
        mock_stream_download.assert_called_once()

        # Should not include content in result (no memory usage for LLM)
        assert "content" not in result
        assert result["success"] is True

    def test_docstring_accuracy(self):
        """Test that docstrings accurately describe the functions."""
        # Test download_pdf_from_url docstring
        doc = download_pdf_from_url.__doc__
        assert "without any conversion" in doc.lower()
        assert "no content" in doc.lower()
        assert "avoid streaming" in doc.lower()

        # Test download_pdf_from_doi docstring
        doc = download_pdf_from_doi.__doc__
        assert "unpaywall" in doc.lower()
        assert "without conversion" in doc.lower()
        assert "no text extraction or content streaming" in doc.lower()
        assert "requires an email address" in doc.lower()

    def test_function_type_hints(self):
        """Test that functions have proper type hints."""
        import inspect

        # Test download_pdf_from_url
        sig = inspect.signature(download_pdf_from_url)
        assert sig.return_annotation != inspect.Signature.empty

        # Test download_pdf_from_doi
        sig = inspect.signature(download_pdf_from_doi)
        assert sig.return_annotation != inspect.Signature.empty

    @patch("artl_mcp.tools.get_unpaywall_info")
    @patch("artl_mcp.tools.file_manager.stream_download_to_file")
    def test_real_world_doi_example(self, mock_stream_download, mock_unpaywall):
        """Test with a real-world DOI example."""
        # Use the DOI from the user's example
        doi = "10.1371/journal.pone.0123456"
        email = "markampa@upenn.edu"
        filename = "0123456.pdf"

        # Mock realistic Unpaywall response
        mock_unpaywall.return_value = {
            "best_oa_location": {
                "url_for_pdf": "https://journals.plos.org/plosone/article/file?id=10.1371/journal.pone.0123456&type=printable"
            }
        }

        # Mock successful download
        mock_stream_download.return_value = (
            Path("/Users/MAM/Documents/artl-mcp/0123456.pdf"),
            502381,
        )

        result = download_pdf_from_doi(doi, email, filename=filename)

        assert result["success"] is True
        assert result["doi"] == doi
        assert "plos" in result["pdf_url"].lower()
        assert result["file_size_bytes"] == 502381
        assert "0123456.pdf" in result["saved_to"]


class TestErrorHandlingAndEdgeCases:
    """Test error handling and edge cases for PDF download functions."""

    @patch("artl_mcp.tools.file_manager.stream_download_to_file")
    def test_empty_url(self, mock_stream_download):
        """Test handling of empty URL."""
        mock_stream_download.side_effect = ValueError("Invalid URL")

        result = download_pdf_from_url("")

        assert result["success"] is False
        assert "error" in result

    @patch("artl_mcp.tools.get_unpaywall_info")
    def test_empty_doi(self, mock_unpaywall):
        """Test handling of empty DOI."""
        mock_unpaywall.side_effect = Exception("Invalid DOI")

        result = download_pdf_from_doi("", "test@example.com")

        assert result["success"] is False
        assert "error" in result

    @patch("artl_mcp.tools.file_manager.stream_download_to_file")
    def test_special_characters_in_filename(self, mock_stream_download):
        """Test handling of special characters in filename."""
        mock_stream_download.return_value = (Path("/test/file.pdf"), 1024)

        result = download_pdf_from_url(
            "https://example.com/test.pdf", filename="paper with spaces & symbols!.pdf"
        )

        # Should handle special characters gracefully
        assert result["success"] is True

    @patch("artl_mcp.tools.file_manager.stream_download_to_file")
    def test_very_long_filename(self, mock_stream_download):
        """Test handling of very long filename."""
        mock_stream_download.return_value = (Path("/test/file.pdf"), 1024)

        long_filename = "a" * 300 + ".pdf"  # Very long filename

        result = download_pdf_from_url(
            "https://example.com/test.pdf", filename=long_filename
        )

        # Should handle long filename gracefully (file_manager should truncate)
        assert result["success"] is True

    @patch("artl_mcp.tools.get_unpaywall_info")
    @patch("artl_mcp.tools.download_pdf_from_url")
    def test_malformed_unpaywall_response(self, mock_download_url, mock_unpaywall):
        """Test handling of malformed Unpaywall response."""
        # Mock malformed response (missing expected keys)
        mock_unpaywall.return_value = {"unexpected": "data"}

        result = download_pdf_from_doi("10.1234/test", "markampa@upenn.edu")

        assert result["success"] is False
        assert "No open access PDF found" in result["error"]
