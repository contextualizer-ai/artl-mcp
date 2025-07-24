# Testing Progress Summary

## Current Status: Issue #126 - Improve Unit Tests

We are systematically achieving 100% test coverage for the artl-mcp project following BBOP best practices.

### Completed Work

1. **Framework Conversion**: Successfully converted from unittest classes to pure pytest functions
2. **Coverage Infrastructure**: Added pytest markers, Makefile targets, and GitHub Actions integration
3. **Comprehensive CLI Testing**: All 21 CLI commands tested with success/failure scenarios (100% coverage)
4. **PubMed Utilities**: 15 comprehensive tests for ID conversion functions (52% → 91% coverage)
5. **Core Tools**: Enhanced `extract_paper_info` with 9 test cases covering all edge cases

### Current Coverage
- **Overall**: 52% (+7 percentage points from 45%)
- **Major improvements**: pubmed_utils.py, tools.py, cli.py
- **Target**: 100% coverage for all meaningful functions

### Testing Philosophy Changes

**User Requirements**:
- ✅ **Eliminate mock and patch** - minimize or remove mocking entirely
- ✅ **Real functionality testing** - test actual behavior, not mocked behavior
- ✅ **Cross-platform compatibility** - code must work on many different operating systems
- ✅ **Temporary files with cleanup** - use real files but ensure proper cleanup
- ✅ **pytest fixtures** - use fixtures for test data and setup
- ✅ **Consistent API markers** - use `@pytest.mark.external_api` for tests requiring external services

### Next Steps

#### ✅ Completed: PDF Tests Rewritten 
File: `tests/test_pdf_fetcher.py` (100% coverage)

**Implemented approach**:
- ✅ Real HTTP requests to known PDF URLs with `@pytest.mark.external_api`
- ✅ Real temporary file creation/cleanup (cross-platform)
- ✅ Real PDF parsing with minimal valid test PDFs
- ✅ Minimal mocking only for unreliable scenarios (network timeouts, OS errors)
- ✅ 14 comprehensive test cases covering all success/failure paths
- ✅ 100% line coverage achieved

#### Remaining Files to Test

1. **`main.py`** - CLI argument validation and execution paths
   - Test argument parsing edge cases
   - Test version reporting
   - Test help output
   - Test invalid argument combinations

2. **`client.py`** - Async MCP operations and error handling
   - Test MCP protocol compliance
   - Test async operation handling
   - Test connection error scenarios
   - Test message parsing/formatting

3. **`tools.py`** - Remaining error handling paths
   - Test edge cases in remaining functions
   - Test error propagation
   - Test input validation

4. **`doi_fetcher.py` and `pubmed_utils.py`** - Remaining edge cases
   - Test network error scenarios
   - Test malformed API responses
   - Test rate limiting behavior

### Testing Strategy Guidelines

#### Unit Tests (No External Dependencies)
- Test pure functions with controlled inputs
- Test error handling with invalid inputs
- Test edge cases and boundary conditions
- Use temporary files that are properly cleaned up
- Ensure cross-platform compatibility

#### Integration Tests (External APIs)
- Mark with `@pytest.mark.external_api`
- Test real API interactions
- Test with known good data sources
- Handle API unavailability gracefully
- Test network error scenarios

#### File Handling Best Practices
- Use `tempfile` module for cross-platform temporary files
- Always clean up in `finally` blocks or use context managers
- Test file cleanup behavior
- Handle permission errors gracefully

#### Fixtures Strategy
- Create fixtures for test data (DOIs, PMIDs, etc.)
- Create fixtures for temporary directories
- Share common setup across related tests
- Keep fixtures simple and focused

### Excluded Files
Per user direction, these files are not being tested:
- `src/artl_mcp/__init__.py`
- `src/artl_mcp/__main__.py` 
- `src/artl_mcp/_version.py`

### Branch and Automation
- **Branch**: `126-improve-unit-tests` (created via GitHub CLI)
- **Makefile targets**: `test`, `test-coverage`, `test-unit`, `test-external-api`
- **GitHub Actions**: Updated to explicitly mention pytest usage
- **Coverage tool**: pytest-cov configured in pyproject.toml

### Key Quote from User
> "i want to covery every function in every source file except for empty or near-empty files like __init__.py. i don't want to skip anything. we shoudl test success and failure cases."

This comprehensive testing approach ensures robust, reliable code that works across different environments while maintaining high confidence in actual functionality rather than mocked behavior.



# 🔄 Additional Notes, Decisions, and Repository Goals

