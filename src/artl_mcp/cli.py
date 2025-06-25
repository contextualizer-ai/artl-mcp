"""Command-line interface wrappers for all artl_mcp tools."""

import json
from typing import Any

import click

from artl_mcp.tools import (
    clean_text,
    doi_to_pmid,
    extract_doi_from_url,
    extract_pdf_text,
    get_abstract_from_pubmed_id,
    get_doi_fetcher_metadata,
    get_doi_metadata,
    get_doi_text,
    get_full_text_from_bioc,
    get_full_text_from_doi,
    get_full_text_info,
    get_pmcid_text,
    get_pmid_from_pmcid,
    get_pmid_text,
    get_text_from_pdf_url,
    get_unpaywall_info,
    pmid_to_doi,
)


def output_result(result: Any) -> None:
    """Output result as JSON to stdout."""
    if result is None:
        click.echo(json.dumps({"error": "No result returned"}))
    else:
        click.echo(json.dumps(result, indent=2))


@click.command()
@click.option("--doi", required=True, help="Digital Object Identifier")
def cli_get_doi_metadata(doi: str) -> None:
    """Retrieve metadata for a scientific article using its DOI."""
    result = get_doi_metadata(doi)
    output_result(result)


@click.command()
@click.option("--pmid", required=True, help="PubMed ID")
def cli_get_abstract_from_pubmed_id(pmid: str) -> None:
    """Get abstract text from a PubMed ID."""
    result = get_abstract_from_pubmed_id(pmid)
    output_result(result)


@click.command()
@click.option("--doi", required=True, help="Digital Object Identifier")
@click.option("--email", required=True, help="Email address for API requests")
def cli_get_doi_fetcher_metadata(doi: str, email: str) -> None:
    """Get metadata for a DOI using DOIFetcher."""
    result = get_doi_fetcher_metadata(doi, email)
    output_result(result)


@click.command()
@click.option("--doi", required=True, help="Digital Object Identifier")
@click.option("--email", required=True, help="Email address for API requests")
@click.option("--strict/--no-strict", default=True, help="Use strict mode for Unpaywall queries")
def cli_get_unpaywall_info(doi: str, email: str, strict: bool) -> None:
    """Get Unpaywall information for a DOI to find open access versions."""
    result = get_unpaywall_info(doi, email, strict)
    output_result(result)


@click.command()
@click.option("--doi", required=True, help="Digital Object Identifier")
@click.option("--email", required=True, help="Email address for API requests")
def cli_get_full_text_from_doi(doi: str, email: str) -> None:
    """Get full text content from a DOI."""
    result = get_full_text_from_doi(doi, email)
    output_result(result)


@click.command()
@click.option("--doi", required=True, help="Digital Object Identifier")
@click.option("--email", required=True, help="Email address for API requests")
def cli_get_full_text_info(doi: str, email: str) -> None:
    """Get full text information from a DOI."""
    result = get_full_text_info(doi, email)
    output_result(result)


@click.command()
@click.option("--pdf-url", required=True, help="URL of the PDF to extract text from")
@click.option("--email", required=True, help="Email address for API requests")
def cli_get_text_from_pdf_url(pdf_url: str, email: str) -> None:
    """Extract text from a PDF URL using DOIFetcher."""
    result = get_text_from_pdf_url(pdf_url, email)
    output_result(result)


@click.command()
@click.option("--pdf-url", required=True, help="URL of the PDF to extract text from")
def cli_extract_pdf_text(pdf_url: str) -> None:
    """Extract text from a PDF URL using the standalone pdf_fetcher."""
    result = extract_pdf_text(pdf_url)
    output_result(result)


@click.command()
@click.option("--text", required=True, help="Text to clean")
@click.option("--email", required=True, help="Email address for API requests")
def cli_clean_text(text: str, email: str) -> None:
    """Clean text using DOIFetcher's text cleaning functionality."""
    result = clean_text(text, email)
    output_result(result)


@click.command()
@click.option("--doi-url", required=True, help="URL containing a DOI")
def cli_extract_doi_from_url(doi_url: str) -> None:
    """Extract DOI from a DOI URL."""
    result = extract_doi_from_url(doi_url)
    output_result(result)


@click.command()
@click.option("--doi", required=True, help="Digital Object Identifier")
def cli_doi_to_pmid(doi: str) -> None:
    """Convert DOI to PubMed ID."""
    result = doi_to_pmid(doi)
    output_result(result)


@click.command()
@click.option("--pmid", required=True, help="PubMed ID")
def cli_pmid_to_doi(pmid: str) -> None:
    """Convert PubMed ID to DOI."""
    result = pmid_to_doi(pmid)
    output_result(result)


@click.command()
@click.option("--doi", required=True, help="Digital Object Identifier")
def cli_get_doi_text(doi: str) -> None:
    """Get full text from a DOI."""
    result = get_doi_text(doi)
    output_result(result)


@click.command()
@click.option("--pmcid", required=True, help="PMC ID (e.g., 'PMC1234567')")
def cli_get_pmid_from_pmcid(pmcid: str) -> None:
    """Convert PMC ID to PubMed ID."""
    result = get_pmid_from_pmcid(pmcid)
    output_result(result)


@click.command()
@click.option("--pmcid", required=True, help="PMC ID (e.g., 'PMC1234567')")
def cli_get_pmcid_text(pmcid: str) -> None:
    """Get full text from a PMC ID."""
    result = get_pmcid_text(pmcid)
    output_result(result)


@click.command()
@click.option("--pmid", required=True, help="PubMed ID")
def cli_get_pmid_text(pmid: str) -> None:
    """Get full text from a PubMed ID."""
    result = get_pmid_text(pmid)
    output_result(result)


@click.command()
@click.option("--pmid", required=True, help="PubMed ID")
def cli_get_full_text_from_bioc(pmid: str) -> None:
    """Get full text from BioC format for a PubMed ID."""
    result = get_full_text_from_bioc(pmid)
    output_result(result)