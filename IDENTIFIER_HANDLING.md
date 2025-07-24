# Identifier Handling in ARTL MCP

This document provides comprehensive guidance on how ARTL MCP handles scientific literature identifiers, including supported formats, conversion capabilities, and best practices.

## Overview

ARTL MCP supports three main types of scientific literature identifiers:
- **DOI** (Digital Object Identifier)
- **PMID** (PubMed ID) 
- **PMCID** (PubMed Central ID)

All tools in ARTL MCP are designed to accept multiple input formats for each identifier type and automatically normalize them to standard formats.

## Supported Identifier Formats

### DOI (Digital Object Identifier)

DOIs can be provided in multiple formats:

| Format | Example | Description |
|--------|---------|-------------|
| **Raw DOI** | `10.1038/nature12373` | Standard DOI format (preferred) |
| **CURIE** | `doi:10.1038/nature12373` | Compact URI format |
| **URL (HTTPS)** | `https://doi.org/10.1038/nature12373` | Standard DOI URL |
| **URL (HTTP)** | `http://dx.doi.org/10.1038/nature12373` | Legacy DOI URL |
| **URL (with query params)** | `https://doi.org/10.1038/nature12373?utm_source=google` | URL with parameters |

**Output Format**: All DOI functions return raw DOI format (`10.1038/nature12373`)

### PMID (PubMed ID)

PMIDs can be provided in multiple formats:

| Format | Example | Description |
|--------|---------|-------------|
| **Raw PMID** | `23851394` | Numeric string (preferred) |
| **Prefixed** | `PMID:23851394` | With PMID prefix |
| **Colon-separated** | `pmid:23851394` | Lowercase with colon |
| **Integer** | `23851394` | Numeric integer (auto-converted) |

**Output Format**: All PMID functions return raw PMID format (`23851394`)

### PMCID (PubMed Central ID)

PMCIDs can be provided in multiple formats:

| Format | Example | Description |
|--------|---------|-------------|
| **Full PMCID** | `PMC3737249` | Standard format with PMC prefix (preferred) |
| **Numeric only** | `3737249` | Numeric part only |
| **Prefixed** | `PMC:3737249` | With colon separator |
| **Colon-separated** | `pmcid:PMC3737249` | Lowercase prefix with colon |

**Output Format**: All PMCID functions return full PMCID format (`PMC3737249`)

## Identifier Validation

Use the `validate_identifier()` function to check if an identifier is properly formatted:

```python
from artl_mcp.tools import validate_identifier

# Validate any identifier (auto-detects type)
assert validate_identifier("10.1038/nature12373") == True
assert validate_identifier("invalid-doi") == False

# Validate with expected type
assert validate_identifier("23851394", "pmid") == True
assert validate_identifier("23851394", "doi") == False  # Wrong type
```

## Identifier Conversion

ARTL MCP provides comprehensive conversion between all identifier types:

### Basic Conversions

```python
from artl_mcp.tools import (
    doi_to_pmid, doi_to_pmcid,
    pmid_to_doi, pmid_to_pmcid, 
    pmcid_to_doi, get_pmid_from_pmcid
)

# DOI conversions
pmid = doi_to_pmid("10.1038/nature12373")        # → "23851394"
pmcid = doi_to_pmcid("doi:10.1038/nature12373")  # → "PMC3737249"

# PMID conversions  
doi = pmid_to_doi("PMID:23851394")               # → "10.1038/nature12373"
pmcid = pmid_to_pmcid("23851394")                # → "PMC3737249"

# PMCID conversions
doi = pmcid_to_doi("PMC3737249")                 # → "10.1038/nature12373"
pmid = get_pmid_from_pmcid("3737249")            # → "23851394"
```

### Comprehensive ID Mapping

Get all available identifiers for any given identifier:

```python
from artl_mcp.tools import get_all_identifiers

# Works with any identifier type/format
result = get_all_identifiers("doi:10.1038/nature12373")
# Returns:
{
    'doi': '10.1038/nature12373',
    'pmid': '23851394',
    'pmcid': 'PMC3737249',
    'input_type': 'doi'
}

# Also works with PMIDs and PMCIDs
result = get_all_identifiers("PMID:23851394")
result = get_all_identifiers("PMC3737249")
```

## Citation and Reference Networks

ARTL MCP provides comprehensive citation analysis tools:

### Getting References (Papers Cited)

```python
from artl_mcp.tools import get_paper_references

references = get_paper_references("10.1038/nature12373")
# Returns list of referenced papers with metadata:
[
    {
        'key': 'ref1',
        'doi': '10.1038/nature11234',
        'title': 'Referenced paper title',
        'journal': 'Nature',
        'year': '2012',
        'author': 'Smith, J.',
        'unstructured': 'Full citation text...'
    },
    # ... more references
]
```

### Getting Citations (Papers That Cite)

```python
from artl_mcp.tools import get_paper_citations

citations = get_paper_citations("10.1038/nature12373")
# Returns list of citing papers:
[
    {
        'doi': '10.1038/nature45678',
        'title': 'Citing paper title',
        'authors': ['Jane Doe', 'John Smith'],
        'published_date': {'date-parts': [[2024, 1, 15]]},
        'citation_count': 42
    },
    # ... more citing papers
]
```

### Citation Network Analysis

```python
from artl_mcp.tools import get_citation_network

network = get_citation_network("10.1038/nature12373")
# Returns comprehensive network data:
{
    'doi': '10.1038/nature12373',
    'title': 'Paper title',
    'cited_by_count': 245,
    'references_count': 33,
    'concepts': [
        {'display_name': 'Genetics', 'level': 1, 'score': 0.95},
        {'display_name': 'Molecular Biology', 'level': 2, 'score': 0.87}
    ],
    'mesh_terms': ['Genes', 'DNA Sequencing'],
    'open_access': {'is_oa': True, 'oa_date': '2024-01-01'}
}
```

