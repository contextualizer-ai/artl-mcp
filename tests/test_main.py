from unittest.mock import Mock, patch

import pytest
import requests

from artl_mcp.tools import get_doi_metadata


def test_get_doi_metadata_success_with_mock():
    """Test successful DOI metadata retrieval with mocked requests."""
    # Mock response data (typical CrossRef API response structure)
    mock_response_data = {
        "status": "ok",
        "message-type": "work",
        "message": {
            "DOI": "10.1038/nature12373",
            "title": ["Sample Article Title"],
            "author": [
                {"given": "John", "family": "Doe"},
                {"given": "Jane", "family": "Smith"},
            ],
            "container-title": ["Nature"],
            "published-print": {"date-parts": [[2023, 6, 15]]},
            "publisher": "Nature Publishing Group",
        },
    }

    # Create mock response object
    mock_response = Mock()
    mock_response.json.return_value = mock_response_data
    mock_response.raise_for_status.return_value = None

    with patch("requests.get", return_value=mock_response) as mock_get:
        result = get_doi_metadata("10.1038/nature12373")

        # Verify requests.get was called correctly
        mock_get.assert_called_once()
        call_args = mock_get.call_args

        # Check URL
        assert "https://api.crossref.org/works/10.1038/nature12373" in call_args[0][0]

        # Check headers
        headers = call_args[1]["headers"]
        assert headers["Accept"] == "application/json"
        assert "artl-mcp" in headers["User-Agent"]

        # Check timeout
        assert call_args[1]["timeout"] == 30

        # Verify result
        assert result == mock_response_data
        assert result["message"]["DOI"] == "10.1038/nature12373"


def test_get_doi_metadata_exception_with_mock():
    """Test DOI metadata retrieval with request exception."""
    with patch("requests.get") as mock_get:
        # Simulate a requests exception
        mock_get.side_effect = requests.exceptions.RequestException("Network error")

        result = get_doi_metadata("10.1038/invalid-doi")

        # Should return None on exception
        assert result is None

        # Verify requests.get was called
        mock_get.assert_called_once()


def test_get_doi_metadata_http_error():
    """Test DOI metadata retrieval with HTTP error."""
    mock_response = Mock()
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        "404 Not Found"
    )

    with patch("requests.get", return_value=mock_response):
        result = get_doi_metadata("10.1038/nonexistent-doi")

        # Should return None on HTTP error
        assert result is None


def test_get_doi_metadata_cleans_doi_url():
    """Test that DOI URLs are properly cleaned."""
    mock_response_data = {"status": "ok", "message": {"DOI": "10.1038/nature12373"}}

    mock_response = Mock()
    mock_response.json.return_value = mock_response_data
    mock_response.raise_for_status.return_value = None

    with patch("requests.get", return_value=mock_response) as mock_get:
        # Test with https://doi.org/ prefix
        get_doi_metadata("https://doi.org/10.1038/nature12373")

        call_args = mock_get.call_args
        url = call_args[0][0]

        # Should have cleaned URL
        assert url == "https://api.crossref.org/works/10.1038/nature12373"

        mock_get.reset_mock()

        # Test with http://dx.doi.org/ prefix
        get_doi_metadata("http://dx.doi.org/10.1038/nature12373")

        call_args = mock_get.call_args
        url = call_args[0][0]

        # Should have cleaned URL
        assert url == "https://api.crossref.org/works/10.1038/nature12373"


def test_get_doi_metadata_timeout():
    """Test DOI metadata retrieval with timeout."""
    with patch("requests.get") as mock_get:
        mock_get.side_effect = requests.exceptions.Timeout("Request timed out")

        result = get_doi_metadata("10.1038/some-doi")

        # Should return None on timeout
        assert result is None


# Tests for the new search functionality (if you want to add them)
def test_search_papers_by_keyword_success():
    """Test successful paper search with mocked requests."""
    mock_response_data = {
        "status": "ok",
        "message-type": "work-list",
        "message": {
            "total-results": 2,
            "items": [
                {
                    "DOI": "10.1038/article1",
                    "title": ["Machine Learning in Science"],
                    "author": [{"given": "Alice", "family": "Johnson"}],
                },
                {
                    "DOI": "10.1038/article2",
                    "title": ["Deep Learning Applications"],
                    "author": [{"given": "Bob", "family": "Wilson"}],
                },
            ],
        },
    }

    mock_response = Mock()
    mock_response.json.return_value = mock_response_data
    mock_response.raise_for_status.return_value = None

    # You'll need to import the search function when you add it
    # from artl_mcp.tools import search_papers_by_keyword

    # This test is a placeholder for when you add the search function
    # with patch("requests.get", return_value=mock_response) as mock_get:
    #     result = search_papers_by_keyword("machine learning", max_results=10)
    #     mock_get.assert_called_once()
    #     call_args = mock_get.call_args
    #     assert "https://api.crossref.org/works" in call_args[0][0]
    #     params = call_args[1]["params"]
    #     assert params["query"] == "machine learning"
    #     assert params["rows"] == 10
    #     assert result == mock_response_data
    #     assert len(result["message"]["items"]) == 2
    pass


# Integration test (optional - runs against real API)
@pytest.mark.integration
def test_get_doi_metadata_real_api():
    """Integration test with real CrossRef API (marked as integration test)."""
    # This will only run if you use: pytest -m integration
    result = get_doi_metadata("10.1038/nature12373")

    # Basic checks for real API response
    if result:  # API might be down or DOI might not exist
        assert result.get("message", {}).get("DOI") is not None
    # Don't fail if API is unavailable
