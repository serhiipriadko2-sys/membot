# Membot Wallet Forensics + Supabase/GitHub Audit Dossier

voice=ISKRIV; phase=BUILD; intent=AUDIT+INVESTIGATE

Date: 2026-05-22  
Repo: `serhiipriadko2-sys/membot` / local checkout `c:\github\membot-1`  
Target wallet: `7BNaxx6KdUYrjACNQZ9He26NBFoFxujQMAfNLnArLGH5`  
Supabase project URL: `https://catntmobfcenkhkodnqv.supabase.co`

## Executive Verdict

This repository is a research scaffold with a partially working forensic pipeline. It is not a trading bot, and it does not prove the target wallet algorithm.

Current strongest conclusion:

- [FACT] The Git checkout matches `origin/main` at `3a6cc07c3809845d96c3018c65473216aebd5751`.
- [FACT] The repo has no `supabase/` directory and no tracked `supabase/migrations`; Supabase state cannot be treated as Git-backed yet.
- [FACT] Supabase MCP tools are currently blocked by client handshake timeout. The public MCP endpoint itself answers `401`, which means the network path exists but authenticated tool access is not ready.
- [FACT] Local ignored raw data exists and can be parsed in memory, but only `459 / 1000` fetched transactions are present in the current local raw snapshot.
- [FACT] Public Solana RPC confirms the wallet is active.
- [INTERP] The current partial local sample looks compatible with short-horizon pump/memecoin scalping, but the sample is too incomplete for a final behavioral model.
- [HYP] Pre-buy triggers, Jito usage, slot-order advantage, off-chain signal provenance, and copy-trade profitability remain unproven.

## Evidence Freeze

### Git / Repo

| Check | Result |
|---|---|
| Local HEAD | `3a6cc07c3809845d96c3018c65473216aebd5751` |
| Remote `origin/main` | `3a6cc07c3809845d96c3018c65473216aebd5751` |
| Local branch | `main...origin/main` |
| Dirty state before dossier | `.vscode/mcp.json` modified before this report; not touched or reverted |
| Workflows present | `agent-ci-smoke.yml`, `run_forensic_verification.yml`, `security-history-scan.yml`, `security-scan.yml` |
| Supabase migrations path | missing |

### Environment / Runtime

| Surface | Result |
|---|---|
| `.env` | missing |
| `SUPABASE_URL` / keys | not set in process env |
| `SOLANA_RPC_URL` / Helius / Dune / GMGN keys | not set in process env |
| `python` | resolves first to Windows Store alias; direct `python` command fails |
| `py -3.12` | available |
| `supabase` CLI | not found on PATH |
| `gmgn-cli` | not found on PATH |
| Node/npm/npx | available |

### Artifact Hashes

| Artifact | Bytes | SHA256 |
|---|---:|---|
| `reports/prebuy_trigger_report.md` | 646 | `b248884a463ce2c90ad13a8ac05ba29a790548b78f355313624572f20496db52` |
| `data/raw/signatures_raw.json` | 271758 | `903092252378ff3e5ff3705b667171d01dc769b402749fd2dc33655e8da8802c` |
| `data/raw/transactions_raw.json` | 14796459 | `d4f60bf6b0a6742b5900879637cdb57713b57b1147ddbe1208a3ffdd08423720` |
| `data/raw/gmgn_trend_snapshots/4c1d2804d1b493cd.html` | 53 | `4c1d2804d1b493cd0064881e5ca51f6955fdd1cba0b32c5358caf6bbe3498135` |
| `data/raw/gmgn_trend_snapshots/89e874b95d0accfd.json` | 2750 | `89e874b95d0accfd1211b946e2660a14cd45a4b416fb3da05f8aeb564c09d406` |

## Supabase / GitHub Audit

### Checked Surfaces

- Local repo: scripts, app pages, docs, workflows, ignored artifacts.
- Git remote: `origin` and `origin/main` commit.
- Supabase plugin tools: `_list_projects`, `_list_tables`, `_list_migrations`, `_list_edge_functions`, `_list_branches`, `_get_project`, `_get_project_url`, `_get_advisors`.
- Supabase public endpoints:
  - `https://mcp.supabase.com/mcp` -> `HTTP 401`, expected for unauthenticated access.
  - `https://catntmobfcenkhkodnqv.supabase.co/rest/v1/` -> `HTTP 401`, expected without API key.
