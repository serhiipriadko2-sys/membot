# RPC Provider Strategy

## Problem

The membot forensic pipeline fetches raw Solana transaction data through
JSON-RPC calls (`getSignaturesForAddress`, `getTransaction`).  The public
Solana mainnet endpoint (`api.mainnet-beta.solana.com`) is rate-limited and
frequently blocked from cloud/CI environments (HTTP 403 via proxy or
geo-restriction).

A failed RPC call at step 01 cascades into an entirely empty dataset:
no `signatures_raw.json` → no `transactions_raw.json` → no `wallet_swaps.csv`
→ no `trades_paired.csv` → no audit possible.

## Design

### Health Gate

`scripts/00_check_rpc_health.py` runs **before** the pipeline.  It probes
every configured endpoint and reports:

| Field                     | Meaning                                          |
|---------------------------|--------------------------------------------------|
| `provider`                | Human label for the RPC source                   |
| `reachable`               | Could we reach it at all?                        |
| `http_status`             | HTTP status code of the probe                    |
| `rpc_version`             | `solana-core` version string                     |
| `latest_slot`             | Latest finalized slot (confirms chain sync)      |
| `supports_getTransaction` | Can we fetch full tx data? (some RPCs block this)|
| `latency_ms`              | Round-trip time for `getVersion`                 |
| `rate_limit_hint`         | `x-ratelimit-*` headers if present               |
| `error`                   | Error message if probe failed                    |

Exit codes:
- **0** — at least one provider supports full pipeline ops
- **1** — no endpoint reachable at all
- **2** — reachable but no endpoint supports `getTransaction`

### Provider Priority

Environment variables are checked in this order:

| Priority | Env Var            | Typical Provider        | Notes                          |
|----------|--------------------|-------------------------|--------------------------------|
| 1        | `SOLANA_RPC_URL`   | Any / primary           | Used by `common.py` at runtime |
| 2        | `HELIUS_RPC_URL`   | Helius                  | Free tier: 10 RPS              |
| 3        | `QUICKNODE_RPC_URL`| QuickNode               | Free tier available            |
| 4        | `TRITON_RPC_URL`   | Triton One              | Free tier available            |
| 5        | `CUSTOM_RPC_URL`   | Self-hosted / other     | Anything with Solana JSON-RPC  |
| fallback | (hardcoded)        | api.mainnet-beta.solana.com | Always probed last          |

The pipeline itself (`01_fetch_signatures.py` etc.) reads only
`SOLANA_RPC_URL` via `common.py`.  If a provider fails the health gate,
update `SOLANA_RPC_URL` in `.env` to the best-available working URL.

## Recommended Providers

### Free Tier (good for development / small fetches)

| Provider   | URL pattern                                      | Limits                    |
|------------|--------------------------------------------------|---------------------------|
| **Helius** | `https://mainnet.helius-rpc.com/?api-key=<KEY>`  | 10 req/s, 100k credits/mo |
| **QuickNode** | `https://<slug>.solana-mainnet.quiknode.pro/<TOKEN>` | 15 req/s free plan  |
| **Triton** | `https://<project>.triton.one/<TOKEN>`            | 10 req/s free plan        |

### Paid Tier (reliable for full history replay)

For fetching the entire transaction history of an active wallet (50k+ txs),
a paid plan is strongly recommended to avoid rate-limit throttling:

- Helius Developer ($49/mo): 50 req/s, 2M credits
- QuickNode Build ($49/mo): 25 req/s, unlimited compute
- Triton Pro: custom pricing

### Self-Hosted

Running a local Solana RPC node provides unrestricted access but requires
significant resources (~2TB disk, 512GB RAM for full history).  This is
generally not practical for one-off forensic analysis.

## Setup Instructions

1. Sign up for a provider (Helius recommended for free-tier simplicity).
2. Copy your RPC URL.
3. Add to `.env`:

   ```bash
   SOLANA_RPC_URL=https://mainnet.helius-rpc.com/?api-key=YOUR_KEY
   # Optional: add backups
   HELIUS_RPC_URL=https://mainnet.helius-rpc.com/?api-key=YOUR_KEY
   ```

4. Verify with the health gate:

   ```bash
   python scripts/00_check_rpc_health.py
   ```

5. If the output shows `[PASS]`, proceed with the pipeline:

   ```bash
   python scripts/01_fetch_signatures.py --limit 100
   python scripts/02_fetch_transactions.py
   python scripts/03_normalize_swaps.py
   python scripts/04_pair_trades.py
   ```

## Rate Limiting Strategy

`common.py` sleeps `REQUEST_SLEEP_SECONDS` (default 0.15s ≈ 6.7 req/s)
between calls.  Adjust per provider:

| Provider        | Safe sleep (s) | Effective rate |
|-----------------|----------------|----------------|
| Public mainnet  | 1.0            | 1 req/s        |
| Helius free     | 0.12           | ~8 req/s       |
| Helius paid     | 0.03           | ~30 req/s      |
| QuickNode free  | 0.08           | ~12 req/s      |

## Failure Modes

| Symptom                               | Likely Cause                          | Fix                                |
|---------------------------------------|---------------------------------------|------------------------------------|
| `Tunnel connection failed: 403`       | Proxy/firewall blocking RPC           | Use a different network or provider|
| `HTTP 429 Too Many Requests`          | Rate limit exceeded                   | Increase `REQUEST_SLEEP_SECONDS`   |
| `getTransaction` returns null         | Transaction not yet finalized or pruned| Wait or use archival RPC           |
| `Method not found` on getTransaction  | RPC does not support this method      | Switch to full-featured provider   |
| Connection timeout                    | Network or provider outage            | Retry or switch provider           |
