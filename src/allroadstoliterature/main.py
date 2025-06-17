import pprint
from typing import Dict, Any, Optional

import click
import habanero


def get_doi_metadata(doi: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve metadata for a scientific article using its DOI.

    Args:
        doi: The Digital Object Identifier of the article.

    Returns:
        A dictionary containing the article metadata if successful, None otherwise.
    """
    cr = habanero.Crossref()
    try:
        result = cr.works(ids=doi)
        return result
    except Exception as e:
        print(f"Error retrieving metadata for DOI {doi}: {e}")
        return None


@click.command()
@click.option('--doi', '-d', required=True, help='DOI of the article to retrieve metadata for')
def main(doi: str) -> None:
    """Retrieve and display metadata for a scientific article using its DOI."""
    click.echo(f"Retrieving metadata for DOI: {doi}")

    metadata = get_doi_metadata(doi)

    if metadata:
        pprint.pprint(metadata)
    else:
        click.echo("Failed to retrieve metadata.")


if __name__ == "__main__":
    main()
