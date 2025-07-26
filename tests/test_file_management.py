"""
Tests for file management functionality and file saving features.

This module tests:
- File saving functionality in all tools
- Cross-platform file management
- Filename sanitization
- Temp file cleanup
- Environment variable configuration
- Error handling for file operations
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from artl_mcp.tools import (
    extract_pdf_text,
    get_abstract_from_pubmed_id,
    get_doi_metadata,
    get_full_text_from_doi,
    search_papers_by_keyword,
)
from artl_mcp.utils.email_manager import EmailManager
from artl_mcp.utils.file_manager import FileManager, file_manager


def get_test_email():
    """Get a valid test email address from environment/local config."""
    em = EmailManager()
    email = em.get_email()
    if not email:
        pytest.skip(
            "No valid email address found for testing. "
            "Set ARTL_EMAIL_ADDR or add to local/.env"
        )
    return email


class TestFileManager:
    """Test core FileManager functionality."""

    def test_init_with_defaults(self):
        """Test FileManager initialization with default settings."""
        fm = FileManager()

        # Should have default directories set
        assert isinstance(fm.temp_dir, Path)
        assert isinstance(fm.output_dir, Path)
        assert isinstance(fm.keep_temp_files, bool)

        # Default output should be in user's Documents
        assert "artl-mcp" in str(fm.output_dir)

    def test_init_with_env_vars(self):
        """Test FileManager initialization with environment variables."""
        with (
            tempfile.TemporaryDirectory() as temp_output,
            tempfile.TemporaryDirectory() as temp_temp,
        ):
            with patch.dict(
                "os.environ",
                {
                    "ARTL_OUTPUT_DIR": temp_output,
                    "ARTL_TEMP_DIR": temp_temp,
                    "ARTL_KEEP_TEMP_FILES": "true",
                },
            ):
                fm = FileManager()

                assert str(fm.output_dir) == temp_output
                assert str(fm.temp_dir) == temp_temp
                assert fm.keep_temp_files is True

    def test_sanitize_filename_invalid_chars(self):
        """Test filename sanitization removes invalid characters."""
        fm = FileManager()

        # Test invalid characters
        test_cases = [
            ("file<name>test", "file_name_test"),
            ('file"name:test', "file_name_test"),
            ("file/name\\test", "file_name_test"),
            ("file|name?test", "file_name_test"),
            ("file*name test", "file_name test"),
        ]

        for input_name, expected in test_cases:
            result = fm.sanitize_filename(input_name)
            assert result == expected

    def test_sanitize_filename_reserved_names(self):
        """Test filename sanitization handles Windows reserved names."""
        fm = FileManager()

        reserved_names = ["CON", "PRN", "AUX", "NUL", "COM1", "LPT1"]

        for name in reserved_names:
            result = fm.sanitize_filename(name)
            assert result.startswith("_")
            assert name in result

    def test_sanitize_filename_length_limit(self):
        """Test filename sanitization respects length limits."""
        fm = FileManager()

        # Test with extension
        long_name = "a" * 250 + ".txt"
        result = fm.sanitize_filename(long_name, max_length=200)
        assert len(result) <= 200
        assert result.endswith(".txt")

        # Test without extension
        long_name_no_ext = "a" * 250
        result = fm.sanitize_filename(long_name_no_ext, max_length=100)
        assert len(result) <= 100

    def test_generate_filename(self):
        """Test automatic filename generation."""
        fm = FileManager()

        # Basic filename generation
        filename = fm.generate_filename("metadata", "10.1038/nature12373", "json")

        assert filename.startswith("metadata_")
        assert "10.1038_nature12373" in filename
        assert filename.endswith(".json")
        assert "_" in filename  # Should have timestamp

    def test_save_content_json(self):
        """Test saving JSON content."""
        with tempfile.TemporaryDirectory() as temp_dir:
            fm = FileManager()

            test_data = {"title": "Test Paper", "doi": "10.1234/test"}
            filename = "test_metadata.json"

            result_path = fm.save_content(test_data, filename, "json", Path(temp_dir))

            assert result_path.exists()
            assert result_path.name == filename

            # Verify content
            with open(result_path) as f:
                loaded_data = json.load(f)
            assert loaded_data == test_data

    def test_save_content_text(self):
        """Test saving text content."""
        with tempfile.TemporaryDirectory() as temp_dir:
            fm = FileManager()

            test_text = "This is test content for file saving."
            filename = "test_content.txt"

            result_path = fm.save_content(test_text, filename, "txt", Path(temp_dir))

            assert result_path.exists()
            assert result_path.name == filename

            # Verify content
            with open(result_path) as f:
                loaded_text = f.read()
            assert loaded_text == test_text

    def test_save_content_pdf(self):
        """Test saving PDF (binary) content."""
        with tempfile.TemporaryDirectory() as temp_dir:
            fm = FileManager()

            test_bytes = b"PDF content goes here"
            filename = "test_document.pdf"

            result_path = fm.save_content(test_bytes, filename, "pdf", Path(temp_dir))

            assert result_path.exists()
            assert result_path.name == filename

            # Verify content
            with open(result_path, "rb") as f:
                loaded_bytes = f.read()
            assert loaded_bytes == test_bytes

    def test_create_temp_file(self):
        """Test temporary file creation."""
        fm = FileManager()

        temp_file = fm.create_temp_file(suffix=".txt", prefix="test_")

        assert temp_file.exists()
        assert temp_file.name.startswith("test_")
        assert temp_file.name.endswith(".txt")
        assert str(fm.temp_dir) in str(temp_file)

    def test_cleanup_temp_file(self):
        """Test temporary file cleanup."""
        fm = FileManager()

        # Create a temp file
        temp_file = fm.create_temp_file()
        assert temp_file.exists()

        # Test cleanup
        was_deleted = fm.cleanup_temp_file(temp_file, force=True)
        assert was_deleted is True
        assert not temp_file.exists()

    def test_cleanup_temp_file_policy(self):
        """Test cleanup respects retention policy."""
        # Test with keep_temp_files = False
        with patch.object(
            FileManager, "_get_temp_retention_policy", return_value=False
        ):
            fm = FileManager()
            temp_file = fm.create_temp_file()

            was_deleted = fm.cleanup_temp_file(temp_file)
            assert was_deleted is True
            assert not temp_file.exists()

        # Test with keep_temp_files = True
        with patch.object(FileManager, "_get_temp_retention_policy", return_value=True):
            fm = FileManager()
            temp_file = fm.create_temp_file()

            was_deleted = fm.cleanup_temp_file(temp_file)
            assert was_deleted is False
            assert temp_file.exists()

            # Cleanup
            temp_file.unlink()

    def test_save_with_metadata(self):
        """Test saving content with metadata."""
        with tempfile.TemporaryDirectory():
            fm = FileManager()

            content = "Test paper content"
            metadata = {"title": "Test Paper", "author": "Test Author"}

            result = fm.save_with_metadata(content, "paper", "test_id", "txt", metadata)

            assert "content" in result
            assert "metadata" in result

            # Both files should exist
            assert result["content"].exists()
            assert result["metadata"].exists()

            # Verify content files
            with open(result["content"]) as f:
                assert f.read() == content

            with open(result["metadata"]) as f:
                assert json.load(f) == metadata


class TestFileWritingInTools:
    """Test file writing functionality in all tools."""

    def test_get_doi_metadata_file_saving(self):
        """Test get_doi_metadata saves files correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(file_manager, "output_dir", Path(temp_dir)):
                # Test with custom filename
                result = get_doi_metadata(
                    "10.1038/nature12373", save_to="test_metadata.json"
                )

                if result is not None:  # Only test if API call succeeded
                    saved_file = Path(temp_dir) / "test_metadata.json"
                    assert saved_file.exists()

                    # Verify content is valid JSON
                    with open(saved_file) as f:
                        data = json.load(f)
                    assert isinstance(data, dict)

    def test_get_doi_metadata_auto_filename(self):
        """Test get_doi_metadata with auto-generated filename."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(file_manager, "output_dir", Path(temp_dir)):
                # Get existing files before test in output directory
                files_before = list(Path(temp_dir).glob("metadata_*.json"))

                result = get_doi_metadata("10.1038/nature12373", save_file=True)

                if result is not None:
                    # Should have created a file with auto-generated name in
                    # output directory
                    files_after = list(Path(temp_dir).glob("metadata_*.json"))
                    new_files = [f for f in files_after if f not in files_before]
                    assert len(new_files) >= 1

                    # Filename should contain metadata - accept any DOI format
                    auto_file = new_files[0]
                    assert "metadata" in auto_file.name
                    # Just check it has some DOI-like identifier
                    assert any(char in auto_file.name for char in ["10.", "_"])

                    # Cleanup
                    auto_file.unlink(missing_ok=True)

    @pytest.mark.external_api
    def test_get_abstract_from_pubmed_id_file_saving(self):
        """Test get_abstract_from_pubmed_id saves files correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(file_manager, "output_dir", Path(temp_dir)):
                result = get_abstract_from_pubmed_id(
                    "31653696", save_to="test_abstract.txt"
                )

                if result:  # Only test if we got an abstract
                    saved_file = Path(temp_dir) / "test_abstract.txt"
                    assert saved_file.exists()

                    # Verify content matches returned result
                    with open(saved_file) as f:
                        file_content = f.read()
                    assert isinstance(result, dict)
                    assert "content" in result
                    # Compare file content with the content field from structured return
                    # Note: File contains full content, result["content"] might be
                    # truncated
                    assert file_content == result["content"] or result.get(
                        "truncated", False
                    )

    @pytest.mark.external_api
    @pytest.mark.slow
    def test_get_full_text_from_doi_file_saving(self):
        """Test get_full_text_from_doi saves files correctly."""
        test_email = get_test_email()

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(file_manager, "output_dir", Path(temp_dir)):
                result = get_full_text_from_doi(
                    "10.1128/msystems.00045-18", test_email, save_to="test_fulltext.txt"
                )

                if result:  # Only test if we got full text
                    saved_file = Path(temp_dir) / "test_fulltext.txt"
                    assert saved_file.exists()

                    # Verify content matches returned result
                    with open(saved_file) as f:
                        file_content = f.read()
                    assert isinstance(result, dict)
                    assert "content" in result
                    # Compare file content with the content field from structured return
                    # Note: File contains full content, result["content"] might be
                    # truncated
                    assert file_content == result["content"] or result.get(
                        "truncated", False
                    )

    @pytest.mark.external_api
    def test_search_papers_by_keyword_file_saving(self):
        """Test search_papers_by_keyword saves files correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(file_manager, "output_dir", Path(temp_dir)):
                result = search_papers_by_keyword(
                    "CRISPR", max_results=5, save_to="test_search.json"
                )

                if result is not None:
                    saved_file = Path(temp_dir) / "test_search.json"
                    assert saved_file.exists()

                    # Verify content is valid JSON and matches result
                    with open(saved_file) as f:
                        data = json.load(f)
                    # The file contains the original data without the saved_to key
                    # Compare the file content with the result excluding saved_to
                    result_without_saved_to = {
                        k: v for k, v in result.items() if k != "saved_to"
                    }
                    assert data == result_without_saved_to

    def test_extract_pdf_text_file_saving(self):
        """Test extract_pdf_text saves files correctly."""
        # Use a real PDF URL for testing
        pdf_url = "https://ceur-ws.org/Vol-1747/IT201_ICBO2016.pdf"

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(file_manager, "output_dir", Path(temp_dir)):
                result = extract_pdf_text(pdf_url, save_to="test_pdf_text.txt")

                if result and "Error" not in str(result):
                    saved_file = Path(temp_dir) / "test_pdf_text.txt"
                    assert saved_file.exists()

                    # Verify content matches returned result
                    with open(saved_file) as f:
                        file_content = f.read()
                    assert isinstance(result, dict)
                    assert "content" in result
                    # Compare file content with the content field from structured return
                    # Note: File contains full content, result["content"] might be
                    # truncated
                    assert file_content == result["content"] or result.get(
                        "truncated", False
                    )


class TestFileWritingErrorHandling:
    """Test error handling in file writing operations."""

    def test_file_saving_with_invalid_path(self):
        """Test file saving gracefully handles invalid paths."""
        # Mock file_manager to use invalid path
        with patch.object(
            file_manager, "output_dir", Path("/invalid/path/that/does/not/exist")
        ):
            # Should not raise exception, just log warning
            result = get_doi_metadata("10.1038/nature12373", "test.json")

            # Function should still return data even if file save fails
            if result is not None:
                assert isinstance(result, dict)

    def test_file_saving_with_permission_error(self):
        """Test file saving handles permission errors gracefully."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a directory with no write permissions
            no_write_dir = Path(temp_dir) / "no_write"
            no_write_dir.mkdir()
            no_write_dir.chmod(0o444)  # Read-only

            try:
                with patch.object(file_manager, "output_dir", no_write_dir):
                    # Should not raise exception
                    result = get_doi_metadata("10.1038/nature12373", "test.json")

                    # Function should still return data
                    if result is not None:
                        assert isinstance(result, dict)

            finally:
                # Restore permissions for cleanup
                no_write_dir.chmod(0o755)

    def test_file_saving_without_extension(self):
        """Test file saving automatically adds extensions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(file_manager, "output_dir", Path(temp_dir)):
                result = get_doi_metadata(
                    "10.1038/nature12373", save_to="test_metadata"
                )

                if result is not None:
                    # Should have created file with .json extension
                    saved_file = Path(temp_dir) / "test_metadata.json"
                    assert saved_file.exists()

    def test_file_saving_with_subdirectory(self):
        """Test file saving creates subdirectories as needed."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(file_manager, "output_dir", Path(temp_dir)):
                result = get_doi_metadata(
                    "10.1038/nature12373", save_to="subdir/test.json"
                )

                if result is not None:
                    # Should have created subdirectory and file
                    saved_file = Path(temp_dir) / "subdir" / "test.json"
                    assert saved_file.exists()
                    assert saved_file.parent.is_dir()


