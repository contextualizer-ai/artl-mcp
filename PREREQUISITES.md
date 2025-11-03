# Prerequisites for ARTL-MCP

This guide covers everything you need to get started with ARTL-MCP.

## Quick Start Requirements

### For CLI Usage (Simplest)
- **Python**: 3.11 or later
- **uv**: Python package installer
- **Internet**: For API access to literature databases

That's it! You can use artl-mcp from the command line with just these.

### For MCP Integration (AI Assistant)
- Everything above, PLUS:
- **MCP-compatible client**: Claude Desktop, Goose, Zed, or similar

### For Development (Optional)
- Everything above, PLUS:
- **Git**: Version control
- **Make**: Build automation
- **Claude Code CLI**: Optional, only for `make claude-demos-all` testing

---

## Installing Python 3.11+

### Check Current Version

```bash
python3 --version
# Should show Python 3.11.x or later
```

### Install Python

**macOS (Homebrew):**
```bash
brew install python@3.11
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3.11 python3.11-venv
```

**Windows:**
- Download from https://www.python.org/downloads/
- ✅ **Important**: Check "Add Python to PATH" during installation

**Verify Installation:**
```bash
python3 --version
# Should show 3.11 or later
```

---

## Installing uv

uv is a fast Python package installer and manager.

**Install uv (all platforms):**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Or with pip:**
```bash
pip install uv
```

**Verify:**
```bash
uv --version
```

**More info:** https://github.com/astral-sh/uv

---

## MCP Client Setup

### What is MCP?

The **Model Context Protocol (MCP)** allows AI assistants to access external tools. ARTL-MCP provides literature search tools to MCP-compatible AI assistants.

### Supported MCP Clients

You can use **any** of these:

1. **Claude Desktop** ⭐ (Recommended, best tested)
2. **Goose Desktop** ✅ (Supported)
3. **Zed Editor** ✅ (Code editor with MCP)
4. **Continue** ✅ (VS Code extension)
5. **Any MCP-compatible tool**

> **Important**: You do NOT need Claude Code CLI for MCP usage! That's only for optional development testing.

---

## Claude Desktop Setup

### 1. Install Claude Desktop

**Download:**
- https://claude.ai/download (macOS and Windows)

**Requirements:**
- Internet connection
- Anthropic account (check https://claude.ai/pricing for current plans)

### 2. Locate MCP Configuration File

**macOS:**
```
~/Library/Application Support/Claude/claude_desktop_config.json
```

**Windows:**
```
%APPDATA%\Claude\claude_desktop_config.json
```

**Create if it doesn't exist:**

```bash
# macOS
mkdir -p ~/Library/Application\ Support/Claude
touch ~/Library/Application\ Support/Claude/claude_desktop_config.json

# Windows (PowerShell)
New-Item -Path "$env:APPDATA\Claude" -ItemType Directory -Force
New-Item -Path "$env:APPDATA\Claude\claude_desktop_config.json" -ItemType File
```

### 3. Add ARTL-MCP Configuration

**Option 1: No local installation (Recommended)**

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "artl-mcp": {
      "command": "uvx",
      "args": ["artl-mcp"],
      "env": {
        "ARTL_EMAIL_ADDR": "your@university.edu"
      }
    }
  }
}
```

**Option 2: Local development**

For developers working on artl-mcp:

```json
{
  "mcpServers": {
    "artl-mcp": {
      "command": "uv",
      "args": ["run", "artl-mcp"],
      "cwd": "/path/to/artl-mcp",
      "env": {
        "ARTL_EMAIL_ADDR": "your@university.edu"
      }
    }
  }
}
```

### 4. Restart Claude Desktop

**Important**: You MUST restart Claude Desktop after editing the config file.

### 5. Verify It Works

Open Claude Desktop and try:

```
"Search Europe PMC for papers about CRISPR"
```

If working, you'll see results from the literature database.

---

## Other MCP Clients

### Goose Desktop

Goose supports MCP through its configuration system. Add to Goose's MCP config:

```json
{
  "mcpServers": {
    "artl-mcp": {
      "command": "uvx",
      "args": ["artl-mcp"],
      "config": {
        "ARTL_EMAIL_ADDR": "your@university.edu"
      }
    }
  }
}
```

**Config location**: Check Goose documentation for platform-specific paths.

### Zed Editor

Zed has built-in MCP support. Configuration varies by version - see Zed's MCP documentation.

### Continue (VS Code)

Continue extension supports MCP servers. See Continue's documentation for configuration.

### CBORG (LBL Users)

If you have access to LBL's CBORG service, you can use it to fund Claude Desktop API usage. See [CBORG.md](CBORG.md) for:
- Official CBORG documentation links
- Spending monitoring using CBORG APIs
- Quick budget checks

---

## Claude Code CLI (Optional - Development Only)

> **⚠️ Not Required**: Claude Code CLI is ONLY needed for running `make claude-demos-all` development tests. Normal users don't need this.

### What is Claude Code?

Claude Code is Anthropic's command-line interface, used in this project for optional integration testing.

### When Do You Need It?

**You need Claude Code CLI if:**
- You're developing artl-mcp
- You want to run `make claude-demos-all`
- You're testing MCP server functionality

**You DON'T need it for:**
- ✅ Using artl-mcp CLI
- ✅ Using artl-mcp with Claude Desktop
- ✅ Using artl-mcp with any MCP client
- ✅ Normal end-user workflows

### Installation (If Needed)

```bash
npm install -g @anthropic-ai/claude-code
# or
yarn global add @anthropic-ai/claude-code
```

### Authentication

Requires an Anthropic API key:

1. Get key: https://console.anthropic.com/
2. Set environment variable:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
# Add to ~/.bashrc or ~/.zshrc for persistence
```

