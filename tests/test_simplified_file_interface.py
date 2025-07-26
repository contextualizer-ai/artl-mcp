"""Test the simplified file saving interface."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from artl_mcp.utils.file_manager import file_manager


class TestSimplifiedFileInterface:
    """Test the new simplified file saving interface."""

    def test_handle_file_save_no_saving(self):
        """Test that no file is saved when neither save_file nor save_to is set."""
        result = file_manager.handle_file_save(
            content="test content",
            base_name="test",
            identifier="123",
            file_format="txt",
            save_file=False,
            save_to=None,
        )
        assert result is None

    def test_handle_file_save_to_temp_dir(self):
        """Test saving to temp directory with auto-generated filename."""
        test_content = {"test": "data"}

        result = file_manager.handle_file_save(
            content=test_content,
            base_name="metadata",
            identifier="10.1234/test",
            file_format="json",
            save_file=True,
            save_to=None,
            use_temp_dir=True,
        )

        assert result is not None
        assert result.exists()
        assert result.parent == file_manager.temp_dir
        assert "metadata" in result.name
        assert result.suffix == ".json"

        # Verify content
        with open(result) as f:
            saved_data = json.load(f)
        assert saved_data == test_content

        # Cleanup
        result.unlink(missing_ok=True)

    def test_handle_file_save_to_output_dir(self):
        """Test saving to output directory with auto-generated filename."""
        test_content = "test text content"

        result = file_manager.handle_file_save(
            content=test_content,
            base_name="fulltext",
            identifier="pmid12345",
            file_format="txt",
            save_file=True,
            save_to=None,
            use_temp_dir=False,
        )

        assert result is not None
        assert result.exists()
        assert result.parent == file_manager.output_dir
        assert "fulltext" in result.name
        assert result.suffix == ".txt"

        # Verify content
        assert result.read_text() == test_content

        # Cleanup
        result.unlink(missing_ok=True)

    def test_handle_file_save_to_specific_path(self):
        """Test saving to specific path (overrides save_file)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            save_path = Path(temp_dir) / "custom_file.json"
            test_content = {"custom": "content"}

            result = file_manager.handle_file_save(
                content=test_content,
                base_name="test",
                identifier="123",
                file_format="json",
                save_file=False,  # This should be ignored
                save_to=str(save_path),
            )

            assert result == save_path
            assert result.exists()

            # Verify content
            with open(result) as f:
                saved_data = json.load(f)
            assert saved_data == test_content

    def test_handle_file_save_relative_path(self):
        """Test saving with relative path saves to output directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(file_manager, "output_dir", Path(temp_dir)):
                test_content = {"relative": "content"}

                result = file_manager.handle_file_save(
                    content=test_content,
                    base_name="test",
                    identifier="123",
                    file_format="json",
                    save_file=False,
                    save_to="relative_file.json",  # Relative path
                )

                expected_path = Path(temp_dir) / "relative_file.json"
                assert result == expected_path
                assert result.exists()

                # Verify content
                with open(result) as f:
                    saved_data = json.load(f)
                assert saved_data == test_content

    def test_handle_file_save_auto_extension(self):
        """Test saving automatically adds extension when missing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(file_manager, "output_dir", Path(temp_dir)):
                test_content = {"auto_ext": "content"}

                result = file_manager.handle_file_save(
                    content=test_content,
                    base_name="test",
                    identifier="123",
                    file_format="json",
                    save_file=False,
                    save_to="no_extension",  # No extension provided
                )

                expected_path = Path(temp_dir) / "no_extension.json"
                assert result == expected_path
                assert result.exists()

                # Verify content
                with open(result) as f:
                    saved_data = json.load(f)
                assert saved_data == test_content

    def test_handle_file_save_creates_directories(self):
        """Test that directories are created when saving to specific path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            save_path = Path(temp_dir) / "nested" / "dirs" / "file.txt"
            test_content = "nested content"

            result = file_manager.handle_file_save(
                content=test_content,
                base_name="test",
                identifier="123",
                file_format="txt",
                save_file=False,
                save_to=str(save_path),
            )

            assert result == save_path
            assert result.exists()
            assert result.read_text() == test_content

    def test_save_to_overrides_save_file(self):
        """Test that save_to parameter overrides save_file parameter."""
        import uuid

        with tempfile.TemporaryDirectory() as temp_dir:
            # Use unique identifier to avoid conflicts with previous test runs
            unique_id = str(uuid.uuid4())[:8]
            save_path = Path(temp_dir) / f"override_test_{unique_id}.txt"
            test_content = "override test"

            # Clean up any existing files with our unique identifier (safety measure)
            for existing_file in file_manager.temp_dir.glob(f"*{unique_id}*"):
                existing_file.unlink(missing_ok=True)
            for existing_file in file_manager.output_dir.glob(f"*{unique_id}*"):
                existing_file.unlink(missing_ok=True)

            # save_file=True should be ignored when save_to is provided
            result = file_manager.handle_file_save(
                content=test_content,
                base_name=f"override_{unique_id}",
                identifier="123",
                file_format="txt",
                save_file=True,
                save_to=str(save_path),
            )

            # Should save to specific path, not temp/output dir
            assert result == save_path
            assert result.exists()
            assert result.read_text() == test_content

            # Should not have created any files with our unique identifier
            # in temp/output dirs
            temp_files = list(file_manager.temp_dir.glob(f"*{unique_id}*"))
            output_files = list(file_manager.output_dir.glob(f"*{unique_id}*"))

            assert len(temp_files) == 0, f"Unexpected files in temp dir: {temp_files}"
            assert (
                len(output_files) == 0
            ), f"Unexpected files in output dir: {output_files}"


@pytest.mark.integration
class TestMemoryEfficiencyFeatures:
    """Test memory efficiency features for large file handling."""

    def test_stream_download_to_file(self):
        """Test streaming download functionality."""
        from unittest.mock import MagicMock, patch

        # Mock response with chunked content
        mock_response = MagicMock()
        mock_response.iter_content.return_value = [b"chunk1", b"chunk2", b"chunk3"]
        mock_response.raise_for_status.return_value = None

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("requests.get") as mock_get:
                mock_get.return_value.__enter__.return_value = mock_response

                file_path, total_bytes = file_manager.stream_download_to_file(
                    url="https://example.com/test.pdf",
                    filename="test.pdf",
                    file_format="pdf",
                    output_dir=Path(temp_dir),
                )

                assert file_path.exists()
                assert total_bytes == 18  # len("chunk1chunk2chunk3")
                assert file_path.read_bytes() == b"chunk1chunk2chunk3"

    def test_large_content_warning(self):
        """Test that large content generates appropriate warnings and truncation."""
        from unittest.mock import patch

        from artl_mcp.tools import extract_pdf_text

        # Create large content (>100KB)
        large_text = "A" * (150 * 1024)  # 150KB

        with patch("artl_mcp.tools.extract_text_from_pdf") as mock_extract:
            mock_extract.return_value = large_text

            with patch("artl_mcp.tools.logger") as mock_logger:
                result = extract_pdf_text(
                    "https://example.com/large.pdf", save_file=True
                )

                assert result is not None
                assert result["content_length"] == 150 * 1024
                assert result["truncated"] is True
                assert "[CONTENT TRUNCATED" in result["content"]
                assert len(result["content"]) < 150 * 1024  # Should be truncated
                # Should have logged truncation info
                mock_logger.info.assert_called()

    def test_content_size_limits(self):
        """Test content size limits with different thresholds."""
        from unittest.mock import patch

        from artl_mcp.tools import extract_pdf_text

        # Test small content (no truncation)
        small_text = "Small content"
        with patch("artl_mcp.tools.extract_text_from_pdf") as mock_extract:
            mock_extract.return_value = small_text
            result = extract_pdf_text("https://example.com/small.pdf")

            assert result["content"] == small_text
            assert result["truncated"] is False

        # Test large content with custom limit
        large_text = "A" * 2000
        with patch("artl_mcp.tools.extract_text_from_pdf") as mock_extract:
            mock_extract.return_value = large_text
            result = extract_pdf_text(
                "https://example.com/large.pdf", max_content_size=1000
            )

            assert result["content_length"] == 2000
            assert result["truncated"] is True
            assert len(result["content"]) < 2000


class TestComprehensiveFunctionUpdates:
    """Test all file-saving functions for consistent behavior."""

    def test_all_search_functions_return_structured_data(self):
        """Test that all search functions return consistent structured data."""
        from unittest.mock import MagicMock, patch

        from artl_mcp.tools import (
            search_papers_by_keyword,
            search_pubmed_for_pmids,
        )

        # Test search_papers_by_keyword
        with patch("artl_mcp.tools.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = {"message": {"items": []}}
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            with tempfile.TemporaryDirectory() as temp_dir:
                save_path = Path(temp_dir) / "search.json"
                result = search_papers_by_keyword("test", save_to=str(save_path))

                assert result is not None
                assert "saved_to" in result
                assert result["saved_to"] == str(save_path)
                assert save_path.exists()

        # Test search_pubmed_for_pmids
        with patch("artl_mcp.tools.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "esearchresult": {"idlist": ["123"], "count": "1"}
            }
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            with tempfile.TemporaryDirectory() as temp_dir:
                save_path = Path(temp_dir) / "pubmed.json"
                result = search_pubmed_for_pmids("test", save_to=str(save_path))

                assert result is not None
                assert "saved_to" in result
                assert result["saved_to"] == str(save_path)
                assert save_path.exists()

    def test_citation_functions_return_structured_data(self):
        """Test that citation functions return consistent structured data."""
        from unittest.mock import patch

        from artl_mcp.tools import (
            get_paper_citations,
            get_paper_references,
        )

        sample_citations = [{"title": "Test Paper", "doi": "10.1234/test"}]

        # Test get_paper_references
        with patch(
            "artl_mcp.utils.citation_utils.CitationUtils.get_references_crossref"
        ) as mock_refs:
            mock_refs.return_value = sample_citations

            with tempfile.TemporaryDirectory() as temp_dir:
                save_path = Path(temp_dir) / "refs.json"
                result = get_paper_references("10.1234/test", save_to=str(save_path))

                assert result is not None
                assert "data" in result
                assert "saved_to" in result
                assert result["data"] == sample_citations
                assert result["saved_to"] == str(save_path)
                assert save_path.exists()

        # Test get_paper_citations
        with patch(
            "artl_mcp.utils.citation_utils.CitationUtils.get_citations_crossref"
        ) as mock_cites:
            mock_cites.return_value = sample_citations

            with tempfile.TemporaryDirectory() as temp_dir:
                save_path = Path(temp_dir) / "cites.json"
                result = get_paper_citations("10.1234/test", save_to=str(save_path))

                assert result is not None
                assert "data" in result
                assert "saved_to" in result
                assert result["data"] == sample_citations
                assert result["saved_to"] == str(save_path)
                assert save_path.exists()

    def test_text_functions_with_content_limits(self):
        """Test that text functions apply content limits consistently."""
        from unittest.mock import patch

        from artl_mcp.tools import get_abstract_from_pubmed_id, get_full_text_from_bioc

        # Test with large content
        large_text = "Large abstract content. " * 5000  # ~125KB

        # Test get_abstract_from_pubmed_id
        with patch(
            "artl_mcp.utils.pubmed_utils.get_abstract_from_pubmed"
        ) as mock_abstract:
            mock_abstract.return_value = large_text

            result = get_abstract_from_pubmed_id("12345")
            assert result is not None
            assert "content" in result
            assert "saved_to" in result
            assert len(result["content"]) < len(large_text)  # Should be truncated

        # Test get_full_text_from_bioc with content limits
        with patch("artl_mcp.utils.pubmed_utils.get_full_text_from_bioc") as mock_bioc:
            mock_bioc.return_value = large_text

            result = get_full_text_from_bioc("12345")
            assert result is not None
            assert "content" in result
            assert "saved_to" in result
            assert "truncated" in result
            assert result["truncated"] is True
            assert len(result["content"]) < len(large_text)

    def test_backward_compatibility_warnings(self):
        """Test that functions still work for basic use cases."""
        from unittest.mock import MagicMock, patch

        from artl_mcp.tools import get_doi_metadata, search_papers_by_keyword

        # Test get_doi_metadata without save parameters (backward compatibility)
        with patch("artl_mcp.tools.requests.get") as mock_get:
            mock_response = MagicMock()
            test_data = {"message": {"title": ["Test Paper"]}}
            mock_response.json.return_value = test_data
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            result = get_doi_metadata("10.1234/test")  # No save parameters
            assert result is not None
            assert "message" in result
            # Should NOT have saved_to key when no saving requested
            assert "saved_to" not in result

        # Test search function without save parameters
        with patch("artl_mcp.tools.requests.get") as mock_get:
            mock_response = MagicMock()
            search_data = {"message": {"items": []}}
            mock_response.json.return_value = search_data
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            result = search_papers_by_keyword("test")  # No save parameters
            assert result is not None
            assert "message" in result
            # Should NOT have saved_to key when no saving requested
            assert "saved_to" not in result


class TestToolsIntegration:
    """Test that tools work with the new interface."""

    @patch("artl_mcp.tools.requests.get")
    def test_get_doi_metadata_no_save(self, mock_get):
        """Test DOI metadata retrieval without saving."""
        from artl_mcp.tools import get_doi_metadata

        # Mock API response
        mock_response = MagicMock()
        mock_response.json.return_value = {"message": {"title": ["Test Paper"]}}
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = get_doi_metadata("10.1234/test")

        assert result is not None
        assert result["message"]["title"] == ["Test Paper"]

    @patch("artl_mcp.tools.requests.get")
    def test_get_doi_metadata_save_to_temp(self, mock_get):
        """Test DOI metadata retrieval with saving to temp directory."""
        from artl_mcp.tools import get_doi_metadata

        # Mock API response
        mock_response = MagicMock()
        test_data = {"message": {"title": ["Test Paper"], "DOI": "10.1234/test"}}
        mock_response.json.return_value = test_data
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = get_doi_metadata("10.1234/test", save_file=True)

        assert result is not None
        # Should now include save path information
        assert "saved_to" in result
        assert result["saved_to"] is not None

        # Original data should still be present
        assert result["message"] == test_data["message"]

        # Check that file was saved to output directory
        saved_file = Path(result["saved_to"])
        assert saved_file.exists()
        assert saved_file.parent == file_manager.output_dir

        # Verify saved content
        with open(saved_file) as f:
            saved_data = json.load(f)
        # Remove saved_to key for comparison since it's added by the tool
        expected_data = {k: v for k, v in result.items() if k != "saved_to"}
        assert saved_data == expected_data

        # Cleanup
        saved_file.unlink(missing_ok=True)

    @patch("artl_mcp.tools.requests.get")
    def test_get_doi_metadata_save_to_path(self, mock_get):
        """Test DOI metadata retrieval with saving to specific path."""
        from artl_mcp.tools import get_doi_metadata

        # Mock API response
        mock_response = MagicMock()
        test_data = {"message": {"title": ["Test Paper"], "DOI": "10.1234/test"}}
        mock_response.json.return_value = test_data
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        with tempfile.TemporaryDirectory() as temp_dir:
            save_path = Path(temp_dir) / "my_paper.json"

            result = get_doi_metadata("10.1234/test", save_to=str(save_path))

            assert result is not None
            # Should include save path information
            assert "saved_to" in result
            assert result["saved_to"] == str(save_path)

            # Original data should still be present
            assert result["message"] == test_data["message"]
            assert save_path.exists()

            # Verify saved content
            with open(save_path) as f:
                saved_data = json.load(f)
            # Remove saved_to key for comparison since it's added by the tool
            expected_data = {k: v for k, v in result.items() if k != "saved_to"}
            assert saved_data == expected_data

    def test_get_doi_text_returns_structured_data(self):
        """Test that get_doi_text returns structured data with save path info."""
        from unittest.mock import patch

        from artl_mcp.tools import get_doi_text

        with patch("artl_mcp.utils.pubmed_utils.get_doi_text") as mock_get_text:
            mock_get_text.return_value = "Sample full text content"

            # Test without saving
            result = get_doi_text("10.1234/test")
            assert result is not None
            assert result["content"] == "Sample full text content"
            assert result["saved_to"] is None

            # Test with saving
            with tempfile.TemporaryDirectory() as temp_dir:
                save_path = Path(temp_dir) / "test_text.txt"

                result = get_doi_text("10.1234/test", save_to=str(save_path))
                assert result is not None
                assert result["content"] == "Sample full text content"
                assert result["saved_to"] == str(save_path)
                assert save_path.exists()
                assert save_path.read_text() == "Sample full text content"

    def test_extract_pdf_text_returns_structured_data(self):
        """Test that extract_pdf_text returns structured data with content info."""
        from unittest.mock import patch

        from artl_mcp.tools import extract_pdf_text

        with patch("artl_mcp.tools.extract_text_from_pdf") as mock_extract:
            sample_text = "Sample PDF text content"
            mock_extract.return_value = sample_text

            # Test without saving
            result = extract_pdf_text("https://example.com/test.pdf")
            assert result is not None
            assert result["content"] == sample_text
            assert result["saved_to"] is None
            assert result["content_length"] == len(sample_text)
            assert result["streamed"] is False

            # Test with saving
            with tempfile.TemporaryDirectory() as temp_dir:
                save_path = Path(temp_dir) / "pdf_text.txt"

                result = extract_pdf_text(
                    "https://example.com/test.pdf", save_to=str(save_path)
                )
                assert result is not None
                assert result["content"] == sample_text
                assert result["saved_to"] == str(save_path)
                assert save_path.exists()
                assert save_path.read_text() == sample_text

    def test_get_citation_network_returns_structured_data(self):
        """Test that get_citation_network returns structured data with save info."""
        from unittest.mock import patch

        from artl_mcp.tools import get_citation_network

        sample_network = {"cited_by_count": 42, "concepts": [{"display_name": "Test"}]}

        with patch(
            "artl_mcp.utils.citation_utils.CitationUtils.get_citation_network_openalex"
        ) as mock_network:
            mock_network.return_value = sample_network

            # Test without saving
            result = get_citation_network("10.1234/test")
            assert result is not None
            assert result["data"] == sample_network
            assert result["saved_to"] is None

            # Test with saving
            with tempfile.TemporaryDirectory() as temp_dir:
                save_path = Path(temp_dir) / "network.json"

                result = get_citation_network("10.1234/test", save_to=str(save_path))
                assert result is not None
                assert result["data"] == sample_network
                assert result["saved_to"] == str(save_path)
                assert save_path.exists()

                with open(save_path) as f:
                    saved_data = json.load(f)
                assert saved_data == sample_network
