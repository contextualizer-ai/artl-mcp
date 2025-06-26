"""Command-line interface wrappers for all artl_mcp tools."""

import json
from typing import Any

import click

from artl_mcp._version import __version__
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
    search_papers_by_keyword,
    search_recent_papers,
)


def output_result(result: Any) -> None:
    """Output result as JSON to stdout."""
    if result is None:
        click.echo(json.dumps({"error": "No result returned"}))
    else:
        click.echo(json.dumps(result, indent=2))


@click.group()
@click.version_option(version=__version__)
def cli():
    """All Roads to Literature - CLI tools for scientific literature access."""
    pass


@cli.command("get-doi-metadata")
@click.option("--doi", required=True, help="Digital Object Identifier")
def get_doi_metadata_cmd(doi: str) -> None:
    """Retrieve metadata for a scientific article using its DOI."""
    result = get_doi_metadata(doi)
    output_result(result)


@cli.command("get-abstract-from-pubmed-id")
@click.option("--pmid", required=True, help="PubMed ID")
def get_abstract_from_pubmed_id_cmd(pmid: str) -> None:
    """Get abstract text from a PubMed ID."""
    result = get_abstract_from_pubmed_id(pmid)
    if result:
        click.echo(result)
    else:
        click.echo("No abstract found", err=True)


@cli.command("get-doi-fetcher-metadata")
@click.option("--doi", required=True, help="Digital Object Identifier")
@click.option("--email", required=True, help="Email address for API requests")
def get_doi_fetcher_metadata_cmd(doi: str, email: str) -> None:
    """Get metadata for a DOI using DOIFetcher."""
    result = get_doi_fetcher_metadata(doi, email)
    output_result(result)


@cli.command("get-unpaywall-info")
@click.option("--doi", required=True, help="Digital Object Identifier")
@click.option("--email", required=True, help="Email address for API requests")
@click.option(
    "--strict/--no-strict", default=True, help="Use strict mode for Unpaywall queries"
)
def get_unpaywall_info_cmd(doi: str, email: str, strict: bool) -> None:
    """Get Unpaywall information for a DOI to find open access versions."""
    result = get_unpaywall_info(doi, email, strict)
    output_result(result)


@cli.command("get-full-text-from-doi")
@click.option("--doi", required=True, help="Digital Object Identifier")
@click.option("--email", required=True, help="Email address for API requests")
def get_full_text_from_doi_cmd(doi: str, email: str) -> None:
    """Get full text content from a DOI."""
    result = get_full_text_from_doi(doi, email)
    output_result(result)


@cli.command("get-full-text-info")
@click.option("--doi", required=True, help="Digital Object Identifier")
@click.option("--email", required=True, help="Email address for API requests")
def get_full_text_info_cmd(doi: str, email: str) -> None:
    """Get full text information from a DOI."""
    result = get_full_text_info(doi, email)
    output_result(result)


@cli.command("get-text-from-pdf-url")
@click.option("--pdf-url", required=True, help="URL of the PDF to extract text from")
@click.option("--email", required=True, help="Email address for API requests")
def get_text_from_pdf_url_cmd(pdf_url: str, email: str) -> None:
    """Extract text from a PDF URL using DOIFetcher."""
    result = get_text_from_pdf_url(pdf_url, email)
    output_result(result)


@cli.command("extract-pdf-text")
@click.option("--pdf-url", required=True, help="URL of the PDF to extract text from")
def extract_pdf_text_cmd(pdf_url: str) -> None:
    """Extract text from a PDF URL using the standalone pdf_fetcher."""
    result = extract_pdf_text(pdf_url)
    output_result(result)


@cli.command("clean-text")
@click.option("--text", required=True, help="Text to clean")
@click.option("--email", required=True, help="Email address for API requests")
def clean_text_cmd(text: str, email: str) -> None:
    """Clean text using DOIFetcher's text cleaning functionality."""
    result = clean_text(text, email)
    output_result(result)