### Pricing

Claude Code CLI uses pay-per-use pricing:
- **Typical demo cost**: $0.05-0.20 per demo
- **Full `make claude-demos-all`**: ~$1-2

See https://www.anthropic.com/pricing for current rates.

---

## Cost & Funding Information

### CLI Usage (100% FREE)

**No AI or LLM service required:**
```bash
uvx --from artl-mcp artl-cli get-doi-metadata --doi "..."
```
- ✅ Completely free - Direct API calls to CrossRef, Europe PMC, PubMed
- ✅ No AI account or API key needed
- ✅ No usage fees
- ⚠️ Rate-limited by source APIs (typically 1000 requests/hour)

### MCP Usage (Requires LLM Service)

**Using artl-mcp with AI assistants requires:**
- An MCP-compatible client (Claude Desktop, Goose, Zed, etc.)
- An account with your chosen LLM service provider
- LLM services typically have usage costs or subscription plans

**Pricing varies by provider:**
- Check https://claude.ai/pricing for Claude Desktop plans
- Check your chosen MCP client's pricing page for costs
- Some may offer trial periods or limited free usage

### Claude Code CLI (Optional Developer Tool)

**Only needed for `make claude-demos-all` testing:**
- Pay-per-use API pricing
- Typical costs: ~$1-2 for all demos (based on current pricing)
- See https://www.anthropic.com/pricing for up-to-date rates
- Not needed for normal CLI or MCP usage

### Important Notes

- **ARTL-MCP itself**: Free and open source
- **Literature APIs**: Free (Europe PMC, CrossRef, PubMed, Unpaywall)
- **CLI usage**: No costs
- **MCP usage**: Costs depend on your chosen LLM service

---

## Email Configuration

Several literature APIs require email addresses for:
- Rate limit identification
- Terms of service compliance
- Access to enhanced features

### How to Provide Email

**Method 1: Environment Variable (Recommended)**
```bash
export ARTL_EMAIL_ADDR="researcher@university.edu"
```

**Method 2: CLI Parameter**
```bash
uvx --from artl-mcp artl-cli get-full-text-from-doi \
  --doi "10.1038/nature12373" \
  --email "researcher@university.edu"
```

**Method 3: MCP Client Config**
```json
{
  "mcpServers": {
    "artl-mcp": {
      "env": {
        "ARTL_EMAIL_ADDR": "your@university.edu"
      }
    }
  }
}
```

**Important**: Use your actual institutional email (university, research institute, or company) for best access to content. The system rejects fake emails like `test@example.com`.

---

## Verification Checklist

### ✅ CLI Works

```bash
uvx --from artl-mcp artl-cli --help
uvx --from artl-mcp artl-cli get-doi-metadata --doi "10.1038/nature12373"
```

Expected: Metadata returned in JSON format

### ✅ MCP Server Works (Local)

```bash
# If you cloned the repo
cd artl-mcp
uv run artl-mcp
```

Expected: Server starts without errors

### ✅ Claude Desktop Integration Works

1. Open Claude Desktop
2. Ask: "Search Europe PMC for CRISPR papers"
3. Expected: Structured results from literature database

If errors:
- Check config file syntax (use jsonlint.com)
- Verify Claude Desktop restarted
- Check logs (macOS: `~/Library/Logs/Claude/`)

### ✅ Claude Code CLI Works (Optional)

```bash
claude --version
make local/claude-demo-rhizosphere.txt
```

Expected: Demo file created with search results

---

## Troubleshooting

### "command not found: python3"
→ Install Python 3.11+ (see above)

### "command not found: uv"
→ Install uv, then restart your shell

### "command not found: claude"
→ Only needed for `make claude-demos-all`. Not required for normal use.

### "ANTHROPIC_API_KEY not set"
→ Only needed for Claude Code CLI (optional)

### "Claude Desktop doesn't see artl-mcp"
→ Check config file location, verify JSON syntax, restart Claude Desktop

### "ModuleNotFoundError" when running locally
→ Run `uv sync` in the artl-mcp directory

---

## Quick Start Paths

### Path 1: Try CLI Immediately (30 seconds)

```bash
# No installation needed with uvx!
uvx --from artl-mcp artl-cli get-doi-metadata --doi "10.1038/nature12373"
```

**Time**: 30 seconds
**Cost**: Free
**Requires**: Python 3.11+, uv

---

### Path 2: Use with Claude Desktop (10 minutes)

1. Install Claude Desktop (5 min)
2. Add MCP config (2 min)
3. Restart Claude Desktop (1 min)
4. Try: "Search Europe PMC for CRISPR papers"

**Time**: 10 minutes
**Cost**: Requires LLM service (check provider pricing)
**Best for**: Natural language queries

---

### Path 3: Full Development Setup (15 minutes)

```bash
git clone https://github.com/contextualizer-ai/artl-mcp.git
cd artl-mcp
uv sync --group dev
uv run artl-cli --help
```

**Time**: 15 minutes
**Cost**: Free
**Best for**: Contributing to artl-mcp

---

## Next Steps

- **For CLI users**: See [README.md](README.md) for command examples
- **For MCP users**: See [USERS.md](USERS.md) for detailed guide
- **For developers**: See [DEVELOPERS.md](DEVELOPERS.md) for contribution guide

## Getting Help

- **Documentation**: Check README.md and USERS.md
- **Issues**: https://github.com/contextualizer-ai/artl-mcp/issues
- **Discussions**: https://github.com/contextualizer-ai/artl-mcp/discussions
