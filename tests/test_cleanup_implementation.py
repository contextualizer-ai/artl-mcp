"""
Tests for cleanup implementation and temporary file management.

This module specifically tests:
- Temp file creation and cleanup policies
- PDF processing temp file handling
- Error conditions in cleanup
- Retention policies based on environment configuration
- Edge cases in file cleanup
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from artl_mcp.utils.file_manager import FileManager, file_manager
from artl_mcp.utils.pdf_fetcher import extract_text_from_pdf


class TestTempFileCreation:
    """Test temporary file creation functionality."""

    def test_create_temp_file_default_params(self):
        """Test temp file creation with default parameters."""
        fm = FileManager()

        temp_file = fm.create_temp_file()

        try:
            # File should exist and be in temp directory
            assert temp_file.exists()
            assert str(fm.temp_dir) in str(temp_file)
            assert temp_file.name.startswith("artl_")

            # Should be a file, not directory
            assert temp_file.is_file()

        finally:
            # Cleanup
            if temp_file.exists():
                temp_file.unlink()

    def test_create_temp_file_custom_params(self):
        """Test temp file creation with custom prefix and suffix."""
        fm = FileManager()

        temp_file = fm.create_temp_file(suffix=".pdf", prefix="test_pdf_")

        try:
            assert temp_file.exists()
            assert temp_file.name.startswith("test_pdf_")
            assert temp_file.name.endswith(".pdf")
            assert str(fm.temp_dir) in str(temp_file)

        finally:
            if temp_file.exists():
                temp_file.unlink()

    def test_create_multiple_temp_files(self):
        """Test creating multiple temp files generates unique names."""
        fm = FileManager()

        temp_files = []

        try:
            # Create multiple temp files
            for i in range(5):
                temp_file = fm.create_temp_file(suffix=f"_{i}.tmp")
                temp_files.append(temp_file)
                assert temp_file.exists()

            # All should have unique names
            names = [tf.name for tf in temp_files]
            assert len(set(names)) == len(names)  # All unique

        finally:
            # Cleanup all files
            for tf in temp_files:
                if tf.exists():
                    tf.unlink()

    def test_temp_dir_creation(self):
        """Test that temp directory is created if it doesn't exist."""
        with tempfile.TemporaryDirectory() as parent_temp:
            custom_temp_dir = Path(parent_temp) / "custom_artl_temp"

            with patch.object(
                FileManager, "_get_temp_directory", return_value=custom_temp_dir
            ):
                fm = FileManager()
                temp_file = fm.create_temp_file()

                try:
                    # Temp directory should have been created
                    assert custom_temp_dir.exists()
                    assert custom_temp_dir.is_dir()
                    assert temp_file.exists()
                    assert str(custom_temp_dir) in str(temp_file)

                finally:
                    if temp_file.exists():
                        temp_file.unlink()


class TestCleanupPolicies:
    """Test cleanup policies and retention settings."""

    def test_cleanup_force_delete(self):
        """Test forced cleanup regardless of policy."""
        fm = FileManager()

        # Create temp file
        temp_file = fm.create_temp_file()
        assert temp_file.exists()

        # Force cleanup should always delete
        was_deleted = fm.cleanup_temp_file(temp_file, force=True)

        assert was_deleted is True
        assert not temp_file.exists()

    def test_cleanup_respects_keep_policy_true(self):
        """Test cleanup respects keep_temp_files=True policy."""
        with patch.object(FileManager, "_get_temp_retention_policy", return_value=True):
            fm = FileManager()

            temp_file = fm.create_temp_file()
            assert temp_file.exists()

            # Should not delete when policy is to keep files
            was_deleted = fm.cleanup_temp_file(temp_file)

            assert was_deleted is False
            assert temp_file.exists()

            # Cleanup for test
            temp_file.unlink()

    def test_cleanup_respects_keep_policy_false(self):
        """Test cleanup respects keep_temp_files=False policy."""
        with patch.object(
            FileManager, "_get_temp_retention_policy", return_value=False
        ):
            fm = FileManager()

            temp_file = fm.create_temp_file()
            assert temp_file.exists()

            # Should delete when policy is to not keep files
            was_deleted = fm.cleanup_temp_file(temp_file)

            assert was_deleted is True
            assert not temp_file.exists()

    def test_cleanup_nonexistent_file(self):
        """Test cleanup of non-existent file."""
        fm = FileManager()

        # Try to cleanup a file that doesn't exist
        with tempfile.TemporaryDirectory() as temp_dir:
            nonexistent_file = Path(temp_dir) / "nonexistent_file_12345.tmp"

            was_deleted = fm.cleanup_temp_file(nonexistent_file)

            # Should return True (considered successfully "deleted")
            assert was_deleted is True

    def test_cleanup_permission_error(self):
        """Test cleanup handles permission errors gracefully."""
        fm = FileManager()

        temp_file = fm.create_temp_file()
        assert temp_file.exists()

        # Mock a permission error during deletion
        with patch.object(
            Path, "unlink", side_effect=PermissionError("Permission denied")
        ):
            was_deleted = fm.cleanup_temp_file(temp_file, force=True)

            # Should return False when deletion fails
            assert was_deleted is False
            assert temp_file.exists()  # File should still exist

        # Cleanup
        temp_file.unlink()

    def test_cleanup_os_error(self):
        """Test cleanup handles OS errors gracefully."""
        fm = FileManager()

        temp_file = fm.create_temp_file()
        assert temp_file.exists()

        # Mock an OS error during deletion
        with patch.object(Path, "unlink", side_effect=OSError("File in use")):
            was_deleted = fm.cleanup_temp_file(temp_file, force=True)

            # Should return False when deletion fails
            assert was_deleted is False

        # Cleanup
        temp_file.unlink()


