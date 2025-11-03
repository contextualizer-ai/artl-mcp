# CBORG Usage for LBL Users

**CBORG** (Compute Broker for Research Groups) is LBL's internal service for accessing commercial AI APIs including Claude.

## Official Resources

- **Main site**: https://cborg.lbl.gov/
- **Claude Code setup**: https://cborg.lbl.gov/tools_claudecode/

## Using artl-mcp with CBORG

artl-mcp works with Claude Desktop when you configure Claude Desktop to use CBORG for API access. The artl-mcp CLI itself doesn't require CBORG (it's free and accesses literature databases directly).

**For Claude Desktop + CBORG setup**, see the official CBORG documentation linked above.

## Monitoring Your CBORG Spending

CBORG provides two API endpoints for tracking usage:

### 1. User/Period View (Monthly Budget)

```bash
curl -H "Authorization: Bearer $(cat ~/.cborg-key)" \
  https://api.cborg.lbl.gov/user/info | jq .
```

**Shows:**
- `user_info.spend` - Current period (monthly) spend
- `user_info.max_budget` - Your monthly budget limit
- `user_info.budget_reset_at` - When budget resets (typically 1st of month)
- `keys[]` - All your keys and their individual spend

### 2. Key View (Lifetime Spend)

```bash
curl -H "Authorization: Bearer $(cat ~/.cborg-key)" \
  https://api.cborg.lbl.gov/key/info | jq .
```

**Shows:**
- `info.spend` - Lifetime spend for this specific key
- `info.max_budget` - Hard cap on this key (if set)
- `info.expires` - Key expiration date
- `info.blocked` - Whether key is blocked

### Quick Budget Check

```bash
# Check current period spend vs limit
curl -sS -H "Authorization: Bearer $(cat ~/.cborg-key)" \
  https://api.cborg.lbl.gov/user/info | \
  jq '{spend: .user_info.spend, budget: .user_info.max_budget, reset: .user_info.budget_reset_at}'
```

## Notes

- Spend values may lag by a few seconds after recent API calls
- For detailed CBORG configuration and usage, see https://cborg.lbl.gov/
- For issues with CBORG itself, contact LBL CBORG support (not artl-mcp maintainers)
