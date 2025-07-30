"""Tests for content windowing functionality."""

from artl_mcp.tools import _apply_content_windowing


class TestContentWindowing:
    """Test suite for the _apply_content_windowing function."""

    def test_no_windowing_small_content(self):
        """Test that small content is returned unchanged."""
        content = "This is a small piece of content."
        result_content, was_windowed = _apply_content_windowing(content)

        assert result_content == content
        assert was_windowed is False

    def test_offset_windowing(self):
        """Test content windowing with offset parameter."""
        content = "0123456789" * 10  # 100 characters
        offset = 20

        result_content, was_windowed = _apply_content_windowing(content, offset=offset)

        expected_content = content[offset:]
        assert result_content.startswith(expected_content)
        assert was_windowed is True
        assert f"Starting from character {offset:,}" in result_content

    def test_offset_beyond_content_length(self):
        """Test offset that exceeds content length."""
        content = "Short content"
        offset = 100

        result_content, was_windowed = _apply_content_windowing(content, offset=offset)

        assert result_content == ""
        assert was_windowed is True

    def test_limit_windowing(self):
        """Test content windowing with limit parameter."""
        content = "0123456789" * 20  # 200 characters
        limit = 50

        result_content, was_windowed = _apply_content_windowing(content, limit=limit)

        expected_content = content[:limit]
        assert result_content.startswith(expected_content)
        assert was_windowed is True
        assert f"showing {limit:,} characters" in result_content

    def test_offset_and_limit_windowing(self):
        """Test content windowing with both offset and limit."""
        content = "0123456789" * 30  # 300 characters
        offset = 50
        limit = 100

        result_content, was_windowed = _apply_content_windowing(
            content, offset=offset, limit=limit
        )

        expected_start = content[offset : offset + limit]
        assert result_content.startswith(expected_start)
        assert was_windowed is True
        assert f"Starting from character {offset:,}" in result_content
        assert f"showing {limit:,} characters" in result_content
        assert f"ends at {offset + limit:,}" in result_content

    def test_large_content_no_truncation(self):
        """Test that large content is no longer truncated by default."""
        content = "x" * 1000  # 1000 characters

        result_content, was_windowed = _apply_content_windowing(content)

        # Content should be returned unchanged when no windowing parameters are used
        assert result_content == content
        assert was_windowed is False

    def test_with_saved_path_message(self):
        """Test windowing message includes saved path when provided."""
        content = "0123456789" * 20  # 200 characters
        saved_path = "/tmp/test_file.txt"
        offset = 50

        result_content, was_windowed = _apply_content_windowing(
            content, saved_path=saved_path, offset=offset
        )

        assert was_windowed is True
        assert f"Full content saved to: {saved_path}" in result_content

    def test_without_saved_path_message(self):
        """Test windowing message when no saved path provided."""
        content = "0123456789" * 20  # 200 characters
        offset = 50

        result_content, was_windowed = _apply_content_windowing(content, offset=offset)

        assert was_windowed is True
        assert "file not saved - use save_file=True or save_to=path" in result_content

    def test_zero_offset_no_windowing(self):
        """Test that offset=0 doesn't trigger windowing."""
        content = "Test content"

        result_content, was_windowed = _apply_content_windowing(content, offset=0)

        assert result_content == content
        assert was_windowed is False

    def test_zero_limit_no_windowing(self):
        """Test that limit=0 doesn't trigger windowing."""
        content = "Test content"

        result_content, was_windowed = _apply_content_windowing(content, limit=0)

        assert result_content == content
        assert was_windowed is False

    def test_none_limit_no_windowing(self):
        """Test that limit=None doesn't trigger windowing."""
        content = "Test content"

        result_content, was_windowed = _apply_content_windowing(content, limit=None)

        assert result_content == content
        assert was_windowed is False

    def test_negative_offset(self):
        """Test that negative offset is treated as zero."""
        content = "Test content"

        result_content, was_windowed = _apply_content_windowing(content, offset=-10)

        assert result_content == content
        assert was_windowed is False

    def test_limit_larger_than_content(self):
        """Test limit larger than content length."""
        content = "Short"
        limit = 100

        result_content, was_windowed = _apply_content_windowing(content, limit=limit)

        assert result_content == content
        assert was_windowed is False

    def test_windowing_preserves_content_structure(self):
        """Test that windowing preserves the structure of the content."""
        content = (
            "# Title\n\n"
            "This is a paragraph with some content.\n\n"
            "## Section 1\n"
            "More content here.\n\n"
            "## Section 2\n"
            "Even more content here.\n"
        ) * 10  # Make it large enough to trigger windowing

        offset = 100
        limit = 200

        result_content, was_windowed = _apply_content_windowing(
            content, offset=offset, limit=limit
        )

        # Extract just the content part (before the windowing message)
        content_part = result_content.split("\n\n[CONTENT WINDOWED")[0]
        expected_content = content[offset : offset + limit]

        assert content_part == expected_content
        assert was_windowed is True

    def test_empty_content(self):
        """Test windowing with empty content."""
        content = ""

        result_content, was_windowed = _apply_content_windowing(
            content, offset=10, limit=50
        )

        assert result_content == ""
        assert was_windowed is True  # Because offset > 0 and >= content_length

    def test_complex_windowing_scenario(self):
        """Test a complex scenario with all parameters."""
        content = "A" * 2000  # Large content
        offset = 500
        limit = 800
        saved_path = "/tmp/complex_test.txt"

        result_content, was_windowed = _apply_content_windowing(
            content, saved_path=saved_path, offset=offset, limit=limit
        )

        # Check windowed content is correct
        expected_content = content[offset : offset + limit]
        content_part = result_content.split("\n\n[CONTENT WINDOWED")[0]
        assert content_part == expected_content

        # Check windowing metadata
        assert was_windowed is True
        assert f"Starting from character {offset:,}" in result_content
        assert f"showing {limit:,} characters" in result_content
        assert f"ends at {offset + limit:,}" in result_content
        assert f"Full content saved to: {saved_path}" in result_content
        assert f"of {len(content):,} total characters" in result_content