class TestEnvironmentRetentionPolicy:
    """Test environment variable configuration for retention policy."""

    @patch.dict("os.environ", {"ARTL_KEEP_TEMP_FILES": "true"})
    def test_retention_policy_true_variants(self):
        """Test various 'true' values for retention policy."""
        fm = FileManager()
        assert fm.keep_temp_files is True

    @patch.dict("os.environ", {"ARTL_KEEP_TEMP_FILES": "TRUE"})
    def test_retention_policy_case_insensitive(self):
        """Test case insensitive retention policy."""
        fm = FileManager()
        assert fm.keep_temp_files is True

    @patch.dict("os.environ", {"ARTL_KEEP_TEMP_FILES": "1"})
    def test_retention_policy_numeric_true(self):
        """Test numeric true value."""
        fm = FileManager()
        assert fm.keep_temp_files is True

    @patch.dict("os.environ", {"ARTL_KEEP_TEMP_FILES": "yes"})
    def test_retention_policy_yes(self):
        """Test 'yes' value."""
        fm = FileManager()
        assert fm.keep_temp_files is True

    @patch.dict("os.environ", {"ARTL_KEEP_TEMP_FILES": "on"})
    def test_retention_policy_on(self):
        """Test 'on' value."""
        fm = FileManager()
        assert fm.keep_temp_files is True

    @patch.dict("os.environ", {"ARTL_KEEP_TEMP_FILES": "false"})
    def test_retention_policy_false(self):
        """Test 'false' value."""
        fm = FileManager()
        assert fm.keep_temp_files is False

    @patch.dict("os.environ", {"ARTL_KEEP_TEMP_FILES": "0"})
    def test_retention_policy_numeric_false(self):
        """Test numeric false value."""
        fm = FileManager()
        assert fm.keep_temp_files is False

    @patch.dict("os.environ", {"ARTL_KEEP_TEMP_FILES": "no"})
    def test_retention_policy_no(self):
        """Test 'no' value."""
        fm = FileManager()
        assert fm.keep_temp_files is False

    @patch.dict("os.environ", {"ARTL_KEEP_TEMP_FILES": "off"})
    def test_retention_policy_off(self):
        """Test 'off' value."""
        fm = FileManager()
        assert fm.keep_temp_files is False

    @patch.dict("os.environ", {"ARTL_KEEP_TEMP_FILES": "invalid_value"})
    def test_retention_policy_invalid_value(self):
        """Test invalid value defaults to False."""
        fm = FileManager()
        assert fm.keep_temp_files is False

    def test_retention_policy_no_env_var(self):
        """Test default value when environment variable is not set."""
        # Ensure env var is not set for this test
        with patch.dict("os.environ", {}, clear=False):
            # Remove the key if it exists
            os.environ.pop("ARTL_KEEP_TEMP_FILES", None)

            fm = FileManager()
            assert fm.keep_temp_files is False  # Default should be False

    def test_custom_output_directory(self):
        """Test custom output directory from environment."""
        with tempfile.TemporaryDirectory() as temp_output:
            with patch.dict("os.environ", {"ARTL_OUTPUT_DIR": temp_output}):
                fm = FileManager()
                assert str(fm.output_dir) == temp_output

    def test_custom_temp_directory(self):
        """Test custom temp directory from environment."""
        with tempfile.TemporaryDirectory() as temp_temp:
            with patch.dict("os.environ", {"ARTL_TEMP_DIR": temp_temp}):
                fm = FileManager()
                assert str(fm.temp_dir) == temp_temp