- Supabase local bridge code:
  - `scripts/upload_to_supabase.py`
  - `scripts/upload_all_to_supabase.py`
  - `scripts/_verify_supabase.py`
  - `app/pages/01_Supabase_Bridge.py`

### Drift Table

| Area | Evidence | Drift / Risk | Level | Minimal fix | Verification step |
|---|---|---|---:|---|---|
| Supabase schema | No tracked `supabase/migrations`; bridge code assumes `dataset_runs` and `dataset_artifacts` | Live schema cannot be proven from Git | HIGH | Restore read-only MCP or env-backed SQL, capture schema into migration path | `list_tables`, `list_migrations`, policies query, REST sample read |
| Supabase MCP | MCP endpoint reachable as unauthenticated `401`; plugin tool client times out handshaking | Tool auth/client state blocked | HIGH | Re-authenticate Supabase plugin/MCP, or provide env-backed read-only service flow | Successful `_list_tables` and `_list_migrations` |
| Data API security | Supabase docs require RLS on exposed `public` schema tables and explicit grants | Cannot verify RLS/policies until live access works | HIGH | Query `pg_class.relrowsecurity`, `pg_policies`, grants for `dataset_*` | RLS/policy/grant report saved with timestamp |
| GitHub repo state | Local and remote commit match | No GitHub code drift detected for current checkout | LOW | None | `git rev-parse HEAD` equals `git ls-remote origin refs/heads/main` |
| Runtime data | Current ignored raw tx coverage is 45.9%; docs mention stronger previous limit-1000 run | Local data and docs are out of sync | HIGH | Rerun full fetch with stable RPC and retries; save artifact hashes | Coverage >= 99.5%, parser confidence report, manual ambiguity audit |
| Processed artifacts | `data/processed` has no current files; `reports/prebuy_trigger_report.md` is tracked but stale relative to current raw | UI/analysis cannot render current pipeline state from tracked outputs | HIGH | Regenerate processed artifacts from current or full raw run | `wallet_swaps.csv`, `trades_paired.csv`, `entry_context.csv`, `control_points.csv`, `trigger_tests.csv` exist and hash cleanly |
| Trigger claims | Current tracked report has `0 PASS`, mostly `UNKNOWN` | No trigger can be promoted | HIGH | Add market-wide controls and OOS validation | Entry/control, winner/loser, OOS, latency/fee/slippage tests |
| Secrets | Security scan passes; no env keys present | No current leak in tree, but live keys unavailable | MED | Keep keys in env/secrets only | `py -3.12 scripts/security_scan.py` |

### Supabase SoT Rule

Until live schema is readable, the only honest Supabase verdict is `BLOCKED/PARTIAL`. If live tables exist without Git migrations, that is `HIGH-RISK DRIFT`, because Supabase migration docs treat Git migration files and the remote migration history as separate systems that must stay in sync.

Relevant source anchors:

- Supabase migrations: <https://supabase.com/docs/guides/deployment/database-migrations>
- Supabase MCP: <https://supabase.com/docs/guides/ai-tools/mcp>
- Supabase RLS: <https://supabase.com/docs/guides/database/postgres/row-level-security>
- Supabase API security: <https://supabase.com/docs/guides/api/securing-your-api>

## Wallet Forensic Reconstruction

### Truth Order

1. Raw Solana transaction exports.
2. Normalized swap rows from reproducible parser.
3. FIFO paired trades under documented pairing rules.
4. Entry context and matched control points.
5. Trigger validation reports.
6. Manual audit of ambiguous rows.
7. Dashboards, GMGN, DexScreener, screenshots, and summaries as hints only.

### Current Local Evidence Chain

| Layer | Current state |
|---|---|
| Raw signatures | `1000` signatures for target wallet |
| Signature time span | `2026-05-20T07:12:26Z` to `2026-05-20T19:54:51Z` |
| Raw transactions | `459` fetched tx payloads from `1000` signatures |
| Fetch errors | `25` recorded errors |
| Coverage | `45.9%` |
| In-memory normalized rows | `459` |
| Sides | `BUY=211`, `SELL=222`, `FAILED=23`, `UNKNOWN=3` |
| Parser confidence | `high=456`, `low=3` |
| In-memory FIFO pairs | `174` |
| Pair winners / losers | `88` / `86` |
| Partial paired PnL | `+7.051529579 SOL` before complete-data audit |
| Hold time | min `49s`, median `963.5s`, max `8018s` |
| Pump-like paired mints | `156 / 174` paired trades end with `pump` |

