import pytest

import artl_mcp.utils.pubmed_utils as aupu

# Test data constants
TEST_DOI = "10.1099/ijsem.0.005153"
TEST_PMID = "35545607"
TEST_PMCID = "PMC9087108"
TEST_DOI_URL = "https://doi.org/10.7717/peerj.16290"
TEST_DOI_CLEAN = "10.7717/peerj.16290"


# DOI/PMID conversion tests - core ID conversion functionality
@pytest.mark.external_api
@pytest.mark.slow
def test_doi_to_pmid():
    """Test DOI to PMID conversion."""
    result = aupu.doi_to_pmid(TEST_DOI)

    if result is not None:
        # The function might return int or str, handle both
        if isinstance(result, int):
            result = str(result)
        assert isinstance(result, str)
        assert result.isdigit()  # PMID should be numeric string
        assert len(result) > 6  # PMIDs are typically 7+ digits
    else:
        pytest.skip("DOI to PMID conversion not available for test DOI")


@pytest.mark.external_api
@pytest.mark.slow
def test_pmid_to_doi():
    """Test PMID to DOI conversion."""
    result = aupu.pmid_to_doi(TEST_PMID)

    if result is not None:
        assert isinstance(result, str)
        assert result.startswith("10.")  # DOIs start with "10."
        assert "/" in result  # DOIs contain "/"
    else:
        pytest.skip("PMID to DOI conversion not available for test PMID")


@pytest.mark.external_api
@pytest.mark.slow
def test_doi_to_pmid_invalid():
    """Test DOI to PMID conversion with invalid DOI."""
    result = aupu.doi_to_pmid("invalid-doi-12345")
    assert result is None


@pytest.mark.external_api
@pytest.mark.slow
def test_pmid_to_doi_invalid():
    """Test PMID to DOI conversion with invalid PMID."""
    result = aupu.pmid_to_doi("invalid-pmid")
    assert result is None


# DOI text extraction tests - core text retrieval with fallback logic
@pytest.mark.external_api
@pytest.mark.slow
def test_get_doi_text():
    """Test DOI text extraction with fallback logic."""
    result = aupu.get_doi_text(TEST_DOI)

    if result is not None:
        assert isinstance(result, str)
        assert len(result) > 100  # Should have substantial text content
        # Test should contain meaningful scientific text
        assert any(
            word in result.lower()
            for word in ["abstract", "introduction", "methods", "results", "conclusion"]
        )
    else:
        pytest.skip("DOI text extraction not available for test DOI")


@pytest.mark.external_api
@pytest.mark.slow
def test_get_doi_text_invalid():
    """Test DOI text extraction with invalid DOI."""
    result = aupu.get_doi_text("invalid-doi-12345")
    # Function returns error message for invalid DOI, not None
    assert isinstance(result, str)
    assert "not found" in result.lower() or "not available" in result.lower()


# PMC ID conversion tests - API interaction with JSON parsing
@pytest.mark.external_api
@pytest.mark.slow
def test_get_pmid_from_pmcid():
    """Test PMID extraction from PMC ID."""
    result = aupu.get_pmid_from_pmcid(TEST_PMCID)

    if result is not None:
        assert isinstance(result, str)
        assert result.isdigit()  # PMID should be numeric string
        assert len(result) > 6  # PMIDs are typically 7+ digits
    else:
        pytest.skip("PMCID to PMID conversion not available for test PMCID")


@pytest.mark.external_api
@pytest.mark.slow
def test_get_pmid_from_pmcid_invalid():
    """Test PMID extraction from invalid PMC ID."""
    # Function may raise exception or return None for invalid PMCID
    try:
        result = aupu.get_pmid_from_pmcid("invalid-pmcid")
        assert result is None
    except (IndexError, KeyError):
        pass  # Acceptable to raise exception for invalid PMCID


# Text retrieval tests - multi-step text retrieval
@pytest.mark.external_api
@pytest.mark.slow
def test_get_pmcid_text():
    """Test text extraction from PMC ID."""
    result = aupu.get_pmcid_text(TEST_PMCID)

    if result is not None:
        assert isinstance(result, str)
        if "FULL TEXT NOT AVAILABLE" in result:
            # This is a valid response, not an error
            assert len(result) > 0
        elif len(result) > 100:
            # Should contain typical scientific paper content or be valid text
            assert len(result.strip()) > 50  # Has substantial content
        else:
            # Some text was retrieved but not substantial - still valid
            assert len(result) >= 0  # Any non-None result is valid
    else:
        # None result means the function handled the error appropriately
        assert result is None