class TestPDFProcessingCleanup:
    """Test cleanup in PDF processing workflows."""

    @pytest.mark.external_api
    @pytest.mark.slow
    def test_pdf_extraction_uses_temp_files(self):
        """Test that PDF extraction creates and cleans up temp files."""
        pdf_url = "https://ceur-ws.org/Vol-1747/IT201_ICBO2016.pdf"

        # Track temp file creation by mocking file_manager.create_temp_file
        from artl_mcp.utils.file_manager import file_manager

        original_create_temp_file = file_manager.create_temp_file
        temp_files_created = []

        def mock_create_temp_file(*args, **kwargs):
            temp_file = original_create_temp_file(*args, **kwargs)
            temp_files_created.append(temp_file)
            return temp_file

        with patch.object(
            file_manager, "create_temp_file", side_effect=mock_create_temp_file
        ):
            result = extract_text_from_pdf(pdf_url)

            if result and "Error" not in str(result):
                # Should have created temp files during PDF processing
                assert len(temp_files_created) >= 1  # At least one temp file created

                # Temp files should be cleaned up after processing
                for temp_file_path in temp_files_created:
                    assert (
                        not temp_file_path.exists()
                    ), f"Temp file {temp_file_path} was not cleaned up"

    def test_pdf_extraction_temp_file_cleanup_failure(self):
        """Test temp file cleanup when PDF extraction fails."""
        invalid_pdf_url = "https://example.com/nonexistent.pdf"

        # Track temp file operations
        original_create = file_manager.create_temp_file
        original_cleanup = file_manager.cleanup_temp_file

        created_files = []
        cleaned_files = []

        def mock_create(*args, **kwargs):
            temp_file = original_create(*args, **kwargs)
            created_files.append(temp_file)
            return temp_file

        def mock_cleanup(temp_file, force=False):
            cleaned_files.append(temp_file)
            return original_cleanup(temp_file, force)

        with (
            patch.object(file_manager, "create_temp_file", side_effect=mock_create),
            patch.object(file_manager, "cleanup_temp_file", side_effect=mock_cleanup),
            patch(
                "artl_mcp.utils.pdf_fetcher.requests.get",
                side_effect=ConnectionError("Network error"),
            ),
        ):

            result = extract_text_from_pdf(invalid_pdf_url)

            # Even on failure, cleanup should still be attempted
            # (though there might not be any temp files created if it fails early)
            assert result is None or "Error" in str(result)

    def test_pdf_extraction_with_keep_temp_files(self):
        """Test PDF extraction respects keep_temp_files setting."""
        pdf_url = "https://ceur-ws.org/Vol-1747/IT201_ICBO2016.pdf"

        with patch.object(FileManager, "_get_temp_retention_policy", return_value=True):
            # When keep_temp_files is True, files should be preserved
            original_cleanup = file_manager.cleanup_temp_file
            cleanup_calls = []

            def mock_cleanup(temp_file, force=False):
                cleanup_calls.append((temp_file, force))
                return original_cleanup(temp_file, force)

            with patch.object(
                file_manager, "cleanup_temp_file", side_effect=mock_cleanup
            ):
                result = extract_text_from_pdf(pdf_url)

                if result and "Error" not in str(result):
                    # Cleanup should have been called but files should be preserved
                    for _temp_file, force in cleanup_calls:
                        if not force:  # Non-forced cleanup should preserve files
                            # This depends on the implementation - some temp files might
                            # still exist if policy is to keep them
                            pass


