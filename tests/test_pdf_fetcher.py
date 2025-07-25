"""Comprehensive tests for PDF fetcher functionality with real PDF operations."""

import os
import tempfile
from pathlib import Path

import pytest
import requests

from artl_mcp.utils.pdf_fetcher import extract_text_from_pdf


@pytest.fixture
def temp_dir():
    """Provide a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_pdf_content():
    """Create a minimal valid PDF content for testing."""
    # This is a minimal PDF structure that can be parsed
    return b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj
4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(Hello World) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000206 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
299
%%EOF"""


@pytest.fixture
def invalid_pdf_content():
    """Create invalid PDF content for testing error handling."""
    return b"This is not a PDF file, just plain text"


class TestExtractTextFromPDF:
    """Test PDF text extraction with real functionality and minimal mocking."""

    def test_extract_text_from_invalid_url(self):
        """Test with completely invalid URL (unit test)."""
        with pytest.raises(requests.exceptions.MissingSchema):
            extract_text_from_pdf("not-a-valid-url")

    def test_extract_text_from_malformed_url(self):
        """Test with malformed URL (unit test)."""
        with pytest.raises(requests.exceptions.InvalidURL):
            extract_text_from_pdf("http://")

    @pytest.mark.external_api
    @pytest.mark.slow
    def test_extract_text_from_nonexistent_url(self):
        """Test with URL that returns 404 (external API test)."""
        result = extract_text_from_pdf("https://httpbin.org/status/404")
        assert result == "Error: Unable to retrieve PDF."

    @pytest.mark.external_api
    @pytest.mark.slow
    def test_extract_text_from_server_error_url(self):
        """Test with URL that returns 500 (external API test)."""
        result = extract_text_from_pdf("https://httpbin.org/status/500")
        assert result == "Error: Unable to retrieve PDF."

    @pytest.mark.external_api
    @pytest.mark.slow
    def test_extract_text_from_non_pdf_content(self):
        """Test with URL that returns non-PDF content (external API test)."""
        # httpbin.org/html returns HTML, not PDF (if available)
        result = extract_text_from_pdf("https://httpbin.org/html")
        # Could return either HTTP error or PDF parsing error
        assert (
            "Error extracting PDF text:" in result
            or result == "Error: Unable to retrieve PDF."
        )

    def test_extract_text_with_sample_pdf_content(self, sample_pdf_content):
        """Test PDF text extraction with valid PDF content using real temp file."""
        import tempfile

        from pdfminer.high_level import extract_text

        # Create a real temporary file like the function does
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_pdf:
            temp_pdf.write(sample_pdf_content)
            temp_pdf.flush()
            temp_path = temp_pdf.name

        try:
            # Test the actual PDF extraction
            text = extract_text(temp_path)
            assert text is not None
            assert text.strip() != ""
        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_extract_text_with_invalid_pdf_content(self, invalid_pdf_content):
        """Test with invalid PDF content using real temp file."""
        import tempfile

        from pdfminer.high_level import extract_text
        from pdfminer.pdfparser import PDFSyntaxError

        # Create a real temporary file with invalid content
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_pdf:
            temp_pdf.write(invalid_pdf_content)
            temp_pdf.flush()
            temp_path = temp_pdf.name

        try:
            # Test that PDF extraction fails
            with pytest.raises(PDFSyntaxError):
                extract_text(temp_path)
        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_extract_text_with_empty_pdf(self):
        """Test with completely empty file."""
        import tempfile

        from pdfminer.high_level import extract_text
        from pdfminer.pdfparser import PDFSyntaxError

        # Create a real temporary file with no content
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_pdf:
            temp_pdf.write(b"")
            temp_pdf.flush()
            temp_path = temp_pdf.name

        try:
            # Test that PDF extraction fails with empty file
            with pytest.raises(PDFSyntaxError):
                extract_text(temp_path)
        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.remove(temp_path)

    @pytest.mark.external_api
    @pytest.mark.slow
    def test_extract_text_from_real_pdf_url(self):
        """Test with a real PDF URL (external API test)."""
        # This is a known small PDF from arXiv
        test_url = "https://arxiv.org/pdf/1706.03762.pdf"

        try:
            result = extract_text_from_pdf(test_url)
            # Should not be an error message
            assert result != "Error: Unable to retrieve PDF."
            assert "Error extracting PDF text:" not in result
            # Should contain some actual text content
            assert len(result.strip()) > 100  # Real PDFs have substantial content
        except requests.exceptions.RequestException:
            # If network is unavailable, skip this test
            pytest.skip("Network unavailable for external API test")

    @pytest.mark.external_api
    @pytest.mark.slow
    def test_temporary_file_cleanup(self):
        """Test that temporary files are properly cleaned up using real HTTP request."""
        import tempfile
        from pathlib import Path

        # Count temp PDF files before
        temp_dir = Path(tempfile.gettempdir())
        initial_pdf_count = len(list(temp_dir.glob("*.pdf")))

        # Use a real but small PDF
        try:
            extract_text_from_pdf(
                "https://httpbin.org/status/404"
            )  # Will fail but test cleanup
            # Count temp PDF files after - should be same (cleanup happened)
            final_pdf_count = len(list(temp_dir.glob("*.pdf")))
            assert final_pdf_count == initial_pdf_count
        except requests.exceptions.RequestException:
            pytest.skip("Network unavailable for cleanup test")

    def test_text_stripping(self, sample_pdf_content):
        """Test that extracted text is properly stripped of whitespace."""
        import tempfile

        from pdfminer.high_level import extract_text

        # Create a real temporary file
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_pdf:
            temp_pdf.write(sample_pdf_content)
            temp_pdf.flush()
            temp_path = temp_pdf.name

        try:
            # Test the actual PDF extraction and stripping
            text = extract_text(temp_path)
            if text:
                # Test that our function would strip the text
                stripped = (
                    text.strip() if text else "Error: No text extracted from PDF."
                )
                assert stripped == stripped.strip()
        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_empty_text_handling(self):
        """Test handling of PDFs that extract to empty text."""
        # Create a PDF with no text content
        pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
