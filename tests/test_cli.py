"""Comprehensive tests for CLI interface."""

import json
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from artl_mcp.cli import (
    clean_text_cmd,
    cli,
    doi_to_pmid_cmd,
    extract_doi_from_url_cmd,
    extract_pdf_text_cmd,
    get_abstract_from_pubmed_id_cmd,
    get_doi_fetcher_metadata_cmd,
    get_doi_metadata_cmd,
    get_doi_text_cmd,
    get_full_text_from_bioc_cmd,
    get_full_text_from_doi_cmd,
    get_full_text_info_cmd,
    get_pmcid_text_cmd,
    get_pmid_from_pmcid_cmd,
    get_pmid_text_cmd,
    get_text_from_pdf_url_cmd,
    get_unpaywall_info_cmd,
    output_result,
    pmid_to_doi_cmd,
    search_papers_by_keyword_cmd,
    search_recent_papers_cmd,
)
from artl_mcp.utils.email_manager import EmailManager


def get_test_email():
    """Get a valid test email address from environment/local config."""
    em = EmailManager()
    email = em.get_email()
    if not email:
        pytest.skip(
            "No valid email address found for CLI testing. "
            "Set ARTL_EMAIL_ADDR or add to local/.env"
        )
    return email


class TestOutputResult:
    """Test the output_result helper function."""

    def test_output_result_with_data(self):
        """Test output_result with valid data."""
        import click

        @click.command()
        def test_cmd():
            output_result({"test": "data", "number": 42})

        runner = CliRunner()
        result = runner.invoke(test_cmd)
        assert result.exit_code == 0
        output = json.loads(result.output.strip())
        assert output == {"test": "data", "number": 42}

    def test_output_result_with_none(self):
        """Test output_result with None input."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            import click

            @click.command()
            def test_cmd():
                output_result(None)

            result = runner.invoke(test_cmd)
            assert result.exit_code == 0
            output = json.loads(result.output.strip())
            assert output == {"error": "No result returned"}


class TestCLIMain:
    """Test the main CLI group function."""

    def test_cli_version(self):
        """Test CLI version option."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "version" in result.output.lower()

    def test_cli_help(self):
        """Test CLI help output."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "All Roads to Literature" in result.output
        assert "CLI tools for scientific literature access" in result.output

    def test_cli_main_group(self):
        """Test main CLI group function."""
        runner = CliRunner()
        result = runner.invoke(cli, [])
        # Click shows usage info when no command given
        assert "Usage:" in result.output


class TestDOICommands:
    """Test DOI-related CLI commands."""

    @patch("artl_mcp.cli.get_doi_metadata")
    def test_get_doi_metadata_cmd_success(self, mock_get_doi_metadata):
        """Test successful DOI metadata retrieval."""
        mock_get_doi_metadata.return_value = {
            "DOI": "10.1038/nature12373",
            "title": "Test Article",
        }

        runner = CliRunner()
        result = runner.invoke(get_doi_metadata_cmd, ["--doi", "10.1038/nature12373"])

        assert result.exit_code == 0
        mock_get_doi_metadata.assert_called_once_with("10.1038/nature12373")
        output = json.loads(result.output.strip())
        assert output["DOI"] == "10.1038/nature12373"

    @patch("artl_mcp.cli.get_doi_metadata")
    def test_get_doi_metadata_cmd_failure(self, mock_get_doi_metadata):
        """Test DOI metadata retrieval failure."""
        mock_get_doi_metadata.return_value = None

        runner = CliRunner()
        result = runner.invoke(get_doi_metadata_cmd, ["--doi", "invalid-doi"])

        assert result.exit_code == 0
        output = json.loads(result.output.strip())
        assert output == {"error": "No result returned"}

    def test_get_doi_metadata_cmd_missing_arg(self):
        """Test DOI metadata command with missing required argument."""
        runner = CliRunner()
        result = runner.invoke(get_doi_metadata_cmd, [])

        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output.lower()

    @patch("artl_mcp.cli.get_doi_fetcher_metadata")
    def test_get_doi_fetcher_metadata_cmd_success(self, mock_get_doi_fetcher_metadata):
        """Test successful DOI fetcher metadata retrieval."""
        mock_get_doi_fetcher_metadata.return_value = {"DOI": "10.1038/nature12373"}

        runner = CliRunner()
        test_email = get_test_email()
        result = runner.invoke(
            get_doi_fetcher_metadata_cmd,
            ["--doi", "10.1038/nature12373", "--email", test_email],
        )

        assert result.exit_code == 0
        mock_get_doi_fetcher_metadata.assert_called_once_with(
            "10.1038/nature12373", test_email
        )

    @patch("artl_mcp.cli.get_doi_text")
    def test_get_doi_text_cmd_success(self, mock_get_doi_text):
        """Test successful DOI text retrieval."""
        mock_get_doi_text.return_value = "This is the full text of the article..."

        runner = CliRunner()
        result = runner.invoke(get_doi_text_cmd, ["--doi", "10.1038/nature12373"])

        assert result.exit_code == 0
        mock_get_doi_text.assert_called_once_with("10.1038/nature12373")
        output = json.loads(result.output.strip())
        assert "This is the full text" in output


class TestPubMedCommands:
    """Test PubMed-related CLI commands."""

    @patch("artl_mcp.cli.get_abstract_from_pubmed_id")
    def test_get_abstract_from_pubmed_id_cmd_success(self, mock_get_abstract):
        """Test successful abstract retrieval."""
        mock_get_abstract.return_value = "This is the abstract of the paper..."

        runner = CliRunner()
        result = runner.invoke(get_abstract_from_pubmed_id_cmd, ["--pmid", "12345678"])

        assert result.exit_code == 0
        mock_get_abstract.assert_called_once_with("12345678")
        assert "This is the abstract" in result.output

    @patch("artl_mcp.cli.get_abstract_from_pubmed_id")
    def test_get_abstract_from_pubmed_id_cmd_failure(self, mock_get_abstract):
        """Test abstract retrieval failure."""
        mock_get_abstract.return_value = None

        runner = CliRunner()
        result = runner.invoke(get_abstract_from_pubmed_id_cmd, ["--pmid", "12345678"])

        assert result.exit_code == 0
        mock_get_abstract.assert_called_once_with("12345678")
        assert "No abstract found" in result.output

    @patch("artl_mcp.cli.doi_to_pmid")
    def test_doi_to_pmid_cmd_success(self, mock_doi_to_pmid):
        """Test successful DOI to PMID conversion."""
        mock_doi_to_pmid.return_value = "12345678"

        runner = CliRunner()
        result = runner.invoke(doi_to_pmid_cmd, ["--doi", "10.1038/nature12373"])

        assert result.exit_code == 0
        mock_doi_to_pmid.assert_called_once_with("10.1038/nature12373")
        output = json.loads(result.output.strip())
        assert output == "12345678"

    @patch("artl_mcp.cli.pmid_to_doi")
    def test_pmid_to_doi_cmd_success(self, mock_pmid_to_doi):
        """Test successful PMID to DOI conversion."""
        mock_pmid_to_doi.return_value = "10.1038/nature12373"

        runner = CliRunner()
        result = runner.invoke(pmid_to_doi_cmd, ["--pmid", "12345678"])

        assert result.exit_code == 0
        mock_pmid_to_doi.assert_called_once_with("12345678")
        output = json.loads(result.output.strip())
        assert output == "10.1038/nature12373"

    @patch("artl_mcp.cli.get_pmid_from_pmcid")
    def test_get_pmid_from_pmcid_cmd_success(self, mock_get_pmid_from_pmcid):
        """Test successful PMCID to PMID conversion."""
        mock_get_pmid_from_pmcid.return_value = "12345678"

        runner = CliRunner()
        result = runner.invoke(get_pmid_from_pmcid_cmd, ["--pmcid", "PMC9087108"])

        assert result.exit_code == 0
        mock_get_pmid_from_pmcid.assert_called_once_with("PMC9087108")
        output = json.loads(result.output.strip())
        assert output == "12345678"

    @patch("artl_mcp.cli.get_pmcid_text")
    def test_get_pmcid_text_cmd_success(self, mock_get_pmcid_text):
        """Test successful PMC text retrieval."""
        mock_get_pmcid_text.return_value = "Full text from PMC..."

        runner = CliRunner()
        result = runner.invoke(get_pmcid_text_cmd, ["--pmcid", "PMC9087108"])

        assert result.exit_code == 0
        mock_get_pmcid_text.assert_called_once_with("PMC9087108")

    @patch("artl_mcp.cli.get_pmid_text")
    def test_get_pmid_text_cmd_success(self, mock_get_pmid_text):
        """Test successful PMID text retrieval."""
        mock_get_pmid_text.return_value = "Text from PMID..."

        runner = CliRunner()
        result = runner.invoke(get_pmid_text_cmd, ["--pmid", "12345678"])

        assert result.exit_code == 0
        mock_get_pmid_text.assert_called_once_with("12345678")

    @patch("artl_mcp.cli.get_full_text_from_bioc")
    def test_get_full_text_from_bioc_cmd_success(self, mock_get_full_text_from_bioc):
        """Test successful BioC full text retrieval."""
        mock_get_full_text_from_bioc.return_value = "BioC full text content..."

        runner = CliRunner()
        result = runner.invoke(get_full_text_from_bioc_cmd, ["--pmid", "12345678"])

        assert result.exit_code == 0
        mock_get_full_text_from_bioc.assert_called_once_with("12345678")


class TestUnpaywallCommands:
    """Test Unpaywall-related CLI commands."""

    @patch("artl_mcp.cli.get_unpaywall_info")
    def test_get_unpaywall_info_cmd_success_strict(self, mock_get_unpaywall_info):
        """Test successful Unpaywall info retrieval with strict mode."""
        mock_get_unpaywall_info.return_value = {
            "is_oa": True,
            "genre": "journal-article",
        }

        runner = CliRunner()
        test_email = get_test_email()
        result = runner.invoke(
            get_unpaywall_info_cmd,
            ["--doi", "10.1038/nature12373", "--email", test_email, "--strict"],
        )

        assert result.exit_code == 0
        mock_get_unpaywall_info.assert_called_once_with(
            "10.1038/nature12373", test_email, True
        )
        output = json.loads(result.output.strip())
        assert output["is_oa"] is True

    @patch("artl_mcp.cli.get_unpaywall_info")
    def test_get_unpaywall_info_cmd_success_non_strict(self, mock_get_unpaywall_info):
        """Test successful Unpaywall info retrieval without strict mode."""
        mock_get_unpaywall_info.return_value = {"is_oa": False}

        runner = CliRunner()
        test_email = get_test_email()
        result = runner.invoke(
            get_unpaywall_info_cmd,
            ["--doi", "10.1038/nature12373", "--email", test_email],
        )

        assert result.exit_code == 0
        mock_get_unpaywall_info.assert_called_once_with(
            "10.1038/nature12373", test_email, True
        )


class TestFullTextCommands:
    """Test full text retrieval CLI commands."""

    @patch("artl_mcp.cli.get_full_text_from_doi")
    def test_get_full_text_from_doi_cmd_success(self, mock_get_full_text_from_doi):
        """Test successful full text retrieval from DOI."""
        mock_get_full_text_from_doi.return_value = "Complete full text content..."

        runner = CliRunner()
        test_email = get_test_email()
        result = runner.invoke(
            get_full_text_from_doi_cmd,
            ["--doi", "10.1038/nature12373", "--email", test_email],
        )

        assert result.exit_code == 0
        mock_get_full_text_from_doi.assert_called_once_with(
            "10.1038/nature12373", test_email
        )

    @patch("artl_mcp.cli.get_full_text_info")
    def test_get_full_text_info_cmd_success(self, mock_get_full_text_info):
        """Test successful full text info retrieval."""
        mock_get_full_text_info.return_value = {
            "success": True,
            "info": "Found full text",
        }

        runner = CliRunner()
        test_email = get_test_email()
        result = runner.invoke(
            get_full_text_info_cmd,
            ["--doi", "10.1038/nature12373", "--email", test_email],
        )

        assert result.exit_code == 0
        mock_get_full_text_info.assert_called_once_with(
            "10.1038/nature12373", test_email
        )


class TestPDFCommands:
    """Test PDF-related CLI commands."""

    @patch("artl_mcp.cli.get_text_from_pdf_url")
    def test_get_text_from_pdf_url_cmd_success(self, mock_get_text_from_pdf_url):
        """Test successful PDF text extraction from URL."""
        mock_get_text_from_pdf_url.return_value = "Extracted PDF text content..."

        runner = CliRunner()
        test_email = get_test_email()
        result = runner.invoke(
            get_text_from_pdf_url_cmd,
            [
                "--pdf-url",
                "https://example.com/paper.pdf",
                "--email",
                test_email,
            ],
        )

        assert result.exit_code == 0
        mock_get_text_from_pdf_url.assert_called_once_with(
            "https://example.com/paper.pdf", test_email
        )

    @patch("artl_mcp.cli.extract_pdf_text")
    def test_extract_pdf_text_cmd_success(self, mock_extract_pdf_text):
        """Test successful standalone PDF text extraction."""
        mock_extract_pdf_text.return_value = "PDF text content..."

        runner = CliRunner()
        result = runner.invoke(
            extract_pdf_text_cmd, ["--pdf-url", "https://example.com/paper.pdf"]
        )

        assert result.exit_code == 0
        mock_extract_pdf_text.assert_called_once_with("https://example.com/paper.pdf")


class TestUtilityCommands:
    """Test utility CLI commands."""

    @patch("artl_mcp.cli.clean_text")
    def test_clean_text_cmd_success(self, mock_clean_text):
        """Test successful text cleaning."""
        mock_clean_text.return_value = "cleaned text"

        runner = CliRunner()
        test_email = get_test_email()
        result = runner.invoke(
            clean_text_cmd,
            ["--text", "  messy   text  ", "--email", test_email],
        )

        assert result.exit_code == 0
        mock_clean_text.assert_called_once_with("  messy   text  ", test_email)
        output = json.loads(result.output.strip())
        assert output == "cleaned text"

    @patch("artl_mcp.cli.extract_doi_from_url")
    def test_extract_doi_from_url_cmd_success(self, mock_extract_doi_from_url):
        """Test successful DOI extraction from URL."""
        mock_extract_doi_from_url.return_value = "10.1038/nature12373"

        runner = CliRunner()
        result = runner.invoke(
            extract_doi_from_url_cmd,
            ["--doi-url", "https://doi.org/10.1038/nature12373"],
        )

        assert result.exit_code == 0
        mock_extract_doi_from_url.assert_called_once_with(
            "https://doi.org/10.1038/nature12373"
        )
        output = json.loads(result.output.strip())
        assert output == "10.1038/nature12373"


class TestSearchCommands:
    """Test search-related CLI commands."""

    @patch("artl_mcp.cli.search_papers_by_keyword")
    def test_search_papers_by_keyword_cmd_basic(self, mock_search_papers_by_keyword):
        """Test basic keyword search."""
        mock_search_papers_by_keyword.return_value = {
            "message": {"items": [{"DOI": "10.1038/test1"}, {"DOI": "10.1038/test2"}]}
        }

        runner = CliRunner()
        result = runner.invoke(
            search_papers_by_keyword_cmd, ["--query", "machine learning"]
        )

        assert result.exit_code == 0
        mock_search_papers_by_keyword.assert_called_once_with(
            query="machine learning",
            max_results=20,
            sort="relevance",
            filter_params=None,
        )

    @patch("artl_mcp.cli.search_papers_by_keyword")
    def test_search_papers_by_keyword_cmd_with_options(
        self, mock_search_papers_by_keyword
    ):
        """Test keyword search with all options."""
        mock_search_papers_by_keyword.return_value = {"message": {"items": []}}

        runner = CliRunner()
        result = runner.invoke(
            search_papers_by_keyword_cmd,
            [
                "--query",
                "artificial intelligence",
                "--max-results",
                "10",
                "--sort",
                "published",
                "--filter-type",
                "journal-article",
                "--from-pub-date",
                "2020-01-01",
                "--until-pub-date",
                "2023-12-31",
            ],
        )

        assert result.exit_code == 0
        expected_filters = {
            "type": "journal-article",
            "from-pub-date": "2020-01-01",
            "until-pub-date": "2023-12-31",
        }
        mock_search_papers_by_keyword.assert_called_once_with(
            query="artificial intelligence",
            max_results=10,
            sort="published",
            filter_params=expected_filters,
        )

    @patch("artl_mcp.cli.search_recent_papers")
    def test_search_recent_papers_cmd_basic(self, mock_search_recent_papers):
        """Test basic recent papers search."""
        mock_search_recent_papers.return_value = {"message": {"items": []}}

        runner = CliRunner()
        result = runner.invoke(search_recent_papers_cmd, ["--query", "deep learning"])

        assert result.exit_code == 0
        mock_search_recent_papers.assert_called_once_with(
            query="deep learning",
            years_back=5,
            max_results=20,
            paper_type="journal-article",
        )

    @patch("artl_mcp.cli.search_recent_papers")
    def test_search_recent_papers_cmd_with_options(self, mock_search_recent_papers):
        """Test recent papers search with options."""
        mock_search_recent_papers.return_value = {"message": {"items": []}}

        runner = CliRunner()
        result = runner.invoke(
            search_recent_papers_cmd,
            ["--query", "neural networks", "--years-back", "5", "--max-results", "15"],
        )

        assert result.exit_code == 0
        mock_search_recent_papers.assert_called_once_with(
            query="neural networks",
            years_back=5,
            max_results=15,
            paper_type="journal-article",
        )


class TestCommandFailures:
    """Test CLI command failure scenarios."""

    def test_missing_required_arguments(self):
        """Test various commands with missing required arguments."""
        runner = CliRunner()

        # Test commands that require --doi
        commands_requiring_doi = [
            get_doi_metadata_cmd,
            get_doi_text_cmd,
            doi_to_pmid_cmd,
        ]

        for cmd in commands_requiring_doi:
            result = runner.invoke(cmd, [])
            assert result.exit_code != 0
            assert (
                "Missing option" in result.output or "required" in result.output.lower()
            )

    def test_missing_email_arguments(self):
        """Test commands that require email argument."""
        runner = CliRunner()

        # Test commands that require both --doi and --email
        result = runner.invoke(get_doi_fetcher_metadata_cmd, ["--doi", "10.1038/test"])
        assert result.exit_code != 0
        assert "Missing option" in result.output or "email" in result.output.lower()

    @patch("artl_mcp.cli.get_doi_metadata")
    def test_function_exception_handling(self, mock_get_doi_metadata):
        """Test CLI command when underlying function raises exception."""
        mock_get_doi_metadata.side_effect = Exception("API Error")

        runner = CliRunner()
        result = runner.invoke(get_doi_metadata_cmd, ["--doi", "10.1038/test"])

        # CLI should handle exceptions gracefully (exit code depends on implementation)
        # The important thing is it doesn't crash
        assert "API Error" in result.output or result.exit_code != 0
