# File Management Strategy for ARTL MCP

## Overview

ARTL MCP now includes comprehensive file saving capabilities for all content retrieval functions. This system provides cross-platform file management with configurable output directories and temp file handling.

## Environment Variables

### Primary Configuration

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `ARTL_OUTPUT_DIR` | Directory for saved files | `~/Documents/artl-mcp` | `/path/to/papers` |
| `ARTL_TEMP_DIR` | Temporary files directory | System temp + `artl-mcp` | `/tmp/artl-mcp` |
| `ARTL_KEEP_TEMP_FILES` | Keep temp files after processing | `false` | `true` |
| `ARTL_EMAIL_ADDR` | Email for API requests | None | `user@domain.com` |

### Platform Defaults

- **Windows**: `%USERPROFILE%\Documents\artl-mcp`
- **macOS/Linux**: `~/Documents/artl-mcp`
- **Temp files**: System temp directory + `artl-mcp/`

## File Saving Features

### Simplified File Saving Interface

Every content retrieval function now supports a consistent, minimal file saving interface with two parameters:

- `save_file: bool = False` - Save to temp directory with auto-generated filename
- `save_to: str | None = None` - Save to specific path (overrides save_file if provided)

```python
# No saving (default)
get_doi_metadata("10.1038/nature12373")

# Save to temp directory with auto-generated filename
get_doi_metadata("10.1038/nature12373", save_file=True)

# Save to specific path (overrides save_file)
get_doi_metadata("10.1038/nature12373", save_to="my_paper.json")

# Full text examples
get_full_text_from_doi("10.1038/nature12373", email, save_file=True)
get_full_text_from_doi("10.1038/nature12373", email, save_to="/path/to/paper.txt")

# Search results
search_papers_by_keyword("CRISPR", save_file=True)
search_papers_by_keyword("CRISPR", save_to="crispr_papers.json")
```

### Supported File Formats

| Content Type | Default Format | Supported Extensions |
|--------------|----------------|----------------------|
| Metadata | JSON | `.json` |
| Abstracts | Text | `.txt` |
| Full text | Text | `.txt` |
| Search results | JSON | `.json` |
| PDF content | Binary | `.pdf` |
| Citation data | JSON | `.json`, `.csv` |

### Auto-Generated Filenames

When using `save_file=True`, filenames follow this pattern:
```
{content_type}_{clean_identifier}_{timestamp}.{extension}
```

Examples:
- `metadata_10.1038_nature12373_20250724_152502.json`
- `fulltext_PMC1234567_20250724_153015.txt`
- `search_CRISPR_gene_editing_20250724_154230.json`

## Cross-Platform Safety

### Filename Sanitization

The system automatically sanitizes filenames for cross-platform compatibility:

- **Invalid characters** (`<>:"/\|?*`) → replaced with `_`
- **Reserved names** (Windows: `CON`, `PRN`, etc.) → prefixed with `_`
- **Length limits** → truncated while preserving extensions
- **Unicode support** → full UTF-8 support in content

### Path Handling

- Uses `pathlib.Path` for cross-platform path operations
- Automatically creates output directories if they don't exist
- Handles both forward slashes (`/`) and backslashes (`\`)

## Temp File Management

### Automatic Cleanup

- PDF processing creates temporary files for text extraction
- Files are automatically cleaned up after processing
- Configurable retention policy via `ARTL_KEEP_TEMP_FILES`

### Retention Policies

| Setting | Behavior |
|---------|----------|
| `false` (default) | Always delete temp files |
| `true` | Keep temp files for debugging |

## Usage Examples

### Basic File Saving

```python
from artl_mcp.tools import get_doi_metadata, get_abstract_from_pubmed_id

# Save metadata with auto-generated filename
metadata = get_doi_metadata("10.1038/nature12373", save_file=True)

# Save abstract with custom filename
abstract = get_abstract_from_pubmed_id("23851394", save_to="paper_abstract.txt")
```

### Configuration Setup

```bash
# Set custom output directory
export ARTL_OUTPUT_DIR="/Users/researcher/papers"

# Keep temp files for debugging
export ARTL_KEEP_TEMP_FILES=true

# Set email for API access
export ARTL_EMAIL_ADDR="researcher@university.edu"
```

### Batch Processing

```python
# Process multiple papers and save all
dois = ["10.1038/nature12373", "10.1126/science.1234567"]

for doi in dois:
    # Auto-generates unique filenames for each paper
    metadata = get_doi_metadata(doi, save_file=True)
    fulltext = get_full_text_from_doi(doi, email, save_file=True)
```

## File Organization

### Default Directory Structure

```
~/Documents/artl-mcp/
├── metadata_10.1038_nature12373_20250724_152502.json
├── fulltext_10.1038_nature12373_20250724_152503.txt
├── search_CRISPR_20250724_153000.json
└── abstract_23851394_20250724_153100.txt
```

### Custom Organization

Users can organize files by setting `ARTL_OUTPUT_DIR` or using subdirectories:

```python
# Save to specific subdirectory
get_doi_metadata("10.1038/nature12373", save_to="nature_papers/metadata.json")
```

## Error Handling

### Graceful Degradation

- File saving errors don't prevent content retrieval
- Warnings logged for file operation failures
- Original functionality preserved if file operations fail

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Permission denied | Insufficient write permissions | Check directory permissions |
| Disk full | No space left | Free up disk space or change output directory |
| Invalid filename | Special characters in identifier | Auto-sanitization handles this |

## Integration with MCP Tools

All MCP-registered tools maintain their original functionality while adding optional file saving:

```python
# MCP tools work exactly as before
metadata = mcp.call_tool("get_doi_metadata", {"doi": "10.1038/nature12373"})

# With optional file saving
metadata = mcp.call_tool("get_doi_metadata", {
    "doi": "10.1038/nature12373", 
    "save_file": True
})
```

## Benefits

### For Researchers
- **Offline access** to retrieved papers
- **Organized storage** with automatic naming
- **Batch processing** capabilities
- **Cross-platform** compatibility

### For Developers
- **Consistent API** across all functions
- **Configurable behavior** via environment variables
- **Error resilience** with graceful degradation
- **Extensible format** support

### For System Administrators
- **Centralized configuration** via environment variables
- **Predictable file locations** for backup/archival
- **Temp file management** to prevent disk bloat
- **Platform independence** for deployment

## Future Enhancements

Potential future improvements include:
- **Compression options** for large files
- **Cloud storage integration** (S3, Google Drive)
- **Metadata embedding** in saved files
- **Duplicate detection** and handling
- **File indexing** and search capabilities