## 🧪 Testing Strategy and Coverage Overview

This document outlines the testing strategy, rationale, and current implementation status for our Python project. It incorporates BBOP best practices and addresses tradeoffs between test coverage, developer workflow, and CI automation.

---

## ✅ Testing Strategy

We support multiple `make` targets to accommodate fast development cycles, comprehensive CI testing, and granular test runs:

### Primary Targets

| Target             | Description                                            | Use Case                           |
|--------------------|--------------------------------------------------------|------------------------------------|
| `make test`        | Runs all tests **with coverage enabled**              | Default for developers             |
| `make test-coverage` | Full test suite + coverage reports (identical to `test`) | Used in CI, local audits           |
| `make all`         | Comprehensive build check, includes `test-coverage`   | Default in GitHub Actions          |

### Granular Targets

| Target                  | Description                                     | Use Case                          |
|-------------------------|-------------------------------------------------|-----------------------------------|
| `make test-unit`        | Runs only unit tests; excludes external APIs   | Fast dev feedback (~1s runtime)   |
| `make test-external-api` | Runs only external API integration tests       | Checks API dependencies           |

**Rationale**:
- Developers get fast iteration (`test-unit`)
- External integrations tested separately, cleanly (`test-external-api`)
- CI ensures full coverage via `test-coverage` or `make all`

---

## 🧠 Design Rationale

### Tradeoffs Considered

#### ✅ Advantages of Multiple Targets

- **Speed**: `test-unit` provides fast feedback (<1s)
- **Flexibility**: Avoid flaky external APIs during development
- **CI Optimization**: PRs can use `test-unit`, `main` branch runs full coverage
- **Debugging**: Failures in external APIs are easier to isolate

#### ❌ Disadvantages

- Slightly more complexity
- Requires documentation and developer awareness
- Potential confusion about which target is canonical (→ resolved by having `make test` always run full coverage)

### Final Decision

- **Default developer target**: `make test` (includes coverage)
- **Granular options** for advanced/test-specific workflows

