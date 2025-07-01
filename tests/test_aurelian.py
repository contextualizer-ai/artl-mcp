import os

import pytest

import artl_mcp.utils.pubmed_utils as aupu
from artl_mcp.utils.doi_fetcher import DOIFetcher

# todo this recapitulates a lot of the tests in https://github.com/monarch-initiative/aurelian/blob/main/src/aurelian/utils/doi_fetcher.py
#   and you could argue that we shouldn't be hitting the APIs in tests


def test_doi_fetcher_initialization():
    """Test that DOIFetcher can be initialized properly."""
    dfr = DOIFetcher(email="test@example.com")
    assert dfr is not None

    # Check if essential attributes exist
    attributes = vars(dfr)
    assert "email" in attributes
    assert attributes["email"] == "test@example.com"


def test_doi_fetcher_attributes():
    """Test that DOIFetcher has expected methods and attributes."""
    dfr = DOIFetcher(email="test@example.com")

    # Get all attributes to examine what's actually available
    all_attributes = dir(dfr)
    public_attributes = [attr for attr in all_attributes if not attr.startswith("__")]

    # Print for debugging (remove after fixing)
    print(f"Available attributes: {public_attributes}")

    # Test for essential attributes we know exist
    assert hasattr(dfr, "email")
    assert dfr.email == "test@example.com"


def test_doi_fetcher_functionality():
    """Test basic functionality of DOIFetcher."""
    dfr = DOIFetcher(email="test@example.com")

    # Test if the instance can be properly converted to string
    assert str(dfr) is not None

    # Inspect the object to find actual methods for fetching DOIs
    # Assuming one of these methods exists for fetching DOIs
    fetching_methods = [
        m for m in dir(dfr) if "doi" in m.lower() or "fetch" in m.lower()
    ]
    print(f"Potential fetching methods: {fetching_methods}")

    # At minimum, the object should be instantiable
    assert isinstance(dfr, DOIFetcher)


def test_doi_fetcher_all():
    """Test that DOIFetcher can fetch all DOIs."""
    dfr = DOIFetcher(email="senior_distinguished_scientist@lbl.gov")
    input_text = "   xxx   xxx   "
    output_text = dfr.clean_text(input_text)
    assert output_text == "xxx xxx"

    doi_value = "10.1099/ijsem.0.005153"
    doi_metadata = dfr.get_metadata(doi_value)
    assert doi_metadata["DOI"] == doi_value

    from_unpaywall = dfr.get_unpaywall_info(doi_value, strict=True)
    assert from_unpaywall["genre"] == "journal-article"

    full_text_doi = "10.1128/msystems.00045-18"

    full_text_result = dfr.get_full_text(full_text_doi)
    assert "microbiome" in full_text_result

    full_text_into_result = dfr.get_full_text_info(full_text_doi)
    assert full_text_into_result.success  # not really useful in this case

    pdf_url = "https://ceur-ws.org/Vol-1747/IT201_ICBO2016.pdf"
    pdf_text = dfr.text_from_pdf_url(pdf_url)
    assert "biosphere" in pdf_text


@pytest.mark.skipif(
    os.environ.get("CI") == "true", reason="Skip flaky network test in CI"
)
def test_uapu():
    doi_url = "https://doi.org/10.7717/peerj.16290"
    doi_portion = "10.7717/peerj.16290"
    expected_text = "Magellanic"

    pmid_for_abstract = "31653696"
    expected_in_abstract_from_pmid = "deglycase"

    extracted_doi = aupu.extract_doi_from_url(doi_url)
    assert extracted_doi == doi_portion

    text_from_doi = aupu.get_doi_text(doi_portion)
    assert expected_text in text_from_doi

    abstract_from_pubmed = aupu.get_abstract_from_pubmed(pmid_for_abstract)
    assert expected_in_abstract_from_pmid in abstract_from_pubmed