### Live Public RPC Snapshot

Source: public Solana JSON-RPC `https://api.mainnet-beta.solana.com`.

| Check | Result |
|---|---|
| RPC API version | `3.1.14` |
| Balance slot | `421283954` |
| Balance | `106.287567435 SOL` |
| Latest fetched finalized tx | `2L1Kwnyav6fMt2empQY4bstLEqerSREqBespq9bVYP25znHkSnpbUT1hH3XX1DTDPQv4g1ebBUJ37HDU8pUigaxm` |
| Latest tx time | `2026-05-21T21:31:33Z` |
| Latest tx slot/index | `421283687 / 832` |

Solana source anchors:

- `getTransaction`: <https://solana.com/docs/rpc/http/gettransaction>
- `getBlock`: <https://solana.com/docs/rpc/http/getblock>

### FACT / INTERP / HYP

#### FACT

- The target wallet has finalized recent activity and a positive SOL balance.
- Local raw signatures and partial raw transactions exist.
- The current local raw transaction snapshot is incomplete.
- The parser preserves uncertainty with `UNKNOWN` and low-confidence rows.
- The tracked trigger report does not contain any trading-trigger `PASS`.

#### INTERP

- The partial sample is consistent with a high-turnover memecoin/pump trading style.
- The mix of roughly balanced winners/losers and positive partial PnL suggests tail-skew rather than simple high hit-rate behavior.
- Repeat mint activity and pump-like dominance imply token lifecycle and wave-level analysis matter more than a single isolated buy signal.

#### HYP

- The wallet may use a reject-first cascade rather than one magic trigger.
- Useful pre-buy triggers may sit in market microstructure, creator/funder history, token lifecycle state, or execution feasibility.
- Jito/priority fee behavior may affect realized edge.
- Copying the wallet after public observation may erase or invert the edge due to latency, slippage, fees, and crowding.

## Hint-Layer Snapshot: DexScreener Top Local Mints

Source: DexScreener token-pairs API. This is current metadata/liquidity context only, not proof of historical pre-entry conditions.

| Mint | Local rows | Pairs | First dex | Price USD | Liquidity USD | FDV / mcap | Boosts |
|---|---:|---:|---|---:|---:|---:|---|
| `FZekF8EV...RRpump` | 17 | 5 | `pumpswap` | `0.000006351` | `6649.61` | `6349` | null |
| `28Q3ToL...ViRL` | 15 | 2 | `pumpswap` | `0.00007267` | `23255.23` | `70461` | null |
| `4tR7PbU...Ytpump` | 13 | 2 | `pumpswap` | `0.0001805` | `35237.39` | `180502` | null |
| `TjsmLrT...tSpump` | 11 | 1 | `pumpswap` | `0.00002536` | `13303.18` | `25366` | null |
| `FBS7Ysj...KUpump` | 10 | 2 | `pumpswap` | `0.000003919` | `5123.59` | `3919` | null |

Source anchor: <https://docs.dexscreener.com/api/reference>

## Pre-Buy Trigger Research Catalog

The correct question is not "what trigger buys?" but "which observable pre-entry state survives controls, delay, fees, and out-of-sample?"