class TestEnvironmentConfiguration:
    """Test environment variable configuration."""

    @patch.dict("os.environ", {"ARTL_KEEP_TEMP_FILES": "true"})
    def test_keep_temp_files_true(self):
        """Test temp file retention when ARTL_KEEP_TEMP_FILES=true."""
        fm = FileManager()
        assert fm.keep_temp_files is True

    @patch.dict("os.environ", {"ARTL_KEEP_TEMP_FILES": "false"})
    def test_keep_temp_files_false(self):
        """Test temp file deletion when ARTL_KEEP_TEMP_FILES=false."""
        fm = FileManager()
        assert fm.keep_temp_files is False

    @patch.dict("os.environ", {"ARTL_KEEP_TEMP_FILES": "1"})
    def test_keep_temp_files_numeric_true(self):
        """Test temp file retention with numeric true value."""
        fm = FileManager()
        assert fm.keep_temp_files is True

    @patch.dict("os.environ", {"ARTL_KEEP_TEMP_FILES": "yes"})
    def test_keep_temp_files_yes(self):
        """Test temp file retention with 'yes' value."""
        fm = FileManager()
        assert fm.keep_temp_files is True

    @patch.dict("os.environ", {"ARTL_OUTPUT_DIR": "/custom/output/path"})
    def test_custom_output_directory(self):
        """Test custom output directory from environment."""
        with patch("pathlib.Path.mkdir"):  # Mock mkdir to avoid creating real dirs
            fm = FileManager()
            assert str(fm.output_dir) == "/custom/output/path"

    @patch.dict("os.environ", {"ARTL_TEMP_DIR": "/custom/temp/path"})
    def test_custom_temp_directory(self):
        """Test custom temp directory from environment."""
        with patch("pathlib.Path.mkdir"):  # Mock mkdir to avoid creating real dirs
            fm = FileManager()
            assert str(fm.temp_dir) == "/custom/temp/path"


