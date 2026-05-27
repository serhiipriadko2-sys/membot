# Supabase Integration Guide

## Overview

Membot now integrates with Supabase as its primary persistent storage layer for:
- Hypothesis tracking with Bayesian probabilities
- Immutable event logging
- Observer gate alerts
- System health monitoring

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Membot Core   │────▶│  Supabase Client │────▶│    Supabase     │
│   (Analytics)   │     │  (Python SDK)    │     │   (PostgreSQL)  │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌──────────────────┐
                        │   Migrations     │
                        │   (SQL Scripts)  │
                        └──────────────────┘
```

## Setup Instructions

### 1. Prerequisites

- Supabase account and project created
- Python 3.11+ installed
- Dependencies installed: `pip install supabase pydantic-settings python-dotenv`

### 2. Configure Environment Variables

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` and replace `YOUR_NEW_SECRET_KEY_HERE` with your actual Supabase service role key:

```bash
SUPABASE_URL=https://catntmobfcenkhkodnqv.supabase.co
SUPABASE_KEY=sb_secret_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
SUPABASE_PROJECT_REF=catntmobfcenkhkodnqv
```

**⚠️ SECURITY WARNING:**
- Never commit `.env` to version control
- Rotate your keys immediately if they are ever exposed
- Use environment-specific keys for development/staging/production

### 3. Apply Database Migrations

#### Option A: Via Supabase Dashboard (Recommended)

1. Go to [Supabase Dashboard](https://app.supabase.com)
2. Select your project: `catntmobfcenkhkodnqv`
3. Navigate to **SQL Editor**
4. Copy the contents of `migrations/001_initial_schema.sql`
5. Paste into the editor and click **Run**

#### Option B: Via Supabase CLI

```bash
# Install Supabase CLI
npm install -g supabase

# Link to your project
supabase link --project-ref catntmobfcenkhkodnqv

# Push migrations
supabase db push
```

#### Option C: Via Python Script (Limited)

```bash
python scripts/apply_migrations.py
```

Note: This script provides guidance but cannot execute all SQL statements directly due to API limitations.

### 4. Verify Connection

Test the integration:

```bash
python src/storage/supabase_client.py
```

Expected output:
```
[FACT] Connected to Supabase project: catntmobfcenkhkodnqv
[INTERP] Connection OK, but tables not initialized yet
✓ Supabase connection successful
```

If tables were created successfully:
```
[FACT] Connected to Supabase project: catntmobfcenkhkodnqv
[FACT] Connection successful - health check table exists
✓ Supabase connection successful
```

## Usage

### Initialize Client

```python
from src.storage.supabase_client import get_supabase_client

client = get_supabase_client()
```

### Store Hypothesis

```python
client.insert_hypothesis(
    hypothesis_id="HYP-001",
    name="Liquidity Spike Detection",
    probability=0.85,
    metadata={
        "source": "wallet_swaps",
        "confidence": 0.92,
        "tags": ["liquidity", "spike"]
    }
)
```

### Log Event

```python
client.insert_event(
    event_type="hypothesis_updated",
    payload={
        "hypothesis_id": "HYP-001",
        "old_probability": 0.75,
        "new_probability": 0.85
    },
    source="bayesian_engine"
)
```

### Retrieve Data

```python
# Get all hypotheses
hypotheses = client.get_hypotheses(limit=50)

# Get recent events
events = client.get_recent_events(event_type="hypothesis_updated", limit=20)
```

## Database Schema

### Tables

| Table | Purpose |
|-------|---------|
| `_membot_health_check` | Connection verification |
| `membot_hypotheses` | Store hypotheses with probabilities |
| `membot_events` | Immutable event log |
| `membot_alerts` | Observer gate threshold alerts |

### Key Fields

**membot_hypotheses:**
- `hypothesis_id`: Unique identifier (TEXT)
- `probability`: Bayesian probability (FLOAT, 0-1)
- `status`: active/confirmed/rejected/paused
- `metadata`: Flexible JSONB for additional data

**membot_events:**
- `event_type`: Categorization (TEXT)
- `payload`: Event data (JSONB)
- `timestamp`: Auto-generated (TIMESTAMPTZ)

## MCP Server Integration

Membot supports Supabase MCP (Model Context Protocol) for enhanced AI-assisted development:

```bash
# Add MCP server (run in local terminal with Claude CLI)
claude mcp add --scope project --transport http supabase \
  "https://mcp.supabase.com/mcp?project_ref=catntmobfcenkhkodnqv"

# Authenticate
claude /mcp

# Optional: Install Agent Skills
npx skills add supabase/agent-skills
```

This enables:
- Natural language queries to database
- AI-assisted migration generation
- Automated schema documentation

## Troubleshooting

### Connection Errors

**Error:** `Failed to connect to Supabase: Invalid API key`
- **Solution:** Verify `SUPABASE_KEY` in `.env` is correct and not expired

**Error:** `relation "membot_hypotheses" does not exist`
- **Solution:** Apply migrations first (see Step 3)

### Permission Issues

**Error:** `permission denied for table`
- **Solution:** Check RLS policies in Supabase Dashboard → Authentication → Policies

### Migration Failures

**Error:** `syntax error at or near ...`
- **Solution:** Ensure you're using PostgreSQL-compatible SQL syntax
- Check Supabase logs in Dashboard → Logs

## Next Steps

1. **Enable Row Level Security (RLS)** for production deployments
2. **Set up automated backups** in Supabase Dashboard
3. **Configure monitoring alerts** for database performance
4. **Implement data retention policies** for event logs
5. **Add integration tests** for database operations

## References

- [Supabase Documentation](https://supabase.com/docs)
- [Supabase Python Client](https://github.com/supabase-community/supabase-py)
- [PostgreSQL JSONB Documentation](https://www.postgresql.org/docs/current/datatype-json.html)