| Family | Candidate features | Source | Status | Falsifiable test |
|---|---|---|---|---|
| `wallet_flow` | target buy/sell count, net SOL, repeat entries | local `wallet_swaps` | IMPLEMENTED/PARTIAL | Entry vs matched same-token controls |
| `market_microstructure` | market tx count, unique buyers, buy/sell imbalance, market volume | Dune `dex_solana.trades` export | IMPLEMENTED path, missing export | Dune same-token pre-entry window vs controls |
| `VPIN/OFI toxicity` | VPIN buckets, signed order-flow imbalance, toxicity persistence | Dune or low-latency trade feed | HYP | VPIN at entry > controls and survives OOS |
| `bonding_curve_graduation` | curve progress, velocity, acceleration, migration proximity | Pump lifecycle export / RPC / indexer | HYP | Age/liquidity-matched controls around graduation |
| `creator_funder_fingerprint` | creator prior launches, deployer win rate, funder cluster, wallet age | RPC/indexer | HYP | Creator/funder features predict winners, not just entries |
| `attention_arbitrage` | DexScreener boosts/orders/profile changes, social link freshness | DexScreener API and external metadata | HYP | Boost/order events observed before entry and not after |
| `token_2022_safety` | TransferHook, PermanentDelegate, freeze/mint authorities, extension risk | mint account RPC | HYP | Risk score separates avoided losers from winners |
| `slot_execution` | entry tx index, same-slot order, priority fee, compute budget, Jito tip candidates | `getBlock`, transaction meta, fee audit | HYP | Winners have earlier slot/order or better landing economics after controls |
| `ATA_to_buy_timing` | seconds/slots from ATA creation to buy | raw tx instruction traces | HYP | Very short ATA-to-buy delta separates entries from controls |
| `cluster_toxicity` | distinct wallets, funding similarity, same-token temporal clustering | market trades + funding graph | PARTIAL/HYP | Cluster presence is classified bullish vs toxic vs sybil |
| `entropy_reflexivity` | volatility compression, price-volume-attention feedback | market + metadata time series | HYP | Inflection score predicts continuation after costs |

Source anchors:

- Dune Solana DEX trades: <https://docs.dune.com/data-catalog/curated/dex-trades/solana/solana-dex-trades>
- Helius webhooks: <https://www.helius.dev/docs/webhooks>
- Jito low-latency send: <https://docs.jito.wtf/lowlatencytxnsend/>
- Pump.fun graduation paper: <https://arxiv.org/abs/2602.14860>
- SolRugDetector paper: <https://arxiv.org/abs/2603.24625>
- VPIN / Bitcoin jumps reference: <https://ideas.repec.org/a/eee/riibaf/v81y2026ics0275531925004192.html>

## "What If?" Models

### Model A: Reject-First Cascade

Hypothesis: the edge is mostly avoiding traps, not finding one positive trigger.

Pipeline:

```text
new / active token universe
-> hard reject: low liquidity, bad token authority, suspicious creator, toxic cluster
-> soft reject: no market flow, weak age bucket, bad holder growth
-> trigger score
-> execution feasibility
-> position sizing
```

Falsifier: rejected candidates later outperform entries after matched age/liquidity controls.

### Model B: Graduation Crescendo

Hypothesis: entries happen near pump lifecycle acceleration, where bonding-curve progress and market attention reinforce each other.

Features:

- curve progress percentile
- curve velocity over 30s/60s/300s
- unique buyer acceleration
- market buy imbalance
- pool migration / PumpSwap state marker

Falsifier: same-age, same-liquidity controls show equal or better continuation.

### Model C: Toxicity Filter

Hypothesis: the wallet buys when order-flow imbalance is strong but not yet toxic enough to imply immediate dump/crowding.

Features:

- VPIN bucket
- OFI slope
- buy/sell concentration
- top-wallet dominance
- cluster toxicity score

Falsifier: VPIN/OFI separates entries from controls but fails winner-vs-loser or collapses under delay.

### Model D: Execution Edge

Hypothesis: the observed PnL is less about token selection and more about landing speed, priority fee policy, and exit discipline.

Features:

- tx index within slot
- compute unit price / limit
- Jito tip candidate
- block leader / Jito slot context
- time from signal to landed buy
- delayed replay PnL at +1 slot, +3 slots, +10s, +30s

Falsifier: delayed replay retains most of the edge and execution metrics do not separate winners.

### Model E: Attention Lag Arbitrage

Hypothesis: the wallet enters before public attention surfaces catch up.

Features:

- DexScreener profile/order/boost timeline
- social links added before entry
- search/trending appearance delay
- liquidity/volume acceleration before boost

Falsifier: attention markers are after-entry or equally present in controls.

## Solana-Flow Audit and Safe Design

This section is a design boundary for any future transaction UI. The current forensic pipeline must stay read-only.

### Current Weak Points to Avoid