class TestCrossPlatformCompatibility:
    """Test cross-platform file management features."""

    def test_windows_path_handling(self):
        """Test Windows-style path handling."""
        fm = FileManager()

        # Test Windows-style paths in filenames
        test_cases = [
            ("C:\\Users\\test\\file.txt", "C__Users_test_file.txt"),
            ("file\\with\\backslashes", "file_with_backslashes"),
            ("normal_file.txt", "normal_file.txt"),
        ]

        for input_path, expected in test_cases:
            result = fm.sanitize_filename(input_path)
            assert result == expected

    def test_unicode_filename_support(self):
        """Test support for Unicode characters in filenames."""
        fm = FileManager()

        unicode_filename = "测试文件_тест_파일.txt"
        result = fm.sanitize_filename(unicode_filename)

        # Should preserve Unicode characters
        assert "测试文件" in result
        assert "тест" in result
        assert "파일" in result

    def test_long_path_handling(self):
        """Test handling of very long file paths."""
        with tempfile.TemporaryDirectory() as temp_dir:
            fm = FileManager()

            # Create a deeply nested directory structure
            long_path = Path(temp_dir)
            for i in range(10):
                long_path = long_path / f"level_{i}"

            long_path.mkdir(parents=True, exist_ok=True)

            # Should be able to save to deep path
            test_content = {"test": "data"}
            result_path = fm.save_content(test_content, "test.json", "json", long_path)

            assert result_path.exists()
            assert result_path.parent == long_path