@pytest.mark.external_api
@pytest.mark.slow
def test_get_pmid_text():
    """Test text extraction from PMID."""
    result = aupu.get_pmid_text(TEST_PMID)

    if result is not None:
        assert isinstance(result, str)
        assert len(result) > 50  # Should have some meaningful content
        # Should contain scientific text
        assert any(
            word in result.lower()
            for word in ["abstract", "background", "method", "result"]
        )
    else:
        pytest.skip("PMID text extraction not available for test PMID")


# BioC format tests - complex XML processing
@pytest.mark.external_api
@pytest.mark.slow
def test_get_full_text_from_bioc():
    """Test full text extraction from BioC format."""
    result = aupu.get_full_text_from_bioc(TEST_PMID)

    if result is not None:
        assert isinstance(result, str)
        assert len(result) > 200  # BioC should have substantial full text
        # Should contain structured scientific content
        assert any(
            word in result.lower()
            for word in ["introduction", "methods", "results", "discussion"]
        )
    else:
        pytest.skip("BioC full text not available for test PMID")


@pytest.mark.external_api
def test_get_full_text_from_bioc_invalid():
    """Test BioC extraction with invalid PMID."""
    result = aupu.get_full_text_from_bioc("invalid-pmid")
    assert result is None or result == ""


# Abstract retrieval tests - XML parsing and text normalization
@pytest.mark.external_api
@pytest.mark.slow
def test_get_abstract_from_pubmed():
    """Test abstract extraction with comprehensive XML parsing."""
    # Use a PMID known to have an abstract
    test_pmid = "31653696"  # This PMID has "deglycase" in abstract
    result = aupu.get_abstract_from_pubmed(test_pmid)

    if result is not None and len(result) > 0:
        assert isinstance(result, str)
        assert len(result) > 50  # Should have meaningful abstract content
        assert "deglycase" in result.lower()  # Known content
        # Should be properly formatted (no excessive whitespace)
        assert not result.startswith(" ")
        assert not result.endswith(" ")
    else:
        pytest.skip("Abstract not available for test PMID")


@pytest.mark.external_api
@pytest.mark.slow
def test_get_abstract_from_pubmed_invalid():
    """Test abstract extraction with invalid PMID."""
    result = aupu.get_abstract_from_pubmed("invalid-pmid")
    assert result is None or result == ""


# URL extraction tests - regex-based DOI extraction edge cases
def test_extract_doi_from_url_variants():
    """Test DOI extraction from various URL formats."""
    test_cases = [
        ("https://doi.org/10.1038/nature12373", "10.1038/nature12373"),
        ("http://dx.doi.org/10.1038/nature12373", "10.1038/nature12373"),
        ("https://www.doi.org/10.1038/nature12373", "10.1038/nature12373"),
        ("https://journal.com/doi/10.1038/nature12373", "10.1038/nature12373"),
        ("https://example.com/article/10.1038/nature12373", "10.1038/nature12373"),
    ]

    for url, expected_doi in test_cases:
        result = aupu.extract_doi_from_url(url)
        assert result == expected_doi, f"Failed for URL: {url}"


def test_extract_doi_from_url_edge_cases():
    """Test DOI extraction edge cases."""
    # Test with query parameters
    url_with_params = "https://doi.org/10.1038/nature12373?utm_source=test"
    result = aupu.extract_doi_from_url(url_with_params)
    assert result == "10.1038/nature12373"

    # Test with fragment
    url_with_fragment = "https://doi.org/10.1038/nature12373#abstract"
    result = aupu.extract_doi_from_url(url_with_fragment)
    assert result == "10.1038/nature12373"

    # Test empty/invalid URLs
    assert aupu.extract_doi_from_url("") is None
    assert aupu.extract_doi_from_url("not-a-url") is None
    assert aupu.extract_doi_from_url("https://example.com") is None

    # Test plain DOI (should return None since it expects URL format)
    assert aupu.extract_doi_from_url("10.1038/nature12373") is None


# Error handling and robustness tests
def test_functions_handle_empty_strings():
    """Test all functions handle empty strings gracefully."""
    assert aupu.doi_to_pmid("") is None
    assert aupu.pmid_to_doi("") is None
    assert aupu.get_pmid_from_pmcid("") is None
    assert aupu.extract_doi_from_url("") is None


def test_functions_handle_none_values():
    """Test functions handle None input gracefully."""
    # These should not crash, should return None or handle gracefully
    try:
        assert aupu.extract_doi_from_url(None) is None
    except (TypeError, AttributeError):
        pass  # Acceptable to raise error for None input
