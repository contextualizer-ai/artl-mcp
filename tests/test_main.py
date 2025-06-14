import pytest
from unittest.mock import patch, Mock

# Fix the import path
from src.allroadstoliterature.main import get_doi_metadata, main

def test_get_doi_metadata_success():
    with patch('habanero.Crossref') as mock_crossref:
        # Setup mock
        mock_instance = Mock()
        mock_crossref.return_value = mock_instance
        mock_instance.works.return_value = {"status": "ok", "data": {"title": "Test Article"}}

        # Call function and assert
        result = get_doi_metadata("10.1234/test.doi")
        assert result == {"status": "ok", "data": {"title": "Test Article"}}

def test_main_function():
    with patch('src.allroadstoliterature.main.get_doi_metadata') as mock_get_metadata:
        with patch('src.allroadstoliterature.main.pprint.pprint') as mock_pprint:
            # Setup mock
            mock_get_metadata.return_value = {"sample": "metadata"}

            # Call function
            main()

            # Assertions
            mock_get_metadata.assert_called_once()
            mock_pprint.assert_called_once()