class TestConvenienceFunctions:
    """Test convenience functions for file management."""

    def test_convenience_functions_import(self):
        """Test that convenience functions are importable."""
        from artl_mcp.utils.file_manager import (
            get_safe_filename,
            save_json,
            save_pdf,
            save_text,
        )

        # Functions should be callable
        assert callable(save_json)
        assert callable(save_text)
        assert callable(save_pdf)
        assert callable(get_safe_filename)

    def test_get_safe_filename(self):
        """Test get_safe_filename convenience function."""
        from artl_mcp.utils.file_manager import get_safe_filename

        filename = get_safe_filename("metadata", "10.1038/nature12373", "json")

        assert filename.startswith("metadata_")
        assert "10.1038_nature12373" in filename
        assert filename.endswith(".json")

    def test_save_json_convenience(self):
        """Test save_json convenience function."""
        from artl_mcp.utils.file_manager import save_json

        with tempfile.TemporaryDirectory() as temp_dir:
            test_data = {"title": "Test Paper"}

            result_path = save_json(test_data, "test.json", Path(temp_dir))

            assert result_path.exists()
            with open(result_path) as f:
                loaded_data = json.load(f)
            assert loaded_data == test_data

    def test_save_text_convenience(self):
        """Test save_text convenience function."""
        from artl_mcp.utils.file_manager import save_text

        with tempfile.TemporaryDirectory() as temp_dir:
            test_text = "Test content"

            result_path = save_text(test_text, "test.txt", Path(temp_dir))

            assert result_path.exists()
            with open(result_path) as f:
                loaded_text = f.read()
            assert loaded_text == test_text

    def test_save_pdf_convenience(self):
        """Test save_pdf convenience function."""
        from artl_mcp.utils.file_manager import save_pdf

        with tempfile.TemporaryDirectory() as temp_dir:
            test_bytes = b"PDF content"

            result_path = save_pdf(test_bytes, "test.pdf", Path(temp_dir))

            assert result_path.exists()
            with open(result_path, "rb") as f:
                loaded_bytes = f.read()
            assert loaded_bytes == test_bytes
