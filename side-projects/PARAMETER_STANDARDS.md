# Parameter Usage Standards

## When to Use Positional vs Named Parameters

### ✅ Use Positional Parameters:
- **First 1-2 obvious required parameters only**
```python
# Good - obvious what these are
get_doi_metadata("10.1038/nature12373")
search_papers("CRISPR")
```

### ✅ Use Named Parameters:
- **All function calls with >2 parameters**
- **All boolean parameters** (to avoid confusion)
- **All optional parameters**

```python
# Good - clear intent
search_papers(
    query="CRISPR",
    max_results=10,
    save_file=True,
    save_to="/path/file.json"
)

# Good - boolean parameters always named
get_unpaywall_info(doi="10.1038/test", email="user@email.com", use_strict_mode=False)
```

### ❌ Avoid:
```python
# Bad - unclear what True/False mean
get_unpaywall_info("10.1038/test", "user@email.com", True, False, None)

# Bad - too many positional parameters
search_papers("CRISPR", 10, "relevance", None, True, "/path/file.json")
```

## Function Definition Standard

```python
def function_name(
    # 1. Primary required parameters (1-2 max)
    identifier: str,
    
    # 2. Secondary required parameters  
    email: str,
    
    # 3. Configuration parameters (alphabetical)
    extract_tables: bool = True,
    processing_method: str = "auto",
    
    # 4. Pagination parameters
    offset: int = 0,
    limit: int | None = None,
    
    # 5. File handling (always last)
    save_file: bool = False,
    save_to: str | None = None,
) -> ReturnType:
```

## Boolean Parameter Naming
- Use verb forms: `extract_tables`, `save_file`, `use_strict_mode`
- Avoid ambiguous names: `strict` → `use_strict_mode`