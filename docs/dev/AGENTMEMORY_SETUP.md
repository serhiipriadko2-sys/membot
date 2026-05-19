# AgentMemory setup for membot

## Status

AgentMemory is allowed as an optional local memory layer for development agents.
It is not a source of truth for membot.

Use it for recall:
- why an RPC/backoff patch exists
- what a previous artifact QA verdict was
- what schema quirks were found in `entry_exit_hypothesis_tests.csv`
- what Supabase Bridge / Iskra Forge decisions were made

Do not use it for canon:
- no API keys or secrets
- no wallet private keys
- no service-role tokens
- no automatic governance changes
- no trading signals without raw artifacts

Project rule:

```text
Memory suggests. Repository verifies. Artifacts decide.
```

## Source notes

AgentMemory upstream documents:
- global install via `npm install -g @agentmemory/agentmemory`
- server start via `agentmemory` or `npx @agentmemory/agentmemory`
- REST on `http://localhost:3111`
- viewer on `http://localhost:3113`
- MCP shim via `@agentmemory/mcp`
- iii bridge functions such as `mem::remember`, `mem::observe`, `mem::context`, `mem::smart-search`, `mem::forget`

Primary upstream references:
- https://github.com/rohitg00/agentmemory
- https://www.agent-memory.dev/

## Recommended local setup

Install once:

```bash
npm install -g @agentmemory/agentmemory
```

Start the server:

```bash
agentmemory
```

Run the demo in a second terminal:

```bash
agentmemory demo
```

Open the viewer:

```text
http://localhost:3113
```

Zero-install alternative:

```bash
npx -y @agentmemory/agentmemory@latest
```

Reason: `npx` can serve stale cached versions, so prefer either global install or explicit `@latest`.

## Health check

```bash
curl http://localhost:3111/agentmemory/health
```

If this fails, run:

```bash
agentmemory doctor
```

## MCP JSON config

Merge this into an existing `mcpServers` object. Do not replace the whole config file.

Local-only minimal config:

```json
{
  "mcpServers": {
    "agentmemory": {
      "command": "npx",
      "args": ["-y", "@agentmemory/mcp"],
      "env": {
        "AGENTMEMORY_URL": "http://localhost:3111"
      }
    }
  }
}
```

Remote/reverse-proxy capable config:

```json
{
  "mcpServers": {
    "agentmemory": {
      "command": "npx",
      "args": ["-y", "@agentmemory/mcp"],
      "env": {
        "AGENTMEMORY_URL": "${AGENTMEMORY_URL}",
        "AGENTMEMORY_SECRET": "${AGENTMEMORY_SECRET}"
      }
    }
  }
}
```

The `${VAR}` values are inherited from the shell at MCP-server launch. Keep them out of git.

## Codex TOML config

```toml
[mcp_servers.agentmemory]
command = "npx"
args = ["-y", "@agentmemory/mcp"]

[mcp_servers.agentmemory.env]
AGENTMEMORY_URL = "http://localhost:3111"
```

Remote variant:

```toml
[mcp_servers.agentmemory]
command = "npx"
args = ["-y", "@agentmemory/mcp"]

[mcp_servers.agentmemory.env]
AGENTMEMORY_URL = "${AGENTMEMORY_URL}"
AGENTMEMORY_SECRET = "${AGENTMEMORY_SECRET}"
```

## Programmatic iii access

AgentMemory exposes memory operations over the iii bridge.

Install SDK:

```bash
pip install iii-sdk
```

Python example:

```python
from iii import register_worker

iii = register_worker("ws://localhost:49134")
iii.connect()

iii.trigger({
    "function_id": "mem::smart-search",
    "payload": {
        "project": "membot",
        "query": "why did we add RPC backoff"
    },
})
```

## What to remember for membot

Good memories:

```text
Project: membot
Type: engineering decision
Content: PR #23 added RPC backoff/resumable transaction fetch because a 600-signature artifact produced only 2 transaction payloads due to public Solana RPC 429 errors.
Evidence: docs/RPC_BACKOFF_AND_SUPABASE_BRIDGE.md
```

```text
Project: membot
Type: UI decision
Content: Navigation was simplified to Iskra Forge + Data Bridge because Streamlit auto-listed every file under app/pages and produced duplicate top-level pages.
Evidence: docs/ui/SINGLE_FORGE_NAVIGATION.md
```

```text
Project: membot
Type: artifact schema
Content: entry_exit_hypothesis_tests.csv may use hypothesis_id for signal name and support_rate_pct for score.
Evidence: app/pages/00_Iskra_Forge.py
```

Bad memories:

```text
SUPABASE_SERVICE_ROLE_KEY=...
SOLANA_RPC_URL with paid API key
private wallet key / seed phrase
BUY token X when signal Y appears
```

## Truth ladder

1. Raw artifacts: `data/raw`, `data/processed`, reports, zip receipts
2. Repository docs and code
3. ADR / governance records
4. AgentMemory recall
5. Chat memory

If AgentMemory says something that conflicts with repo or artifact evidence, repo/artifact wins.

## Maintenance

Start:

```bash
agentmemory
```

Stop:

```bash
agentmemory stop
```

Diagnostics:

```bash
agentmemory doctor
```

Upgrade intentionally:

```bash
npx @agentmemory/agentmemory upgrade
```

Upgrades can mutate local runtime dependencies; do not run them inside CI unless explicitly planned.

## Security checklist

- [ ] No secrets committed to repo
- [ ] `AGENTMEMORY_SECRET` only in shell/host secret store
- [ ] `AGENTMEMORY_URL` points to local/private endpoint unless intentionally remote
- [ ] Remote endpoint is protected before exposing beyond localhost
- [ ] Memory entries cite repo docs/artifacts when they affect engineering decisions
- [ ] Memory recall never becomes BUY/SELL logic

## Rollback

```bash
agentmemory stop
agentmemory remove
```

Then remove the `agentmemory` block from the local MCP host config.
