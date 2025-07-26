# Test Decorators for NCBI Service Availability

This directory contains test decorators that automatically handle NCBI service availability and offline testing scenarios.

## Overview

The test decorators in `test_decorators.py` provide automatic skipping of tests based on:
- NCBI service availability (online/offline)
- Configuration to use alternative sources (Europe PMC, etc.)
- DOE funding compliance (prioritizing US resources when available)

## Available Decorators

### Basic Decorators

#### `@skip_if_ncbi_offline`
Skips test if NCBI services are not responding.
```python
@skip_if_ncbi_offline
def test_pubmed_search():
    # Test code that requires NCBI to be online
    pass

@skip_if_ncbi_offline(reason="PubMed API required")
def test_specific_feature():
    # Test with custom skip reason
    pass
```

#### `@skip_if_using_alternatives`
Skips test if configured to use alternative sources instead of NCBI.
```python
@skip_if_using_alternatives
def test_pubmed_specific():
    # Test code that specifically tests PubMed functionality
    pass
```

#### `@requires_ncbi_access`
Comprehensive decorator that combines configuration and availability checking.
```python
@requires_ncbi_access
def test_pubmed_functionality():
    # Skipped if USE_ALTERNATIVE_SOURCES=true
    pass

@requires_ncbi_access(strict=True)
def test_critical_ncbi():
    # Skipped if NCBI offline OR alternatives configured
    pass
```

### Convenience Markers

Pre-configured pytest markers for common patterns:

```python
@ncbi_required
def test_needs_ncbi():
    # Skipped if alternative sources configured
    pass

@ncbi_online_required  
def test_needs_online_ncbi():
    # Skipped if NCBI services offline
    pass

@ncbi_full_access
def test_needs_full_ncbi():
    # Skipped if offline OR using alternatives
    pass
```

## Configuration Variables

The decorators respond to these environment variables:

- **`USE_ALTERNATIVE_SOURCES`**: Set to "true" to prefer Europe PMC over NCBI
- **`PUBMED_OFFLINE`**: Legacy variable, still supported for backward compatibility

## Service Detection

The decorators automatically test NCBI service availability by checking:
- `https://pubmed.ncbi.nlm.nih.gov/`
- `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/einfo.fcgi`
- `https://www.ncbi.nlm.nih.gov/pmc/`

## Usage Examples

### Test Files

```python
from tests.test_decorators import requires_ncbi_access, skip_if_ncbi_offline

@pytest.mark.external_api
@pytest.mark.slow
@requires_ncbi_access
def test_search_pubmed_for_pmids():
    """Test PubMed search - skipped if alternatives configured."""
    result = search_pubmed_for_pmids("CRISPR", max_results=5)
    assert result is not None

@pytest.mark.external_api
@pytest.mark.slow
@skip_if_ncbi_offline
def test_get_abstract_online():
    """Test abstract retrieval - skipped if NCBI offline."""
    result = get_abstract_from_pubmed_id("12345")
    assert result is not None
```

### Running Tests

Run all tests:
```bash
pytest tests/
```

Run only NCBI-dependent tests when services are available:
```bash
# These will be skipped automatically if NCBI is offline
pytest tests/ -m "external_api and slow"
```

Skip NCBI tests entirely:
```bash
USE_ALTERNATIVE_SOURCES=true pytest tests/
```

## Benefits

1. **Automatic Handling**: Tests automatically skip when services are unavailable
2. **Clear Reasons**: Descriptive skip messages explain why tests were skipped
3. **Configuration Aware**: Respects environment variable configuration
4. **DOE Compliance**: Prioritizes US resources when available
5. **Flexible**: Multiple decorator options for different requirements

## Test Categories

The decorators create these test categories:

- **NCBI Required**: Tests that specifically need NCBI APIs
- **Online Required**: Tests that need live service connectivity  
- **Alternative Safe**: Tests that work with either NCBI or Europe PMC
- **Offline Safe**: Tests that don't require external services

This allows for flexible test execution based on current infrastructure availability and configuration.