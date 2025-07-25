# ARTL-MCP Developer Guide

This guide provides comprehensive information for developers contributing to ARTL-MCP (All Roads to Literature - Model
Context Protocol).

## Table of Contents

- [Project Overview](#project-overview)
- [Development Setup](#development-setup)
- [Architecture](#architecture)
- [Code Quality](#code-quality)
- [Testing](#testing)
- [Release Process](#release-process)
- [Contributing Guidelines](#contributing-guidelines)

## Project Overview

ARTL-MCP is a Python package that provides both an MCP server and CLI tools for scientific literature retrieval and
analysis. The project uses modern Python tooling and follows best practices for maintainability and reliability.

### Key Technologies

- **Python 3.11+** - Target runtime
- **UV** - Fast Python package manager
- **Hatch** - Modern Python packaging tool
- **FastMCP** - MCP server framework
- **Click** - CLI framework
- **Pytest** - Testing framework
- **Ruff** - Linting and formatting
- **MyPy** - Static type checking

### Project Structure

```
artl-mcp/
├── src/artl_mcp/           # Main package
│   ├── __main__.py         # MCP server entry point
│   ├── main.py             # MCP server implementation  
│   ├── cli.py              # CLI commands
│   ├── tools.py            # MCP tool definitions
│   └── utils/              # Utility modules
│       ├── citation_utils.py    # Citation network analysis
│       ├── doi_fetcher.py       # DOI metadata fetching
│       ├── email_manager.py     # Email validation/management
│       ├── file_manager.py      # File saving utilities
│       ├── identifier_utils.py  # ID format handling
│       ├── pdf_fetcher.py       # PDF text extraction
│       └── pubmed_utils.py      # PubMed API utilities
├── tests/                  # Test suite
├── pyproject.toml         # Project configuration
├── Makefile              # Development commands
└── docs/                 # Documentation (*.md files)
```

## Development Setup

### Prerequisites

- **Python 3.11+** installed
- **UV** package manager ([installation guide](https://docs.astral.sh/uv/getting-started/installation/))
- **Git** for version control

### Initial Setup

```bash
# Clone the repository
git clone https://github.com/contextualizer-ai/artl-mcp.git
cd artl-mcp

# Install dependencies (development group)
uv sync --group dev

# Verify installation
uv run pytest --version
uv run artl-mcp --version
```

### Development Environment

The project uses dependency groups defined in `pyproject.toml`:

```toml
[dependency-groups]
dev = [
    # Code quality and formatting
    "black>=23.0.0",
    "ruff>=0.1.0",
    "mypy>=1.0.0",
    # Testing
    "pytest>=8.4.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.0.0",
    "pytest-timeout>=2.1.0",
    # Build and packaging tools
    "hatch-vcs>=0.5.0",
    "hatchling>=1.27.0",
    "hatch>=1.14.1"
]
```

### Environment Variables for Development

**Option 1: Shell Environment (Global)**

```bash
# Email for API testing (use your real institutional email)
export ARTL_EMAIL_ADDR="developer@university.edu"

# File output configuration
export ARTL_OUTPUT_DIR="~/dev/artl-output"
export ARTL_KEEP_TEMP_FILES=true  # Keep temp files for debugging
```

**Option 2: Local Environment File (Project-Specific)**

```bash
# Create local/.env file for this project only
echo "ARTL_EMAIL_ADDR=developer@university.edu" > local/.env
echo "ARTL_OUTPUT_DIR=~/dev/artl-output" >> local/.env
echo "ARTL_KEEP_TEMP_FILES=true" >> local/.env
```

The `.env` file method is ideal for developers who:

- Work on multiple projects with different email requirements
- Want project-specific configuration without affecting global environment
- Prefer not to modify shell configuration files

## Architecture

### Core Components

#### 1. MCP Server (`main.py`)

- Implements FastMCP server protocol
- Registers all tools from `tools.py`
- Handles both stdio and network communication
- Provides basic CLI options for testing

#### 2. CLI Interface (`cli.py`)

- Comprehensive Click-based CLI
- 21+ individual commands
- Consistent parameter handling
- File saving integration

#### 3. Tools Registry (`tools.py`)

- Defines all MCP tools (35+ tools)
- Handles parameter validation
- Integrates with utility modules
- Provides consistent error handling

#### 4. Utility Modules (`utils/`)

**Citation Analysis (`citation_utils.py`)**

- CrossRef API integration
- OpenAlex API integration
- Semantic Scholar API integration
- Citation network analysis

**DOI Operations (`doi_fetcher.py`)**

- CrossRef metadata fetching
- Unpaywall integration
- Enhanced metadata retrieval

**Email Management (`email_manager.py`)**

- Email validation and sanitization
- API-specific email requirements
- Environment variable handling

**File Management (`file_manager.py`)**

- Cross-platform file operations
- Automatic filename sanitization
- Directory management
- Temp file cleanup

**Identifier Handling (`identifier_utils.py`)**

- Multi-format identifier parsing
- Format validation and normalization
- Conversion between formats

**PDF Processing (`pdf_fetcher.py`)**

- PDF download and caching
- Text extraction via pdfminer
- Error handling and cleanup

**PubMed Integration (`pubmed_utils.py`)**

- PubMed API interactions
- PMID/PMCID conversions
- Abstract and metadata retrieval

### Design Patterns

#### 1. Consistent Error Handling

```python
def example_function(identifier: str) -> Optional[Dict]:
    try:
        # Validate input
        if not validate_identifier(identifier):
            return None

        # Perform operation with timeout
        result = api_call(identifier, timeout=10)

        return result
    except (RequestException, ValueError) as e:
        logger.warning(f"Operation failed: {e}")
        return None
```

#### 2. File Saving Integration

```python
@save_file_wrapper
def get_metadata(doi: str, save_file: bool = False, save_to: str = None) -> Dict:
    # Function implementation
    metadata = fetch_metadata(doi)

    # save_file_wrapper handles saving based on parameters
    return metadata
```

#### 3. Email Management

```python
from artl_mcp.utils.email_manager import EmailManager


def api_function(identifier: str, email: str) -> Optional[Dict]:
    em = EmailManager()
    validated_email = em.validate_for_api("crossref", email)

    # Use validated_email for API calls
    return make_api_call(identifier, validated_email)
```

## Code Quality

### Linting and Formatting

The project uses **Ruff** for both linting and formatting:

```bash
# Run linting with auto-fix
make lint
# or
uv run ruff check --fix src/ tests/

# Run formatting  
make format
# or
uv run ruff format src/ tests/
```

### Ruff Configuration

Current ruff rules (in `pyproject.toml`):

```toml
[tool.ruff.lint]
select = [
    "E", # pycodestyle errors
    "W", # pycodestyle warnings  
    "F", # pyflakes
    "I", # isort
    "B", # flake8-bugbear
    "C4", # flake8-comprehensions
    "UP", # pyupgrade
]
```

**Additional rules to consider:**

```toml
select = [
    # ... existing rules ...
    "D", # pydocstyle (docstring checking)
    "S", # flake8-bandit (security)
    "PTH", # flake8-use-pathlib
    "RUF", # Ruff-specific rules
    "PL", # Pylint rules
]
```

### Type Checking

The project uses **MyPy** for static type checking:

```bash
# Run type checking
make mypy
# or  
uv run mypy src/
```

### MyPy Configuration

```toml
[tool.mypy]
python_version = "3.11"
warn_unused_configs = true
show_error_codes = true
ignore_missing_imports = true  # For third-party libraries
disallow_untyped_defs = false  # Gradually enable
```

### Dependency Checking

The project uses **Deptry** to find unused dependencies:

```bash
# Check for unused dependencies
make deptry
# or
uvx deptry .
```

## Testing

### Test Organization

Tests are organized by module in the `tests/` directory:

- `test_main.py` - MCP server and main CLI tests
- `test_cli.py` - Individual CLI command tests
- `test_tools.py` - MCP tool function tests
- `test_*.py` - Utility module tests

### Test Markers

Tests use pytest markers for organization:

```python
@pytest.mark.slow
def test_expensive_operation():
    # Takes >2 seconds
    pass


@pytest.mark.external_api
def test_api_integration():
    # Requires internet/external APIs
    pass


@pytest.mark.integration
def test_component_integration():
    # Tests multiple components together
    pass
```

### Running Tests

#### Quick Testing Commands Reference

**Development (fast tests - skip slow external API tests):**

```bash
# Fastest for development - skip external APIs and slow tests
make test
# or
uv run pytest -m "not slow and not external_api" --cov=artl_mcp --cov-report=term-missing -v

# Skip only slow tests (includes some external APIs but not the slowest)
uv run pytest -m "not slow" --cov=artl_mcp --cov-report=term-missing -v

# Run only fast unit tests (no external APIs at all)  
uv run pytest -m "not external_api" --cov=artl_mcp --cov-report=term-missing -v
```

**Full Testing (including external APIs):**

```bash
# Complete test coverage (runs all tests including slow external API calls)
make test-coverage
# or
uv run pytest --cov=artl_mcp --cov-report=term-missing --cov-report=html -v

# Full test suite without coverage (faster)
uv run pytest -v
```

**Selective Testing:**

```bash
# Run only slow/external API tests
uv run pytest -m "slow or external_api" -v

# Run only integration tests
uv run pytest -m "integration" -v

# Run specific test file
uv run pytest tests/test_tools.py -v

# Run specific test function
uv run pytest tests/test_tools.py::test_get_doi_metadata -v
```

#### Typical Development Workflow

1. **During development**: Use fast tests
   ```bash
   uv run pytest -m "not slow" --cov=artl_mcp --cov-report=term-missing -q
   ```

2. **Before committing**: Run full test suite
   ```bash
   uv run pytest --cov=artl_mcp --cov-report=term-missing -v
   ```

3. **CI/Automated testing**: Skip flaky external APIs
   ```bash
   CI=true uv run pytest -m "not slow" --cov=artl_mcp --cov-report=xml -v
   ```

### Writing Tests

**Testing Philosophy:**

- Minimize mocking - test real functionality when possible
- Use real temporary files with proper cleanup
- Mark external API tests appropriately
- Test both success and failure scenarios
- Aim for high coverage on meaningful code

**Example test structure:**

```python  
import pytest
from artl_mcp.tools import get_doi_metadata


def test_get_doi_metadata_success():
    """Test successful metadata retrieval."""
    result = get_doi_metadata("10.1038/nature12373")

    assert result is not None
    assert "title" in result
    assert "authors" in result
    assert result["DOI"] == "10.1038/nature12373"


def test_get_doi_metadata_invalid_doi():
    """Test handling of invalid DOI."""
    result = get_doi_metadata("invalid-doi")
    assert result is None


@pytest.mark.external_api
def test_get_doi_metadata_real_api():
    """Test with real API call."""
    result = get_doi_metadata("10.1038/nature12373")
    assert result is not None
    # More comprehensive assertions for real API data
```

### Current Coverage Status

Recent coverage metrics:

- **Overall**: 79%
- **PDF fetcher**: 100% ✅
- **Client**: 100% ✅
- **CLI**: 99% ✅
- **DOI fetcher**: 91% ✅
- **Main**: 89% ✅
- **PubMed utils**: 88% ✅
- **Tools**: 60% (target for improvement)

## Release Process

### Automated Releases (Primary Method)

**ARTL-MCP uses GitHub Actions with PyPI Trusted Publisher for secure, automated releases.** This is the standard workflow for all releases.

#### Standard Release Workflow

1. **Merge all passing PRs** to the main branch through normal code review
2. **Create a GitHub release** to trigger automated publishing:
   - Go to https://github.com/contextualizer-ai/artl-mcp/releases  
   - Click "Create a new release"
   - Choose "Create new tag" and enter semantic version (e.g., `v0.9.0`)
   - Add release notes describing changes
   - Click "Publish release"
3. **GitHub Actions automatically** (`.github/workflows/pypi-publish.yaml`):
   - ✅ Runs full test suite
   - ✅ Builds package with hatch
   - ✅ Validates version matches tag
   - ✅ Verifies package integrity  
   - ✅ Publishes to PyPI using trusted publisher (no tokens needed)
   - ✅ Uploads build artifacts to GitHub release

#### Version Management

The project uses **hatch-vcs** for automatic version management:

- Versions are determined from git tags
- Development versions include commit hashes when between tags  
- Only tagged commits produce clean version numbers suitable for PyPI
- The `_version.py` file is auto-generated and should not be committed

#### PyPI Trusted Publisher

The project uses **PyPI Trusted Publisher** for secure authentication:

- ✅ **No API tokens required** - uses OpenID Connect 
- ✅ **Enhanced security** - GitHub Actions authenticates directly with PyPI
- ✅ **Automatic publishing** from authorized repository/workflow
- ✅ **Token rotation not needed** - no secrets to manage

### Special Release Types

- **TestPyPI**: Create tags containing `test` (e.g., `v0.9.0-test`)
- **Dry run**: Create tags containing `dryrun` (e.g., `v0.9.0-dryrun`) 

### Manual Release Process (Emergency Backup Only)

**⚠️ Manual releases should only be used when GitHub Actions is unavailable or for emergency hotfixes.**

#### Emergency Manual Release Steps

1. **Configure PyPI authentication** (if needed):
   ```bash
   export HATCH_INDEX_USER="__token__"
   export HATCH_INDEX_AUTH="pypi-your-actual-token-here"
   ```

2. **Create and push tag**:
   ```bash
   git tag v0.9.0  # Use appropriate version
   git push origin v0.9.0
   ```

3. **Build and upload**:
   ```bash
   make release  # Runs clean, test, build, upload
   ```

4. **Verify**: Check https://pypi.org/project/artl-mcp/

### Troubleshooting

- **Version issues**: Ensure clean git status on tagged commit
- **Build issues**: Run `make clean` then `make dev`
- **Authentication**: Verify token hasn't expired

### Best Practices

1. **Prefer automated releases** - Use GitHub releases for standard workflow
2. **Use semantic versioning** - Follow semver.org conventions  
3. **Test thoroughly** - Run full test suite before releasing
4. **Never delete releases** - Create new patch versions instead

## Contributing Guidelines

### Git Workflow

1. **Fork and clone** the repository
2. **Create feature branch**: `git checkout -b feature/description`
3. **Make changes** with appropriate tests
4. **Run quality checks**: `make lint`, `make mypy`, `make test`
5. **Commit with clear messages**
6. **Push and create pull request**

### Code Standards

#### Function Documentation

```python
def get_paper_metadata(doi: str, email: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieve comprehensive metadata for a scientific paper.
    
    Args:
        doi: Digital Object Identifier for the paper
        email: Email address for API requests (required for some sources)
        
    Returns:
        Dictionary containing paper metadata, or None if not found
        
    Raises:
        ValueError: If DOI format is invalid
        RequestException: If API request fails
    """
```

#### Error Handling

```python
def api_function(identifier: str) -> Optional[Dict]:
    try:
        # Validate inputs first
        if not validate_identifier(identifier):
            logger.warning(f"Invalid identifier format: {identifier}")
            return None

        # Make API request with timeout
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        return response.json()

    except requests.RequestException as e:
        logger.warning(f"API request failed: {e}")
        return None
    except ValueError as e:
        logger.error(f"Data processing error: {e}")
        return None
```

#### File Operations

```python
from pathlib import Path
from artl_mcp.utils.file_manager import FileManager


def save_data(data: Dict, filepath: str) -> bool:
    """Save data to file with proper error handling."""
    try:
        fm = FileManager()
        safe_path = fm.sanitize_filename(filepath)

        with open(safe_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return True

    except (IOError, OSError) as e:
        logger.error(f"Failed to save file {filepath}: {e}")
        return False
```

### Adding New Features

#### 1. New MCP Tool

```python
# In tools.py
@mcp.tool()
def new_tool_name(parameter: str) -> Optional[Dict[str, Any]]:
    """Tool description for MCP client.
    
    Args:
        parameter: Description of parameter
        
    Returns:
        Tool result data
    """
    try:
        # Implementation
        result = process_parameter(parameter)
        return result
    except Exception as e:
        logger.error(f"Tool error: {e}")
        return None
```

#### 2. New CLI Command

```python
# In cli.py
@cli.command()
@click.option('--parameter', required=True, help='Parameter description')
@click.option('--save-file', is_flag=True, help='Save output to file')
def new_command(parameter: str, save_file: bool):
    """Command description."""
    try:
        result = new_tool_name(parameter)

        if result:
            output = json.dumps(result, indent=2)
            click.echo(output)

            if save_file:
                # Handle file saving
                pass
        else:
            click.echo("No results found", err=True)
            sys.exit(1)

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
```

#### 3. New Utility Module

Create `src/artl_mcp/utils/new_module.py`:

```python
"""New utility module description."""

import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class NewUtility:
    """Utility class description."""

    def __init__(self, config: Optional[str] = None):
        self.config = config

    def process_data(self, data: str) -> Optional[Dict[str, Any]]:
        """Process data and return results."""
        try:
            # Implementation
            return {"processed": data}
        except Exception as e:
            logger.error(f"Processing failed: {e}")
            return None
```

### Testing New Features

1. **Write tests first** (TDD approach encouraged)
2. **Test both success and failure cases**
3. **Use appropriate test markers**
4. **Mock external dependencies minimally**
5. **Ensure cross-platform compatibility**

### Pull Request Process

1. **Ensure CI passes** (linting, type checking, tests)
2. **Add/update documentation** as needed
3. **Update CHANGELOG** if applicable
4. **Request review** from maintainers
5. **Address feedback** promptly

### Code Review Checklist

- [ ] Code follows project style and conventions
- [ ] Comprehensive tests included
- [ ] Documentation updated
- [ ] No security vulnerabilities introduced
- [ ] Performance implications considered
- [ ] Cross-platform compatibility maintained
- [ ] Error handling is appropriate
- [ ] Logging is informative but not excessive

## Development Tools Reference

### Makefile Targets

```bash
make dev           # Install development dependencies
make test          # Run fast tests (no external APIs)
make test-coverage # Run full test suite with coverage
make lint          # Run ruff linting with auto-fix
make format        # Run code formatting
make mypy          # Run type checking
make deptry        # Check for unused dependencies
make clean         # Remove build artifacts
make build         # Build package with hatch
make upload        # Upload to PyPI
make upload-test   # Upload to TestPyPI
make release       # Complete release workflow
make all           # Run complete development workflow
```

### Environment Variables

```bash
# Development
ARTL_EMAIL_ADDR=developer@university.edu
ARTL_OUTPUT_DIR=~/dev/artl-output
ARTL_KEEP_TEMP_FILES=true

# CI/Testing
CI=true  # Skips some flaky external API tests
```

### Useful Commands

```bash
# Interactive development
uv run python -c "from artl_mcp.tools import *; print(get_doi_metadata('10.1038/nature12373'))"

# Test specific functionality
uv run artl-cli get-doi-metadata --doi "10.1038/nature12373"

# Debug MCP server
uv run artl-mcp --doi-query "10.1038/nature12373"

# Check package info
uv run hatch version
uv run hatch build --check
```