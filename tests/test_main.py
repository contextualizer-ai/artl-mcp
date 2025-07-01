from unittest.mock import Mock, patch

from artl_mcp.tools import get_doi_metadata, search_pubmed_for_pmids


# Test core function with mocks
def test_get_doi_metadata_success_with_mock():
    with patch("habanero.Crossref") as mock_crossref:
        # Setup mock
        mock_instance = Mock()
        mock_crossref.return_value = mock_instance
        mock_instance.works.return_value = {
            "status": "ok",
            "data": {"title": "Test Article"},
        }

        # Call function and assert
        result = get_doi_metadata("10.1234/test.doi")
        assert result == {"status": "ok", "data": {"title": "Test Article"}}


# Test error handling with mocks
def test_get_doi_metadata_exception_with_mock():
    with patch("habanero.Crossref") as mock_crossref:
        # Setup mock to raise exception
        mock_instance = Mock()
        mock_crossref.return_value = mock_instance
        mock_instance.works.side_effect = Exception("API error")

        # Call function and assert
        result = get_doi_metadata("10.1234/test.doi")
        assert result is None


# Test PubMed search function with mocks
def test_search_pubmed_for_pmids_success_with_mock():
    with patch("requests.get") as mock_get:
        # Setup mock response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "esearchresult": {
                "idlist": ["12345678", "87654321", "11111111"],
                "count": "744"
            }
        }
        mock_get.return_value = mock_response

        # Call function and assert
        result = search_pubmed_for_pmids("alzheimer disease")
        expected = {
            "pmids": ["12345678", "87654321", "11111111"],
            "total_count": 744,
            "returned_count": 3,
            "query": "alzheimer disease",
            "max_results": 20
        }
        assert result == expected
        
        # Verify the API was called with correct parameters
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "pubmed" in call_args.kwargs["url"]
        assert "alzheimer disease" in call_args.kwargs["params"]["term"]


def test_search_pubmed_for_pmids_no_results_with_mock():
    with patch("requests.get") as mock_get:
        # Setup mock response with no results
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "esearchresult": {
                "idlist": [],
                "count": "0"
            }
        }
        mock_get.return_value = mock_response

        # Call function and assert
        result = search_pubmed_for_pmids("nonexistent query")
        expected = {
            "pmids": [],
            "total_count": 0,
            "returned_count": 0,
            "query": "nonexistent query",
            "max_results": 20
        }
        assert result == expected


def test_search_pubmed_for_pmids_exception_with_mock():
    with patch("requests.get") as mock_get:
        # Setup mock to raise exception
        mock_get.side_effect = Exception("Network error")

        # Call function and assert
        result = search_pubmed_for_pmids("alzheimer disease")
        assert result is None