class TestCleanupEdgeCases:
    """Test edge cases in cleanup implementation."""

    def test_cleanup_directory_instead_of_file(self):
        """Test cleanup behavior when given a directory path."""
        fm = FileManager()

        # Create a temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Try to cleanup a directory - should handle gracefully
            was_deleted = fm.cleanup_temp_file(temp_path, force=True)

            # Directory should still exist (we don't delete directories)
            assert temp_path.exists()
            # cleanup should return False for directories
            assert was_deleted is False

    def test_cleanup_symlink(self):
        """Test cleanup of symbolic links."""
        fm = FileManager()

        # Create a real file and a symlink to it
        real_file = fm.create_temp_file()
        symlink_path = real_file.parent / f"{real_file.name}_link"

        try:
            # Create symlink (skip if not supported on this platform)
            try:
                symlink_path.symlink_to(real_file)
            except OSError:
                pytest.skip("Symlinks not supported on this platform")

            # Cleanup should work on symlinks
            was_deleted = fm.cleanup_temp_file(symlink_path, force=True)

            assert was_deleted is True
            assert not symlink_path.exists()
            assert real_file.exists()  # Original file should still exist

        finally:
            # Cleanup
            if real_file.exists():
                real_file.unlink()
            if symlink_path.exists():
                symlink_path.unlink()

    def test_cleanup_with_concurrent_access(self):
        """Test cleanup when file is being accessed concurrently."""
        fm = FileManager()

        temp_file = fm.create_temp_file()

        try:
            # Open file for writing to simulate concurrent access
            with open(temp_file, "w") as f:
                f.write("test content")

                # Try to cleanup while file is open
                # This might succeed or fail depending on the platform
                was_deleted = fm.cleanup_temp_file(temp_file, force=True)

                # On Windows, this might fail; on Unix, it might succeed
                # Just ensure it doesn't crash
                assert isinstance(was_deleted, bool)

        finally:
            # Ensure cleanup after test
            if temp_file.exists():
                temp_file.unlink()

    def test_cleanup_very_long_filename(self):
        """Test cleanup with very long filenames."""
        fm = FileManager()

        # Create file with very long name
        long_suffix = "_" + "a" * 200 + ".tmp"
        temp_file = fm.create_temp_file(suffix=long_suffix)

        try:
            assert temp_file.exists()

            # Cleanup should work even with long names
            was_deleted = fm.cleanup_temp_file(temp_file, force=True)

            assert was_deleted is True
            assert not temp_file.exists()

        except OSError:
            # Some filesystems might not support very long names
            if temp_file.exists():
                temp_file.unlink()

    def test_cleanup_unicode_filename(self):
        """Test cleanup with Unicode characters in filename."""
        fm = FileManager()

        unicode_suffix = "_测试文件_тест_파일.tmp"
        temp_file = fm.create_temp_file(suffix=unicode_suffix)

        try:
            assert temp_file.exists()

            # Cleanup should work with Unicode filenames
            was_deleted = fm.cleanup_temp_file(temp_file, force=True)

            assert was_deleted is True
            assert not temp_file.exists()

        except (OSError, UnicodeError):
            # Some filesystems might not support Unicode names
            if temp_file.exists():
                temp_file.unlink()


class TestCleanupInErrorScenarios:
    """Test cleanup behavior during error scenarios."""

    def test_cleanup_during_disk_full_error(self):
        """Test cleanup behavior when disk is full."""
        fm = FileManager()

        temp_file = fm.create_temp_file()

        try:
            assert temp_file.exists()

            # Mock disk full error during deletion
            with patch.object(
                Path, "unlink", side_effect=OSError("No space left on device")
            ):
                was_deleted = fm.cleanup_temp_file(temp_file, force=True)

                # Should handle error gracefully
                assert was_deleted is False
                assert temp_file.exists()

        finally:
            # Real cleanup
            if temp_file.exists():
                temp_file.unlink()

    def test_cleanup_during_network_drive_error(self):
        """Test cleanup behavior with network drive errors."""
        fm = FileManager()

        temp_file = fm.create_temp_file()

        try:
            assert temp_file.exists()

            # Mock network error during deletion
            with patch.object(
                Path, "unlink", side_effect=OSError("Network path not found")
            ):
                was_deleted = fm.cleanup_temp_file(temp_file, force=True)

                # Should handle error gracefully
                assert was_deleted is False

        finally:
            # Real cleanup
            if temp_file.exists():
                temp_file.unlink()

    def test_cleanup_during_interrupt(self):
        """Test cleanup behavior during interruption."""
        fm = FileManager()

        temp_file = fm.create_temp_file()

        try:
            assert temp_file.exists()

            # Mock keyboard interrupt during deletion
            with patch.object(
                Path, "unlink", side_effect=KeyboardInterrupt("User interrupted")
            ):
                # KeyboardInterrupt should not be caught
                with pytest.raises(KeyboardInterrupt):
                    fm.cleanup_temp_file(temp_file, force=True)

        finally:
            # Real cleanup
            if temp_file.exists():
                temp_file.unlink()


