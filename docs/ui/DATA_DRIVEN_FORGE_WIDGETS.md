# Data-driven Iskra Forge widgets

## Purpose
Replace decorative UI placeholders with charts derived from uploaded/local forensic artifacts.

## Live widgets

### Cluster map
Source priority:
1. `wallet_swaps.csv`
2. `trades_paired.csv`

Expected columns, any one accepted:
- token: `token_mint`, `mint`, `base_mint`, `token_address`, `token`, `symbol`
- side: `side`, `swap_side`, `action`, `type`
- amount: `sol_amount`, `amount_sol`, `amount_in`, `amount_out`, `usd_value`, `value`, `net_pnl_sol`, `pnl_sol`

Behavior:
- groups rows by token
- sizes nodes by transaction count
- colors nodes by buy-sell balance
- renders UNKNOWN if token column is absent

### Daily PnL calendar
Source: `daily_pnl_calendar.csv`

Expected columns:
- date: `date_utc`, `date`, `day`, `bucket_date`
- pnl: `net_pnl_sol`, `pnl_sol`, `gross_pnl_sol`, `net_pnl_usd`, `pnl_usd`

Behavior:
- creates week x weekday heatmap
- zmid=0 so positive/negative days split visually
- renders UNKNOWN if date/pnl columns are absent

### Fee/Jito orbit
Source: `priority_fee_jito_audit.csv`

Expected columns:
- verdict: `verdict`, `fee_verdict`, `evidence_verdict`
- Jito: `has_jito_tip`, `jito_tip`, `jito_detected`
- ComputeBudget: `has_compute_budget_ix`, `compute_budget`, `has_priority_fee`

Behavior:
- donut chart of verdicts plus detected Jito/ComputeBudget rows

### Signal cards + radar
Source priority:
1. `trigger_tests.csv`
2. `entry_exit_hypothesis_tests.csv`

Expected columns:
- name: `trigger`, `hypothesis`, `feature`, `name`, `family`, `scope`
- status: `status`, `verdict`, `result`
- score: `score`, `confidence`, `support`, `lift`, `precision`, `win_rate`, `value`
- note: `evidence`, `notes`, `summary`, `description`, `reason`

Behavior:
- radar chart by averaged signal support
- cards sorted by score/status
- PASS means support only; not a BUY signal

## Guardrail
Missing or incompatible artifacts must render UNKNOWN/empty states, never decorative fake evidence.
