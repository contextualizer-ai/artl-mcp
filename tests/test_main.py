import pytest
from unittest.mock import patch, Mock
from click.testing import CliRunner

from allroadstoliterature.main import get_doi_metadata, main


# Test core function with mocks
def test_get_doi_metadata_success_with_mock():
    with patch('habanero.Crossref') as mock_crossref:
        # Setup mock
        mock_instance = Mock()
        mock_crossref.return_value = mock_instance
        mock_instance.works.return_value = {"status": "ok", "data": {"title": "Test Article"}}

        # Call function and assert
        result = get_doi_metadata("10.1234/test.doi")
        assert result == {"status": "ok", "data": {"title": "Test Article"}}


# Test error handling with mocks
def test_get_doi_metadata_exception_with_mock():
    with patch('habanero.Crossref') as mock_crossref:
        # Setup mock to raise exception
        mock_instance = Mock()
        mock_crossref.return_value = mock_instance
        mock_instance.works.side_effect = Exception("API error")

        # Call function and assert
        result = get_doi_metadata("10.1234/test.doi")
        assert result is None


# Simple CLI test without mocks
def test_cli_basic_invocation():
    runner = CliRunner()
    result = runner.invoke(main, ['--doi', '10.1234/test.doi'])
    # Just check it runs without error code
    assert result.exit_code == 0


# CLI test with mocks to verify full functionality
def test_cli_with_mocks():
    with patch('allroadstoliterature.main.get_doi_metadata') as mock_get_metadata:
        mock_get_metadata.return_value = {"sample": "metadata"}

        runner = CliRunner()
        result = runner.invoke(main, ['--doi', '10.1234/test.doi'])

        # Verify the function was called with correct DOI
        mock_get_metadata.assert_called_once_with('10.1234/test.doi')
        assert result.exit_code == 0
        # Verify some expected output
        assert "Retrieving metadata for DOI: 10.1234/test.doi" in result.output


# CLI test for error case
def test_cli_error_case():
    with patch('allroadstoliterature.main.get_doi_metadata') as mock_get_metadata:
        mock_get_metadata.return_value = None

        runner = CliRunner()
        result = runner.invoke(main, ['--doi', '10.1234/test.doi'])

        assert "Failed to retrieve metadata" in result.output