@cli.command("extract-doi-from-url")
@click.option("--doi-url", required=True, help="URL containing a DOI")
def extract_doi_from_url_cmd(doi_url: str) -> None:
    """Extract DOI from a DOI URL."""
    result = extract_doi_from_url(doi_url)
    output_result(result)


@cli.command("doi-to-pmid")
@click.option("--doi", required=True, help="Digital Object Identifier")
def doi_to_pmid_cmd(doi: str) -> None:
    """Convert DOI to PubMed ID."""
    result = doi_to_pmid(doi)
    output_result(result)


@cli.command("pmid-to-doi")
@click.option("--pmid", required=True, help="PubMed ID")
def pmid_to_doi_cmd(pmid: str) -> None:
    """Convert PubMed ID to DOI."""
    result = pmid_to_doi(pmid)
    output_result(result)


@cli.command("get-doi-text")
@click.option("--doi", required=True, help="Digital Object Identifier")
def get_doi_text_cmd(doi: str) -> None:
    """Get full text from a DOI."""
    result = get_doi_text(doi)
    output_result(result)


@cli.command("get-pmid-from-pmcid")
@click.option("--pmcid", required=True, help="PMC ID (e.g., 'PMC1234567')")
def get_pmid_from_pmcid_cmd(pmcid: str) -> None:
    """Convert PMC ID to PubMed ID."""
    result = get_pmid_from_pmcid(pmcid)
    output_result(result)


@cli.command("get-pmcid-text")
@click.option("--pmcid", required=True, help="PMC ID (e.g., 'PMC1234567')")
def get_pmcid_text_cmd(pmcid: str) -> None:
    """Get full text from a PMC ID."""
    result = get_pmcid_text(pmcid)
    output_result(result)


@cli.command("get-pmid-text")
@click.option("--pmid", required=True, help="PubMed ID")
def get_pmid_text_cmd(pmid: str) -> None:
    """Get full text from a PubMed ID."""
    result = get_pmid_text(pmid)
    output_result(result)


@cli.command("get-full-text-from-bioc")
@click.option("--pmid", required=True, help="PubMed ID")
def get_full_text_from_bioc_cmd(pmid: str) -> None:
    """Get full text from BioC format for a PubMed ID."""
    result = get_full_text_from_bioc(pmid)
    output_result(result)


@cli.command("search-papers-by-keyword")
@click.option("--query", required=True, help="Search terms/keywords")
@click.option(
    "--max-results", default=20, help="Maximum number of results (default 20, max 1000)"
)
@click.option(
    "--sort",
    default="relevance",
    help="Sort order: relevance, published, created, updated, is-referenced-by-count",
)
@click.option(
    "--filter-type", help="Filter by publication type (e.g., journal-article)"
)
@click.option("--from-pub-date", help="Filter from publication date (YYYY-MM-DD)")
@click.option("--until-pub-date", help="Filter until publication date (YYYY-MM-DD)")
def search_papers_by_keyword_cmd(
    query: str,
    max_results: int,
    sort: str,
    filter_type: str,
    from_pub_date: str,
    until_pub_date: str,
) -> None:
    """Search for scientific papers using keywords."""
    filter_params = {}
    if filter_type:
        filter_params["type"] = filter_type
    if from_pub_date:
        filter_params["from-pub-date"] = from_pub_date
    if until_pub_date:
        filter_params["until-pub-date"] = until_pub_date

    result = search_papers_by_keyword(
        query=query,
        max_results=max_results,
        sort=sort,
        filter_params=filter_params if filter_params else None,
    )
    output_result(result)


@cli.command("search-recent-papers")
@click.option("--query", required=True, help="Search terms")
@click.option(
    "--years-back", default=5, help="How many years back to search (default 5)"
)
@click.option("--max-results", default=20, help="Maximum number of results")
@click.option(
    "--paper-type",
    default="journal-article",
    help="Type of publication (default journal-article)",
)
def search_recent_papers_cmd(
    query: str, years_back: int, max_results: int, paper_type: str
) -> None:
    """Search for recent papers (convenience function)."""
    result = search_recent_papers(
        query=query,
        years_back=years_back,
        max_results=max_results,
        paper_type=paper_type,
    )
    output_result(result)
