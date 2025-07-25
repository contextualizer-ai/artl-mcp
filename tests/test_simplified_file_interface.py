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

        # Get output files before to find the new one
        files_before = list(file_manager.output_dir.glob("metadata_*.json"))

        result = get_doi_metadata("10.1234/test", save_file=True)

        assert result is not None
        assert result == test_data

        # Check that file was saved to output directory
        files_after = list(file_manager.output_dir.glob("metadata_*.json"))
        new_files = [f for f in files_after if f not in files_before]
        assert len(new_files) >= 1

        # Verify saved content
        with open(new_files[0]) as f:
            saved_data = json.load(f)
        assert saved_data == test_data

        # Cleanup
        for f in new_files:
            f.unlink(missing_ok=True)

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
            assert result == test_data
            assert save_path.exists()

            # Verify saved content
            with open(save_path) as f:
                saved_data = json.load(f)
            assert saved_data == test_data
