"""Comprehensive tests for async MCP client functionality."""

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest

from artl_mcp.client import run_client


class TestRunClient:
    """Test the async MCP client functionality."""

    @pytest.mark.asyncio
    async def test_run_client_success_with_json_text(self):
        """Test successful client run with JSON text response."""
        # Mock the MCP and client
        mock_mcp = Mock()
        mock_client = AsyncMock()

        # Mock response item with JSON text
        mock_item = Mock()
        mock_item.text = '{"DOI": "10.1038/nature12373", "title": "Test Article"}'

        # Mock client behavior
        mock_client.call_tool = AsyncMock(return_value=[mock_item])

        # Mock the Client context manager
        mock_client_class = AsyncMock()
        mock_client_class.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_class.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "artl_mcp.client.Client", return_value=mock_client_class
        ) as mock_client_constructor:
            with patch("builtins.print") as mock_print:
                await run_client("10.1038/nature12373", mock_mcp)

                # Verify Client was created with the MCP
                mock_client_constructor.assert_called_once_with(mock_mcp)

                # Verify call_tool was called correctly
                mock_client.call_tool.assert_called_once_with(
                    "get_doi_metadata", {"doi": "10.1038/nature12373"}
                )

                # Verify JSON was pretty printed
                mock_print.assert_called_once()
                printed_output = mock_print.call_args[0][0]

                # Should be pretty-printed JSON
                expected_json = {"DOI": "10.1038/nature12373", "title": "Test Article"}
                assert json.loads(printed_output) == expected_json
                assert "\n" in printed_output  # Should be indented

    @pytest.mark.asyncio
    async def test_run_client_success_with_plain_text(self):
        """Test successful client run with plain text response."""
        mock_mcp = Mock()
        mock_client = AsyncMock()

        # Mock response item with plain text
        mock_item = Mock()
        mock_item.text = "This is plain text, not JSON"

        mock_client.call_tool = AsyncMock(return_value=[mock_item])

        mock_client_class = AsyncMock()
        mock_client_class.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_class.__aexit__ = AsyncMock(return_value=None)

        with patch("artl_mcp.client.Client", return_value=mock_client_class):
            with patch("builtins.print") as mock_print:
                await run_client("10.1038/test", mock_mcp)

                # Should print plain text directly
                mock_print.assert_called_once_with("This is plain text, not JSON")

    @pytest.mark.asyncio
    async def test_run_client_success_with_invalid_json(self):
        """Test client run with invalid JSON in text field."""
        mock_mcp = Mock()
        mock_client = AsyncMock()

        # Mock response item with invalid JSON
        mock_item = Mock()
        mock_item.text = '{"invalid": json, "missing": quote}'

        mock_client.call_tool = AsyncMock(return_value=[mock_item])

        mock_client_class = AsyncMock()
        mock_client_class.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_class.__aexit__ = AsyncMock(return_value=None)

        with patch("artl_mcp.client.Client", return_value=mock_client_class):
            with patch("builtins.print") as mock_print:
                await run_client("10.1038/test", mock_mcp)

                # Should print the invalid JSON as plain text when parsing fails
                mock_print.assert_called_once_with(
                    '{"invalid": json, "missing": quote}'
                )

    @pytest.mark.asyncio
    async def test_run_client_success_with_no_text_field(self):
        """Test client run when response item has no text field."""
        mock_mcp = Mock()
        mock_client = AsyncMock()

        # Mock response item without text field
        mock_item = Mock()
        mock_item.text = None
        mock_item.model_dump_json = Mock(
            return_value='{"type": "response", "data": "test"}'
        )

        mock_client.call_tool = AsyncMock(return_value=[mock_item])

        mock_client_class = AsyncMock()
        mock_client_class.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_class.__aexit__ = AsyncMock(return_value=None)

        with patch("artl_mcp.client.Client", return_value=mock_client_class):
            with patch("builtins.print") as mock_print:
                await run_client("10.1038/test", mock_mcp)

                # Should call model_dump_json and print the result
                mock_item.model_dump_json.assert_called_once_with(indent=2)
                mock_print.assert_called_once_with(
                    '{"type": "response", "data": "test"}'
                )

    @pytest.mark.asyncio
    async def test_run_client_success_with_empty_text(self):
        """Test client run when response item has empty text field."""
        mock_mcp = Mock()
        mock_client = AsyncMock()

        # Mock response item with empty text
        mock_item = Mock()
        mock_item.text = ""
        mock_item.model_dump_json = Mock(return_value='{"type": "empty", "data": null}')

        mock_client.call_tool = AsyncMock(return_value=[mock_item])

        mock_client_class = AsyncMock()
        mock_client_class.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_class.__aexit__ = AsyncMock(return_value=None)

        with patch("artl_mcp.client.Client", return_value=mock_client_class):
            with patch("builtins.print") as mock_print:
                await run_client("10.1038/test", mock_mcp)

                # Should use model_dump_json for empty text
                mock_item.model_dump_json.assert_called_once_with(indent=2)
                mock_print.assert_called_once_with('{"type": "empty", "data": null}')

    @pytest.mark.asyncio
    async def test_run_client_success_with_multiple_items(self):
        """Test client run with multiple response items."""
        mock_mcp = Mock()
        mock_client = AsyncMock()

        # Mock multiple response items
        mock_item1 = Mock()
        mock_item1.text = '{"DOI": "10.1038/article1"}'

        mock_item2 = Mock()
        mock_item2.text = "Plain text response"

        mock_item3 = Mock()
        mock_item3.text = None
        mock_item3.model_dump_json = Mock(return_value='{"status": "complete"}')

        mock_client.call_tool = AsyncMock(
            return_value=[mock_item1, mock_item2, mock_item3]
        )

        mock_client_class = AsyncMock()
        mock_client_class.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_class.__aexit__ = AsyncMock(return_value=None)

        with patch("artl_mcp.client.Client", return_value=mock_client_class):
            with patch("builtins.print") as mock_print:
                await run_client("10.1038/test", mock_mcp)

                # Should print all three items
                assert mock_print.call_count == 3

                # Check each call
                calls = mock_print.call_args_list

                # First item: JSON pretty-printed
                first_call = calls[0][0][0]
                assert json.loads(first_call) == {"DOI": "10.1038/article1"}

                # Second item: plain text
                assert calls[1][0][0] == "Plain text response"

                # Third item: model dump
                assert calls[2][0][0] == '{"status": "complete"}'

    @pytest.mark.asyncio
    async def test_run_client_with_no_hasattr_text(self):
        """Test client run when response item doesn't have text attribute at all."""
        mock_mcp = Mock()
        mock_client = AsyncMock()

        # Mock response item that doesn't have text attribute
        mock_item = Mock(spec=[])  # Only allow explicitly specified attributes
        mock_item.model_dump_json = Mock(return_value='{"no_text_attr": true}')

        mock_client.call_tool = AsyncMock(return_value=[mock_item])

        mock_client_class = AsyncMock()
        mock_client_class.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_class.__aexit__ = AsyncMock(return_value=None)

        with patch("artl_mcp.client.Client", return_value=mock_client_class):
            with patch("builtins.print") as mock_print:
                await run_client("10.1038/test", mock_mcp)

                # Should use model_dump_json when hasattr(item, "text") is False
                mock_item.model_dump_json.assert_called_once_with(indent=2)
                mock_print.assert_called_once_with('{"no_text_attr": true}')

    @pytest.mark.asyncio
    async def test_run_client_complex_json_formatting(self):
        """Test client run with complex JSON that tests pretty printing."""
        mock_mcp = Mock()
        mock_client = AsyncMock()

        # Mock complex JSON response
        complex_json = {
            "status": "ok",
            "message": {
                "DOI": "10.1038/complex",
                "title": ["Complex Article Title"],
                "author": [
                    {"given": "First", "family": "Author"},
                    {"given": "Second", "family": "Author"},
                ],
                "published": {"date-parts": [[2023, 12, 1]]},
            },
        }

        mock_item = Mock()
        mock_item.text = json.dumps(complex_json)

        mock_client.call_tool = AsyncMock(return_value=[mock_item])

        mock_client_class = AsyncMock()
        mock_client_class.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_class.__aexit__ = AsyncMock(return_value=None)

        with patch("artl_mcp.client.Client", return_value=mock_client_class):
            with patch("builtins.print") as mock_print:
                await run_client("10.1038/complex", mock_mcp)

                # Verify the JSON was pretty-printed with indentation
                printed_output = mock_print.call_args[0][0]
                parsed_output = json.loads(printed_output)

                assert parsed_output == complex_json
                # Check that it's actually indented (contains newlines and spaces)
                assert "\n" in printed_output
                assert "  " in printed_output  # indent=2 should add 2 spaces
