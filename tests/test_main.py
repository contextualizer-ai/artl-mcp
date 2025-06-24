from unittest.mock import Mock, patch

from artl_mcp.main import get_doi_metadata


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
