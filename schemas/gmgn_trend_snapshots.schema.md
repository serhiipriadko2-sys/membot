# gmgn_trend_snapshots.csv schema

Purpose: store parsed GMGN Trend snapshots as a candidate universe / control-group source for wallet reverse engineering.

Non-goals:
- No buy signals.
- No trading recommendations.
- No invented labels for ambiguous GMGN lower-card metrics.

## Raw storage rule

Every parsed input snapshot must also be stored under:

```text
data/raw/gmgn_trend_snapshots/<snapshot_id>.<ext>
```

`gmgn_trend_snapshots.csv` rows must include `raw_source_path` so every parsed row can be traced back to the raw snapshot.

## Columns

| Column | Type | Meaning |
|---|---|---|
| `snapshot_id` | string | Stable short SHA256 id of raw input bytes. |
| `snapshot_ts` | ISO string | Time the snapshot was collected or assigned during parsing. |
| `source_page` | string | Source page from snapshot metadata, e.g. `https://gmgn.ai/trend`. |
| `source_title` | string | Page title if available. |
| `chain` | string | Chain, e.g. `sol`. |
| `section` | string | UI section, e.g. trend section. |
| `filter_windows` | string | Pipe-separated UI filters present in the snapshot. |
| `rank` | integer | Token order in the snapshot. |
| `token_name` | string | Token display name. |
| `display_name_raw` | string | Raw/truncated display name when distinct. |
| `token_mint` | string | Best-effort token mint/address, usually extracted from token links. |
| `address_short` | string | Short address shown by GMGN snapshot. |
| `age_raw` | string | Original age text. |
| `age_seconds` | integer/string | Parsed age in seconds when unambiguous. |
| `score_in_card` | string/integer | Number shown in token card. Semantic meaning is not inferred. |
| `market_cap_raw` | string | Raw market cap text. |
| `growth_raw` | string | Raw growth text. |
| `ath_mc_raw` | string | Raw ATH market cap text. |
| `liquidity_raw` | string | Raw liquidity text. |
| `volume_1h_raw` | string | Raw 1h volume text. |
| `transactions_1h_raw` | string | Raw/normalized 1h transaction count. |
| `buys_sells_raw` | string | Raw buy/sell pair text. |
| `buys_1h` | string | Parsed buys count if `buys_sells_raw` is split safely. |
| `sells_1h` | string | Parsed sells count if `buys_sells_raw` is split safely. |
| `holders_raw` | string | Raw holder count. |
| `total_fees_raw` | string | Raw total fees text. |
| `has_x` | bool string | Whether X/Twitter links were present. |
| `has_website` | bool string | Whether a website link was present. |
| `has_telegram` | bool string | Whether Telegram links were present. |
| `has_pump_fun` | bool string | Whether pump.fun links were present. |
| `has_meteora` | bool string | Whether Meteora links were present. |
| `token_info_raw` | string | Raw token info block value such as `DS`; semantics unknown. |
| `raw_metric_a` ... `raw_metric_g` | string | Ambiguous lower-card metric values preserved without invented names. |
| `parse_confidence` | enum | `high`, `medium`, or `low`. |
| `parse_notes` | string | Pipe-separated parser notes and uncertainties. |
| `raw_source_path` | string | Stored raw snapshot path. |

## Guardrails

- Do not create `buy_signal`, `sell_signal`, `recommendation`, `score`, or similar trading-decision columns.
- If a metric label is unclear, preserve it under `raw_metric_*`.
- GMGN Trend is a candidate-universe/control-group source, not proof of edge.
- H4 remains `UNKNOWN` until trend snapshots are joined with wallet entries and matched control points.