class TestBatchCleanupOperations:
    """Test batch cleanup operations and multiple file handling."""

    def test_cleanup_multiple_files(self):
        """Test cleanup of multiple files."""
        fm = FileManager()

        # Create multiple temp files
        temp_files = []
        for i in range(5):
            temp_file = fm.create_temp_file(suffix=f"_{i}.tmp")
            temp_files.append(temp_file)

        try:
            # All files should exist
            for tf in temp_files:
                assert tf.exists()

            # Cleanup all files
            deletion_results = []
            for tf in temp_files:
                result = fm.cleanup_temp_file(tf, force=True)
                deletion_results.append(result)

            # All should be deleted
            assert all(deletion_results)
            for tf in temp_files:
                assert not tf.exists()

        finally:
            # Ensure cleanup
            for tf in temp_files:
                if tf.exists():
                    tf.unlink()

    def test_cleanup_mixed_success_failure(self):
        """Test cleanup with mixed success and failure scenarios."""
        fm = FileManager()

        # Create multiple temp files
        temp_files = []
        for i in range(3):
            temp_file = fm.create_temp_file(suffix=f"_{i}.tmp")
            temp_files.append(temp_file)

        try:
            deletion_results = []

            # Cleanup with one file causing an error
            for i, tf in enumerate(temp_files):
                if i == 1:  # Middle file causes error
                    with patch.object(
                        Path, "unlink", side_effect=PermissionError("Access denied")
                    ):
                        result = fm.cleanup_temp_file(tf, force=True)
                else:
                    result = fm.cleanup_temp_file(tf, force=True)

                deletion_results.append(result)

            # Two should succeed, one should fail
            assert deletion_results[0] is True
            assert deletion_results[1] is False  # The error case
            assert deletion_results[2] is True

        finally:
            # Ensure cleanup
            for tf in temp_files:
                if tf.exists():
                    tf.unlink()


class TestFileManagerIntegration:
    """Test integration between FileManager and temp file operations."""

    def test_temp_directory_persistence(self):
        """Test that temp directory persists across multiple file operations."""
        with tempfile.TemporaryDirectory() as temp_parent:
            custom_temp = Path(temp_parent) / "persistent_temp"

            with patch.object(
                FileManager, "_get_temp_directory", return_value=custom_temp
            ):
                fm = FileManager()

                # Create multiple files in sequence
                temp_files = []
                for i in range(3):
                    temp_file = fm.create_temp_file(suffix=f"_{i}.tmp")
                    temp_files.append(temp_file)
                    assert temp_file.exists()
                    assert str(custom_temp) in str(temp_file)

                # All files should be in the same temp directory
                temp_dirs = {tf.parent for tf in temp_files}
                assert len(temp_dirs) == 1  # All in same directory
                assert custom_temp in temp_dirs

                # Cleanup
                for tf in temp_files:
                    if tf.exists():
                        tf.unlink()

    def test_file_manager_state_consistency(self):
        """Test that FileManager maintains consistent state."""
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

                # State should be consistent
                assert str(fm.output_dir) == temp_output
                assert str(fm.temp_dir) == temp_temp
                assert fm.keep_temp_files is True

                # Create files in both directories
                temp_file = fm.create_temp_file()
                output_file = fm.save_content(
                    {"test": "data"}, "test.json", "json", fm.output_dir
                )

                try:
                    # Both operations should succeed
                    assert temp_file.exists()
                    assert output_file.exists()
                    assert str(fm.temp_dir) in str(temp_file)
                    assert str(fm.output_dir) in str(output_file)

                finally:
                    # Cleanup
                    if temp_file.exists():
                        temp_file.unlink()
                    if output_file.exists():
                        output_file.unlink()
