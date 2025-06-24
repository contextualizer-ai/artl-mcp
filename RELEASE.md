# PyPI Release Guide for artl-mcp

This document provides step-by-step instructions for manually creating a PyPI release of the artl-mcp package.

This is a temporary strategy to be replaced with GitHub action, dynamic version based PyPI releasing, triggered by GH releases.

## Prerequisites

1. **PyPI Account & API Token**
   - Create an account at https://pypi.org
   - Generate an API token at https://pypi.org/manage/account/token/
   - Store the token securely (you'll need it for each release)

2. **Development Environment**
   - Ensure you have `uv` installed and the project environment set up
   - Run `make dev` to install all development dependencies

## Environment Variables Setup

Before releasing, you must set up authentication environment variables in your terminal. Use the `artl-mcp-2025-06-24` key, which you can get from @turbomam.
```bash
export TWINE_USERNAME="__token__"
export TWINE_PASSWORD="pypi-AgEI...your-actual-token-here"
```

**Important Notes:**
- Use quotes around the token value
- The username is literally `__token__` (with underscores)
- These variables are session-specific and need to be set each time you open a new terminal

### Alternative: Store in Shell Profile

For convenience, you can add these to your shell profile (e.g., `~/.zshrc` or `~/.bashrc`):

```bash
# Add to ~/.zshrc or ~/.bashrc
export TWINE_USERNAME="__token__"
export TWINE_PASSWORD="pypi-your-actual-token-here"
```

Then run `source ~/.zshrc` (or restart your terminal).

## Release Process

### 1. Prepare Your Code

1. **Commit all changes:**
   ```bash
   git add .
   git commit -m "Prepare for release"
   ```

2. **Ensure you're on the main branch:**
   ```bash
   git checkout main
   git pull origin main
   ```

3. **Run tests to ensure everything works:**
   ```bash
   make test
   ```

### 2. Choose Version Number

Check existing tags to avoid conflicts:
```bash
git tag --list
```

Choose the next appropriate version following [Semantic Versioning](https://semver.org/):
- **Patch release** (bug fixes): `v0.8.1`
- **Minor release** (new features): `v0.9.0`
- **Major release** (breaking changes): `v1.0.0`

### 3. Create and Push Version Tag

```bash
# Replace v0.8.1 with your chosen version
git tag v0.8.1
git push origin v0.8.1
```

### 4. Build and Upload to PyPI

Run the complete release workflow:
```bash
make release
```

This single command runs:
1. `make clean` - removes build artifacts
2. `make test` - runs test suite
3. `make build` - builds wheel and source distribution
4. `make upload` - uploads to PyPI

### Alternative: Step-by-Step

If you prefer to run each step individually:

```bash
make clean    # Clean build artifacts
make test     # Run tests
make build    # Build package
make upload   # Upload to PyPI
```

### 5. Verify Release

1. **Check PyPI page:**
   Visit https://pypi.org/project/artl-mcp/ to confirm your release is live

2. **Test installation:**
   ```bash
   pip install artl-mcp==0.8.1  # Use your version number
   ```

## TestPyPI (Optional Testing)

Before uploading to the main PyPI, you can test on TestPyPI:

1. **Set TestPyPI environment variables:**
   ```bash
   export TWINE_USERNAME="__token__"
   export TWINE_PASSWORD="pypi-your-testpypi-token-here"
   ```

2. **Upload to TestPyPI:**
   ```bash
   make upload-test
   ```

3. **Test installation from TestPyPI:**
   ```bash
   pip install --index-url https://test.pypi.org/simple/ artl-mcp==0.8.1
   ```

## Troubleshooting

### Version Issues

If you see errors like "local versions not allowed":
- Ensure you're exactly on a tagged commit with no uncommitted changes
- Check `git status` - working tree should be clean
- The `src/artl_mcp/_version.py` file should be auto-generated and ignored by git

### Authentication Issues

If you get "Username/Password authentication not supported":
- Verify environment variables are set: `echo $TWINE_USERNAME`
- Ensure you're using `__token__` as username, not your PyPI username
- Check that your token hasn't expired

### Build Issues

If the build fails:
- Run `make clean` to remove stale artifacts
- Ensure all dependencies are installed: `make dev`
- Check that your `pyproject.toml` is valid

## Makefile Targets Reference

- `make all` - Complete development workflow (clean, install, test, lint, build)
- `make clean` - Remove build artifacts and cache files
- `make build` - Build wheel and source distribution
- `make test` - Run test suite
- `make test-coverage` - Run tests with coverage report
- `make upload` - Upload to PyPI (requires environment variables)
- `make upload-test` - Upload to TestPyPI
- `make release` - Complete release workflow (clean, test, build, upload)
- `make lint` - Run code linting with ruff
- `make format` - Format code with black

## Version Management

This project uses `hatch-vcs` for automatic version management:
- Versions are determined from git tags
- Development versions include commit hashes when between tags
- Only tagged commits produce clean version numbers suitable for PyPI
- The `_version.py` file is auto-generated and should not be committed

## Best Practices

1. **Always test before releasing** - Run the full test suite
2. **Use semantic versioning** - Follow semver.org conventions
3. **Test on TestPyPI first** - For major releases or when unsure
4. **Keep a clean git history** - Commit all changes before tagging
5. **Document changes** - Update README.md or CHANGELOG.md as needed
6. **Verify the release** - Check the PyPI page and test installation

## Emergency Procedures

### Fixing a Bad Release

If you need to fix a release:

1. **Never delete/modify existing PyPI releases** - they may be in use
2. **Create a new patch version** instead:
   ```bash
   git tag v0.8.2  # Next patch version
   git push origin v0.8.2
   make release
   ```

### Revoking a Release

If you must remove a release:
1. Go to https://pypi.org/project/artl-mcp/
2. Log in and navigate to your release
3. Use the "Options" → "Delete" feature (use sparingly)

---

**Note:** This guide assumes you have the necessary permissions to push to the repository and upload to PyPI. Contact the project maintainers if you need access.