### Finding Related Papers

```python
from artl_mcp.tools import find_related_papers

related = find_related_papers("10.1038/nature12373", max_results=5)
# Returns papers related through citation networks:
[
    {
        'doi': '10.1038/nature45678',
        'title': 'Related paper title',
        'relationship': 'cites_this_paper',
        'citation_count': 67
    },
    {
        'doi': '10.1038/nature78901',
        'title': 'Another related paper',
        'relationship': 'cited_by_this_paper',
        'year': '2020'
    }
]
```

### Comprehensive Citation Analysis

```python
from artl_mcp.tools import get_comprehensive_citation_info

info = get_comprehensive_citation_info("10.1038/nature12373")
# Returns data from multiple sources:
{
    'doi': '10.1038/nature12373',
    'crossref_references': [...],      # From CrossRef API
    'crossref_citations': [...],       # From CrossRef API  
    'openalex_network': {...},         # From OpenAlex API
    'semantic_scholar': {...}          # From Semantic Scholar API
}
```

## Error Handling and Edge Cases

### Invalid Identifiers

All functions gracefully handle invalid identifiers:

```python
# Invalid DOI
result = doi_to_pmid("invalid-doi")  # Returns None

# Invalid format
result = validate_identifier("not-an-id")  # Returns False

# Comprehensive error info
result = get_all_identifiers("invalid")
# Returns: {'doi': None, 'pmid': None, 'pmcid': None, 'input_type': 'unknown', 'error': '...'}
```

### Missing Conversions

Not all papers have all identifier types:

```python
# Paper without PMCID
result = doi_to_pmcid("10.1234/no-pmc-id")  # Returns None

# Check all available IDs
result = get_all_identifiers("10.1234/example")
# Might return: {'doi': '10.1234/example', 'pmid': '12345', 'pmcid': None, 'input_type': 'doi'}
```

### API Timeouts and Failures

All API calls include timeout handling:

```python
# Functions automatically retry and handle timeouts
# If API is unavailable, functions return None gracefully
citations = get_paper_citations("10.1038/nature12373")  
if citations is None:
    print("Citation data temporarily unavailable")
```

## Best Practices

### 1. Use Comprehensive ID Mapping

Instead of multiple individual conversions:

```python
# Don't do this:
pmid = doi_to_pmid(doi)
pmcid = doi_to_pmcid(doi)
# ... separate API calls

# Do this:
all_ids = get_all_identifiers(doi)  # Single API call
pmid = all_ids['pmid']
pmcid = all_ids['pmcid']
```

### 2. Validate Before Processing

```python
# Check identifier validity before expensive operations
if validate_identifier(user_input):
    metadata = get_doi_metadata(user_input)
else:
    print("Invalid identifier format")
```

### 3. Handle Multiple Formats Gracefully

```python
# Your functions can accept any format
def process_paper(identifier):
    # Auto-detects and normalizes any identifier format
    all_ids = get_all_identifiers(identifier)
    
    if all_ids['doi']:
        return get_doi_metadata(all_ids['doi'])
    elif all_ids['pmid']:
        return get_abstract_from_pubmed_id(all_ids['pmid'])
    else:
        return None
```

### 4. Cache Results

```python
# Cache comprehensive ID mappings to avoid repeat API calls
id_cache = {}

def get_cached_ids(identifier):
    if identifier not in id_cache:
        id_cache[identifier] = get_all_identifiers(identifier)
    return id_cache[identifier]
```

## Migration from Legacy Code

If you have existing code that expects specific formats:

### Old Approach
```python
# Manual format handling
def old_doi_function(doi):
    if "https://doi.org/" in doi:
        doi = doi.replace("https://doi.org/", "")
    if "http://dx.doi.org/" in doi:
        doi = doi.replace("http://dx.doi.org/", "")
    # ... more manual cleaning
```

### New Approach
```python
# Automatic normalization
from artl_mcp.utils.identifier_utils import IdentifierUtils

def new_doi_function(doi):
    try:
        normalized = IdentifierUtils.normalize_doi(doi, "raw")
        # Ready to use - no manual cleaning needed
    except IdentifierError:
        return None  # Invalid DOI
```

## API Rate Limiting

All identifier conversion and citation tools implement proper rate limiting:

- **Timeout handling**: 10-second default timeout per request
- **Proper headers**: User-Agent and mailto headers for API courtesy
- **Error handling**: Graceful degradation when APIs are unavailable
- **Retry logic**: Built-in retry for transient failures

## Security Considerations

- **Input validation**: All identifiers are validated before API calls
- **No injection risks**: Identifiers are URL-encoded properly
- **Error message sanitization**: No sensitive information in error messages
- **Rate limiting**: Prevents abuse of external APIs

## Future Enhancements

Planned improvements to identifier handling:

1. **Batch processing**: Convert multiple identifiers in single API calls
2. **Local caching**: Persistent cache for identifier mappings
3. **Additional sources**: Integration with more literature databases
4. **Performance optimization**: Connection pooling and async operations
5. **Extended validation**: Support for additional identifier schemes (ORCID, etc.)

## Support and Troubleshooting

Common issues and solutions:

| Issue | Cause | Solution |
|-------|--------|----------|
| "Invalid DOI format" | Malformed identifier | Use `validate_identifier()` to check format |
| "Conversion returned None" | No mapping exists | Check if paper is indexed in target database |
| "API timeout" | Network/server issues | Retry operation, check internet connection |
| "Invalid email address" | Email required for API | Set `ARTL_EMAIL_ADDR` environment variable |

For additional support, see the main project documentation or submit issues to the GitHub repository.