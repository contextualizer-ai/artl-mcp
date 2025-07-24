# Testing Commands Reference

This document provides the key testing commands for efficient test execution.

## Quick Testing (Skip Slow External API Tests)

For fast development testing (skip external API calls and slow tests):

```bash
# Skip slow external API tests (fastest for development)
uv run pytest -m "not slow and not external_api" --cov=artl_mcp --cov-report=term-missing -v

# Skip only slow tests (includes some external APIs but not the slowest ones)
uv run pytest -m "not slow" --cov=artl_mcp --cov-report=term-missing -v

# Run only fast unit tests (no external APIs at all)
uv run pytest -m "not external_api" --cov=artl_mcp --cov-report=term-missing -v
```

## Full Testing (Including External APIs)

For complete test coverage (runs all tests including slow external API calls):

```bash
# Full test suite with coverage
uv run pytest --cov=artl_mcp --cov-report=term-missing --cov-report=html -v

# Full test suite without coverage (faster)
uv run pytest -v
```

## Selective Testing

Run specific test categories:

```bash
# Run only slow/external API tests
uv run pytest -m "slow or external_api" -v

# Run only integration tests
uv run pytest -m "integration" -v

# Run tests for a specific module
uv run pytest tests/test_tools.py -v

# Run a specific test
uv run pytest tests/test_tools.py::test_clean_text -v
```

## Typical Development Workflow

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

## Current Test Markers

- `@pytest.mark.slow`: Tests that take >2 seconds (mostly external API calls)
- `@pytest.mark.external_api`: Tests that require internet/external APIs
- `@pytest.mark.integration`: Integration tests
- `@pytest.mark.asyncio`: Async tests

## Coverage Targets

Current coverage status:
- **PDF fetcher**: 100% ✅
- **Client**: 100% ✅ 
- **CLI**: 99% ✅
- **DOI fetcher**: 91% ✅
- **Main**: 89% ✅
- **PubMed utils**: 88% ✅
- **Tools**: 60% ✅
- **Overall**: 79% ✅