This approach balances developer speed and CI quality, aligning with [BBOP Best Practices](https://github.com/berkeleybop/bbop/blob/master/docs/dev-practices.md):
> "Commit early, commit often" and "Main branch should never fail"

---

## 🔍 TESTING QUESTIONS & ACTIONS

### Do We Need `__main__.py` and `main.py`?

- ❗ **Decision pending**: Clarify usage and purpose of both.
- 🎯 **Goal**: There should be one entry point for CLI execution, and it should be testable and covered (if practical).
- 🔧 **Recommendation**: Consider consolidating under `cli.py` if applicable.

---

### Don’t Check `_version.py` for Coverage

- ✅ Marked as excluded from coverage.
- ❗ We still need a **clean strategy** for:
  - How `_version.py` is generated (manual? automated?)
  - When it is included/committed
  - Whether it is injected in build steps only

---

### Why Are Some Tests Skipped?

| Reason                  | Example/Test                          | Notes                                     |
|-------------------------|----------------------------------------|-------------------------------------------|
| API returned "not available" | `test_get_abstract_from_pubmed_id` | API didn’t provide expected content       |
| Inconsistent availability | `test_get_pmcid_text`                | Avoiding false test failures              |

🔧 **Goal**: Replace fragile skips with:
- Stable inputs
- `@pytest.mark.external_api`
- Fixtures or mock servers when necessary

---

### Do We Cover Valid and Invalid Input Cases?

- ⚠️ Audit required.
- 🎯 **Target**: Every function should be tested with:
  - Valid input (happy path)
  - Invalid/malformed input
  - Missing fields, empty values, etc.
  - Unexpected data types or edge behavior

---

### Are All `unittest` Classes Removed?

- ✅ Conversion in progress or completed.
- 🎯 Ensure:
  - No `unittest.TestCase` subclasses remain
  - Only `pytest` idioms are used (fixtures, decorators, plain `assert`)

---

### Are We Using `pytest` Decorators Consistently?

| Decorator                     | Usage                               | Status    |
|-------------------------------|--------------------------------------|-----------|
| `@pytest.mark.external_api`   | API integration tests                | 🔧 Needs audit |
| `@pytest.mark.parametrize`    | Input combinations                   | ⚠️ Underused |
| `@pytest.mark.skipif(...)`    | Env-based skips                      | 🔧 Use more consistently |

---

### Should We Minimize or Eliminate Mocks?

| Principle              | Status |
|------------------------|--------|
| Only mock when real behavior is unreliable or costly | ✅ Agreed |
| Prefer small real test PDFs over mocking file behavior | 🔧 In progress |
| Minimize mocking `requests.get` unless testing edge cases | ⚠️ Mixed |
| Use `pytest` fixtures and test assets | ✅ Encouraged |

---

## 🎯 BROADER REPO GOALS (Beyond Testing)

These are the core functional objectives of the repository. These goals are **not all fully implemented** yet, but they should guide architecture, tests, and CLI behavior.

### Input Expectations

- ✅ Accept **DOI** or **PMID** as starting point
- 🆗 Also accept: **PMCID**, **DOI URLs**
- ❗ Clarify: Should users include prefixes (e.g., `doi:`) or not?
  - 🔧 Decide and enforce consistent parsing

### ID Normalization and Conversion

- 🔧 Support:
  - `pmid ↔ doi`
  - `doi → pmcid`
  - `doi-url → doi`
- ✅ Test each conversion path
- ⚠️ Include handling for invalid/missing IDs

### Metadata Retrieval

- ✅ Retrieve as much metadata as possible for any valid ID
- ✅ Abstracts **can** be included in metadata, but:
  - 🎯 Abstract access must also be available **as a separate operation**

### Abstract Handling

- ✅ Get abstract from **DOI**, **PMID**, **PMCID**, **DOI URL**
- ✅ Save abstract to file
- ✅ Expose dedicated methods (not just side effects from metadata retrieval)
- 🔧 Add tests for malformed abstract responses or missing abstracts

### Fulltext (Non-PDF) Retrieval

- ✅ Get machine-readable full text (e.g., BioC, XML)
- ✅ Save to file
- 🎯 Allow format conversion (e.g., XML → plain text)

### PDF Handling

- 🔧 Locate best PDF URL for any ID type
- ✅ Fetch PDF as a file
- ⚠️ Choose and document library for PDF-to-text conversion
  - Currently: `pdfminer.six`
  - ✅ Test real conversion with small test PDFs
- ⚠️ Handle missing or bad PDFs gracefully

### Supplementary Data

- ❗ Define what qualifies as “supplementary” (e.g., Excel files, figures, archives)
- ⚠️ Add method(s) for retrieval
- 🎯 Take cues from [`crawl-first`](https://github.com/monarch-initiative/crawl-first) for scraping patterns and fallback logic

### Integration with `crawl-first` Patterns

- 📌 Inspiration:
  - Stable fallback scraping
  - Multi-step resolution logic
  - Caching of API and scrape results
- 🎯 Design system so metadata/fulltext can be:
  - Retrieved → cached → converted → stored → reasoned upon

### ✅ Summary Checklist

| Goal or Concern                          | Status           |
|------------------------------------------|------------------|
| Clear separation of test targets         | ✅ Done           |
| `_version.py` excluded from coverage     | ✅ Done           |
| `__main__.py` vs. `main.py` clarified    | ❗ Needs decision |
| CLI commands tested                      | ❌ Not yet        |
| Use real PDFs in PDF tests               | 🔧 In progress    |
| Abstract and metadata separately retrievable | ✅ Done        |
| Fulltext and abstract written to file   | ✅ Implemented    |
| Prefix use in IDs clearly documented     | ❗ In progress    |
| Supplementary file retrieval             | ❌ Not yet        |


---

# 🧼 Code Quality, Style, and Automation Standards

## ✅ Universal Checks and Enforcement

All linters, formatters, type checkers, and dependency analyzers must be consistently run across both `src/` and `tests/` directories. This includes:

- ✅ `ruff` or `flake8` for linting
- ✅ `mypy` for type checking
- ✅ `pyright` or similar for static type analysis
- ✅ `black` or `ruff format` for code reformatting
- ✅ `deptry` or `pip-audit` for dependency analysis

These must be integrated into local development *and* CI workflows.

## 🧾 Docstring Standards

- All public functions and modules must have **docstrings in the BBOP style**.
- Format and tone should be consistent with BBOP's guidance.

Reference:  
📘 **BBOP Best Practices**  
https://raw.githubusercontent.com/berkeleybop/berkeleybop.github.io/refs/heads/master/best_practice/index.md

## 📦 UV Environment Notice

This is a **`uv`-based repository**.

- All package installation and resolution is done using [`uv`](https://github.com/astral-sh/uv).
- Coding assistants, build tools, and CI scripts must be reminded of this repeatedly to avoid regressions to `pip` or `poetry`.

✅ Developers must default to:
```bash
uv pip install -e .  # For editable install
uv venv .venv        # For environment creation
```

---

