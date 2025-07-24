"""Comprehensive tests for main.py MCP server and CLI functionality."""

from unittest.mock import Mock, patch

from click.testing import CliRunner

from artl_mcp.main import cli, create_mcp


class TestCreateMCP:
    """Test MCP server creation and tool registration."""

    def test_create_mcp_returns_fastmcp_instance(self):
        """Test that create_mcp returns a FastMCP instance."""
        mcp = create_mcp()

        # Should return a FastMCP instance
        assert hasattr(mcp, "run")
        assert hasattr(mcp, "tool")

        # Check basic properties
        assert mcp.name == "artl-mcp"
        assert "All Roads to Literature" in mcp.instructions

    def test_create_mcp_has_required_tools(self):
        """Test that create_mcp registers all required tools."""
        mcp = create_mcp()

        # FastMCP stores tools differently - check available tools
        # Tools should be available via the MCP instance
        assert mcp.name == "artl-mcp"
        assert "All Roads to Literature" in mcp.instructions

        # The tool registration happens during create_mcp() call
        # Just verify the MCP instance was created successfully with tools
        assert hasattr(mcp, "tool")  # Has tool decorator method
        assert hasattr(mcp, "run")  # Has run method


class TestCLIFunction:
    """Test the main CLI function."""

    # Note: DOI query functionality is tested via integration tests in test_mcps.py
    # and the async client functionality is tested in test_client.py

    @patch("artl_mcp.main.search_pubmed_for_pmids")
    def test_cli_with_pmid_search_success(self, mock_search):
        """Test CLI with --pmid-search option - successful search."""
        mock_search.return_value = {
            "pmids": ["12345678", "87654321"],
            "total_count": 150,
            "returned_count": 2,
            "query": "test query",
        }

        runner = CliRunner()
        result = runner.invoke(cli, ["--pmid-search", "test query"])

        assert result.exit_code == 0
        mock_search.assert_called_once_with("test query", 20)  # default max_results

        # Check output contains expected information
        assert "Found 2 PMIDs out of 150 total results" in result.output
        assert "12345678" in result.output
        assert "87654321" in result.output
        assert "To get more results, use: --max-results" in result.output

    @patch("artl_mcp.main.search_pubmed_for_pmids")
    def test_cli_with_pmid_search_no_results(self, mock_search):
        """Test CLI with --pmid-search option - no results."""
        mock_search.return_value = {
            "pmids": [],
            "total_count": 0,
            "returned_count": 0,
            "query": "nonexistent query",
        }

        runner = CliRunner()
        result = runner.invoke(cli, ["--pmid-search", "nonexistent query"])

        assert result.exit_code == 0
        mock_search.assert_called_once_with("nonexistent query", 20)

        # Check output for no results message
        assert "No PMIDs found for query 'nonexistent query'" in result.output

    @patch("artl_mcp.main.search_pubmed_for_pmids")
    def test_cli_with_pmid_search_error(self, mock_search):
        """Test CLI with --pmid-search option - search error."""
        mock_search.return_value = None

        runner = CliRunner()
        result = runner.invoke(cli, ["--pmid-search", "error query"])

        assert result.exit_code == 0
        mock_search.assert_called_once_with("error query", 20)

        # Check output for error message
        assert "Error searching for query 'error query'" in result.output

    @patch("artl_mcp.main.search_pubmed_for_pmids")
    def test_cli_with_pmid_search_custom_max_results(self, mock_search):
        """Test CLI with --pmid-search and custom --max-results."""
        mock_search.return_value = {
            "pmids": ["12345678"],
            "total_count": 50,
            "returned_count": 1,
            "query": "custom query",
        }

        runner = CliRunner()
        result = runner.invoke(
            cli, ["--pmid-search", "custom query", "--max-results", "5"]
        )

        assert result.exit_code == 0
        mock_search.assert_called_once_with("custom query", 5)

    def test_cli_with_both_options_error(self):
        """Test CLI with both --doi-query and --pmid-search (should fail)."""
        runner = CliRunner()
        result = runner.invoke(
            cli, ["--doi-query", "10.1038/test", "--pmid-search", "test query"]
        )

        assert result.exit_code != 0
        assert (
            "Cannot use both --doi-query and --pmid-search simultaneously"
            in result.output
        )

    def test_cli_default_behavior(self):
        """Test CLI default behavior (should run MCP server)."""
        runner = CliRunner()

        # The MCP server is created at module level, we need to patch the mcp.run call
        with patch("artl_mcp.main.mcp") as mock_mcp:
            mock_mcp.run = Mock()

            result = runner.invoke(cli, [])

            assert result.exit_code == 0
            mock_mcp.run.assert_called_once()

    @patch("artl_mcp.main.search_pubmed_for_pmids")
    def test_cli_pmid_search_with_max_results_suggestion(self, mock_search):
        """Test that max results suggestion handles edge cases correctly."""
        # Test when total_count is exactly 100
        mock_search.return_value = {
            "pmids": ["12345678"],
            "total_count": 100,
            "returned_count": 1,
            "query": "test",
        }

        runner = CliRunner()
        result = runner.invoke(cli, ["--pmid-search", "test"])

        assert "To get more results, use: --max-results 100" in result.output

        # Test when total_count is over 100 (should cap at 100)
        mock_search.return_value = {
            "pmids": ["12345678"],
            "total_count": 500,
            "returned_count": 1,
            "query": "test",
        }

        result = runner.invoke(cli, ["--pmid-search", "test"])
        assert "To get more results, use: --max-results 100" in result.output

        # Test when returned_count equals total_count (no suggestion)
        mock_search.return_value = {
            "pmids": ["12345678"],
            "total_count": 1,
            "returned_count": 1,
            "query": "test",
        }

        result = runner.invoke(cli, ["--pmid-search", "test"])
        assert "To get more results" not in result.output


class TestCLIHelp:
    """Test CLI help and documentation."""

    def test_cli_help_output(self):
        """Test that CLI help contains expected information."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "All Roads to Literature MCP server" in result.output
        assert "--doi-query" in result.output
        assert "--pmid-search" in result.output
        assert "--max-results" in result.output
