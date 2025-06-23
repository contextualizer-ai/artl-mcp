# All Roads to Literature

An MCP for retrieving scientific literature metadata and content using PMIDs, DOIs, and other identifiers.

## Features

- Retrieve metadata for scientific articles using DOIs
- Fetch abstracts from PubMed using PMIDs
- MCP-based architecture for easy extensibility

## Installation

### Prerequisites

- Python 3.11 or higher
- uv (optional but recommended)

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/all-roads-to-literature.git
   cd all-roads-to-literature
   ```

2. Install with uv (recommended):
   ```bash
   uv venv
   uv pip install -e .
   ```

   Or with standard pip:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -e .
   ```

## Usage

### Starting the MCP Server

To start the MCP server:

```bash
uv run artl --server
```

This will start the server in the current terminal. The server provides access to all registered tools through FastMCP's interface.

### Running the Tests

```bash
uv run pytest tests/
```

## Architecture

The project follows this structure:

- `main.py`: Entry point that creates and configures the MCP server
- `tools.py`: Contains the tool implementations that the MCP server exposes