- Mixing research scripts with transaction-sending code.
- Letting dashboards become buy/sell recommendations.
- Using mainnet by default.
- Signing before simulation and human review.
- Trusting RPC account data without owner, data-length, and discriminator checks.
- Hiding writable accounts, fee payer, compute budget, Jito tip, or slippage from the user.
- Letting legacy `web3.js` types leak across the whole app when a narrow adapter would be safer.

### Safe Architecture

```text
read-only forensic pipeline
  -> produces evidence artifacts

decision/research UI
  -> displays FACT / INTERP / HYP and rejects BUY language

transaction review module (separate)
  -> builds unsigned tx on devnet/local by default
  -> simulates
  -> renders review
  -> asks explicit confirmation
  -> wallet-standard signing
  -> sends
  -> tracks confirmation / expiry
```

Recommended stack:

- UI wallet connection: Wallet Standard via `@solana/client` and `@solana/react-hooks`.
- Client/RPC: `@solana/kit`.
- Legacy boundary only when required: `@solana/web3-compat`.
- Dev/test: localnet/devnet first; mainnet only by explicit confirmation.

### Required Transaction Review Fields

Before any signature request:

- cluster and RPC endpoint class
- fee payer
- recipient/token/mint
- amount and max slippage
- program IDs
- signer accounts
- writable accounts
- recent blockhash and expiry
- compute unit limit
- compute unit price
- priority fee estimate
- Jito tip if present
- simulation result and logs

Source anchors:

- Solana compute budget: <https://solana.com/docs/core/fees/compute-budget>
- Solana fee structure: <https://solana.com/docs/core/fees/fee-structure>
- Solana transaction confirmation: <https://solana.com/uk/developers/guides/advanced/confirmation>

## Test and Verification Plan

### Already Verified in This Pass

| Gate | Result |
|---|---|
| `py -3.12 -m pytest -q` | PASS, `50 passed` |
| `py -3.12 scripts/security_scan.py` | PASS, no high-risk secret candidates |
| Public Solana balance/signature read | PASS |
| Supabase REST unauthenticated boundary | PASS as expected `401` |
| Supabase plugin live schema read | BLOCKED by MCP handshake timeout |

### Next Commands

Use `py -3.12` until PATH is fixed.

```powershell
py -3.12 scripts\01_fetch_signatures.py --limit 1000
py -3.12 scripts\02_fetch_transactions.py --max-errors 0
py -3.12 scripts\03_normalize_swaps.py
py -3.12 scripts\04_pair_trades.py
py -3.12 scripts\06_build_price_series.py
py -3.12 scripts\18_build_entry_context.py --sample-winners 30 --sample-losers 30
py -3.12 scripts\19_build_control_points.py
py -3.12 scripts\20_test_entry_triggers.py
```

Minimum dataset acceptance:

- transaction coverage >= `99.5%`
- no unreviewed `UNKNOWN` swap rows
- low-confidence rows manually audited
- all generated artifacts have sha256
- trigger report has explicit `PASS / PARTIAL / NO_SIGNAL / UNKNOWN / FAIL`
- no final trigger claim without OOS, latency, fee, and slippage replay

## Next Falsifiable Step

The next strongest step is not another narrative analysis. It is a full coverage rebuild plus market-wide controls:

1. Restore stable RPC (`SOLANA_RPC_URL`) and Supabase read access.
2. Rebuild raw -> normalized -> paired -> entry/control artifacts.
3. Export same-token market trades from Dune for the exact entry/control windows.
4. Run market enrichment and trigger tests.
5. Falsify the strongest candidate model:
   - if entries do not separate from matched controls, reject the trigger family;
   - if entries separate but winners do not, mark selection-only or crowding artifact;
   - if signal disappears under delay/fees/slippage, reject copyability.

## Close - Delta

Delta: the project now has a single evidence-backed dossier that separates repo facts, live blockers, local partial data, external hints, and hypothesis models.  
D: sources are repo files, public Solana RPC, Supabase/Dune/DexScreener/Helius/Jito/Solana docs, and academic source anchors listed above.  
Omega: `0.78` for repo/local forensic state; `0.35` for Supabase live drift because MCP access is blocked; `0.25` for trigger hypotheses until controls/OOS exist.  
Lambda: revise this dossier immediately after Supabase MCP/env access works or after a >=99.5% transaction coverage rebuild.
