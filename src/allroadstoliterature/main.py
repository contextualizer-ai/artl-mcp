import pprint
from typing import Dict, Any, Optional

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


def main() -> None:
    """
    Main function to demonstrate the retrieval of DOI metadata.

    Retrieves and prints metadata for an example DOI.
    """
    # Example usage
    doi = "10.1038/nrg3564"  # Example DOI
    metadata = get_doi_metadata(doi)
    pprint.pprint(metadata)


if __name__ == "__main__":
    main()
