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

Local verification on 2026-05-19:
- npm `latest` for `@agentmemory/agentmemory` was `0.9.21`
- Windows required `iii-engine` / `iii.exe` `0.11.2` on PATH before the server could start
- `agentmemory --version` may initialize runtime services; use `npm list -g @agentmemory/agentmemory --depth=0` for a non-server package check

Primary upstream references:
- https://github.com/rohitg00/agentmemory
- https://www.agent-memory.dev/

## Recommended local setup

Install once:

```bash
npm install -g @agentmemory/agentmemory
```

Windows dependency note:

```powershell
# If startup reports missing iii-engine, install iii.exe 0.11.2 from:
# https://github.com/iii-hq/iii/releases/tag/iii%2Fv0.11.2
# Put iii.exe somewhere on PATH, for example:
# C:\Users\<you>\.local\bin\iii.exe
iii --version
```

Start the server:

```bash
agentmemory
```

Run the demo in a second terminal:

```bash
agentmemory demo
```

Demo acceptance:
- runtime PASS if the command completes, seeds sessions, and keyword searches return results
- semantic recall PASS only if `agentmemory status` reports a real embedding provider, not `bm25-only`
- without provider keys, `Provider: noop` and `Embeddings: bm25-only` are expected; do not treat paraphrase search as proven

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

PowerShell:

```powershell
Invoke-RestMethod http://localhost:3111/agentmemory/health
```

If this fails, run:

```bash
agentmemory doctor
```

Status check:

```bash
agentmemory status
```

For full semantic recall, configure an embedding provider in `~/.agentmemory/.env` without committing secrets.

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

## Codex MCP config

Preferred additive CLI path:

```powershell
codex mcp add agentmemory --env AGENTMEMORY_URL=http://localhost:3111 -- npx -y @agentmemory/mcp
codex mcp get agentmemory
codex mcp list
```

Manual TOML equivalent:

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

Host note: VS Code workspace MCP files can use `servers` instead of `mcpServers`; do not paste the generic JSON block into that shape without adapting it.

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
