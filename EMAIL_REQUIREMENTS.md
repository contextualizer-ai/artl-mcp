# Email Address Requirements for ARTL MCP

This document outlines which functions and APIs require email addresses, why they need them, and how to provide them properly.

## Overview

Several APIs used by ARTL MCP require email addresses for:
- **Rate limiting identification**: APIs track usage per email to enforce fair use
- **Contact information**: APIs want to reach users if there are issues with their requests
- **Terms of service compliance**: Some APIs require contact info for legal/policy reasons
- **Academic courtesy**: Institutional emails help identify legitimate research use

## Functions Requiring Email Addresses

### DOIFetcher-based Tools (High Priority)

All these functions create a `DOIFetcher` instance which requires an email:

| Function | File | API Used | Email Required | Notes |
|----------|------|----------|----------------|-------|
| `get_doi_fetcher_metadata()` | `tools.py:232` | CrossRef + Unpaywall | **REQUIRED** | CrossRef metadata + Unpaywall open access info |
| `get_unpaywall_info()` | `tools.py:241` | Unpaywall | **REQUIRED** | Unpaywall API requires email for all requests |
| `get_full_text_from_doi()` | `tools.py:266` | Unpaywall + S2ORC | **REQUIRED** | Full text retrieval from multiple sources |
| `get_full_text_info()` | `tools.py:288` | Unpaywall + S2ORC | **REQUIRED** | Metadata about full text availability |
| `get_text_from_pdf_url()` | `tools.py:313` | Unpaywall | **REQUIRED** | PDF text extraction via Unpaywall |
| `clean_text()` | `tools.py:355` | DOIFetcher | **REQUIRED** | Text cleaning via DOIFetcher |

### PubMed Utils (Medium Priority)

Functions that *may* use DOIFetcher internally:

| Function | File | Email Usage | Notes |
|----------|------|-------------|-------|
| `get_doi_text()` | `pubmed_utils.py:67` | **Uses bogus email** | Creates DOIFetcher with "pubmed_utils@example.com" |
| `get_pmcid_text()` | `pubmed_utils.py:157` | **Uses bogus email** | Creates DOIFetcher with "pubmed_utils@example.com" |

### CLI Commands

All CLI commands that call the above functions require `--email` parameter:

| Command | Function Called | Email Required |
|---------|----------------|----------------|
| `get-doi-fetcher-metadata` | `get_doi_fetcher_metadata()` | **YES** |
| `get-unpaywall-info` | `get_unpaywall_info()` | **YES** |
| `get-full-text-from-doi` | `get_full_text_from_doi()` | **YES** |
| `get-full-text-info` | `get_full_text_info()` | **YES** |
| `get-text-from-pdf-url` | `get_text_from_pdf_url()` | **YES** |
| `clean-text` | `clean_text()` | **YES** |

## Email Address Sources (Priority Order)

The `EmailManager` class looks for email addresses in this order:

1. **Provided parameter**: Email passed directly to function
2. **`ARTL_EMAIL_ADDR` environment variable**: `export ARTL_EMAIL_ADDR=your@email.com`
3. **`local/.env` file**: `ARTL_EMAIL_ADDR=your@email.com`
4. **Legacy `local/.env` format**: `email_address=your@email.com` (deprecated)

## Setting Up Email Address

### Option 1: Environment Variable (Recommended)
```bash
export ARTL_EMAIL_ADDR=researcher@university.edu
```

### Option 2: Local .env File
Create `local/.env` file:
```
ARTL_EMAIL_ADDR=researcher@university.edu
```

### Option 3: CLI Parameter
```bash
artl-cli get-unpaywall-info --doi "10.1038/nature12373" --email "researcher@university.edu"
```

## Email Validation Rules

The system validates email addresses and rejects:

### Bogus Email Patterns (Automatically Rejected)
- `*@example.com` - Test domain
- `*test*@*` - Contains "test"  
- `*dummy*@*` - Contains "dummy"
- `*fake*@*` - Contains "fake"
- `*placeholder*@*` - Contains "placeholder"
- `*invalid*@*` - Contains "invalid"
- `*noreply*@*` - No-reply addresses
- `*no-reply*@*` - No-reply addresses

### API-Specific Requirements
- **Unpaywall/CrossRef**: Prefer institutional emails (`.edu`, `.org`, `.gov`)
- **All APIs**: Must be valid email format (`user@domain.com`)

## Current Issues to Fix

### High Priority
1. **`pubmed_utils.py` uses bogus emails**: 
   - `get_doi_text()` uses `"pubmed_utils@example.com"`
   - `get_pmcid_text()` uses `"pubmed_utils@example.com"`
   - **Solution**: Update to use `EmailManager`

2. **Test files use bogus emails**:
   - Multiple test files use `"test@example.com"`
   - **Solution**: Use real emails or skip email-required tests

### Medium Priority  
3. **MCP tools don't expose email requirements**:
   - MCP tool definitions should indicate when email is needed
   - **Solution**: Update tool schemas and documentation

## Example Integration

### Before (Problematic)
```python
# DON'T DO THIS - uses bogus email
doi_fetcher = DOIFetcher(email="pubmed_utils@example.com")
result = doi_fetcher.get_full_text(doi)
```

### After (Recommended)
```python
from artl_mcp.utils.email_manager import require_email

# Get validated email from environment/config
email = require_email()
doi_fetcher = DOIFetcher(email=email)
result = doi_fetcher.get_full_text(doi)
```

### Function with Email Parameter
```python
from artl_mcp.utils.email_manager import EmailManager

def get_full_text_from_doi(doi: str, email: str) -> Optional[str]:
    \"\"\"Get full text for a DOI.
    
    Args:
        doi: DOI to get full text for
        email: Email address for API requests (required by Unpaywall)
    \"\"\"
    em = EmailManager()
    validated_email = em.validate_for_api("unpaywall", email)
    
    dfr = DOIFetcher(email=validated_email)
    return dfr.get_full_text(doi)
```

## API Rate Limiting

When using email addresses:
- **Use your real institutional email** when possible
- **Don't share email addresses** across different users/systems  
- **Respect rate limits** (typically 1000 requests/hour per email)
- **Cache results** to minimize API calls

## Troubleshooting

### "Bogus email address not allowed"
- You're using a test/fake email address
- Set a real email via `ARTL_EMAIL_ADDR` environment variable

### "No valid email address found"  
- No email configured in environment or .env file
- Set `ARTL_EMAIL_ADDR=your@email.com` in environment or `local/.env`

### "Invalid email format"
- Email doesn't match standard format
- Check for typos in email address

### "API requires a real institutional email"
- Using `@example.com` or similar for APIs that need real emails
- Use your institutional email address (`.edu`, `.org`, `.gov`)

## Future Improvements

1. **Add email to MCP tool schemas**: Tools should declare email requirements
2. **Improve error messages**: More specific guidance for each API
3. **Add email validation for specific APIs**: Some APIs have specific format requirements
4. **Support multiple email addresses**: Allow different emails for different APIs
5. **Add usage tracking**: Monitor API usage per email address