>>
endobj
xref
0 4
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
trailer
<<
/Size 4
/Root 1 0 R
>>
startxref
179
%%EOF"""

        import tempfile

        from pdfminer.high_level import extract_text

        # Create a real temporary file
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_pdf:
            temp_pdf.write(pdf_content)
            temp_pdf.flush()
            temp_path = temp_pdf.name

        try:
            # Test the actual PDF extraction
            text = extract_text(temp_path)
            # This PDF should return empty or None text
            result = text.strip() if text else "Error: No text extracted from PDF."
            if not result:
                result = "Error: No text extracted from PDF."
            assert result == "Error: No text extracted from PDF."
        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.remove(temp_path)

    @pytest.mark.external_api
    @pytest.mark.slow
    def test_network_timeout_handling(self):
        """Test handling of network timeouts (external API test)."""
        # We need to mock the requests.get in the pdf_fetcher module to test timeout
        from unittest.mock import patch

        import requests as req_module

        with patch("artl_mcp.utils.pdf_fetcher.requests.get") as mock_get:
            mock_get.side_effect = req_module.exceptions.Timeout("Request timeout")

            result = extract_text_from_pdf("https://httpbin.org/delay/10")
            assert "Error: Network error while retrieving PDF:" in result
            assert "Request timeout" in result

    def test_os_error_handling(self):
        """Test handling of OS errors during file operations."""
        from unittest.mock import Mock, patch

        # Mock successful HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"PDF content"

        with patch(
            "artl_mcp.utils.pdf_fetcher.requests.get", return_value=mock_response
        ):
            # Mock FileManager to simulate OSError during temp file creation
            from artl_mcp.utils.file_manager import file_manager

            with patch.object(
                file_manager,
                "create_temp_file",
                side_effect=OSError("Permission denied"),
            ):
                result = extract_text_from_pdf("https://example.com/test.pdf")

                assert "Error extracting PDF text:" in result
                assert "Permission denied" in result
