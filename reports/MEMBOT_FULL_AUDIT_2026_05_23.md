# MEMBOT — полный аудит, тестирование и проектирование контроля

Дата: 2026-05-23
Scope: GitHub `serhiipriadko2-sys/membot`, Supabase `catntmobfcenkhkodnqv`, Streamlit/Data Bridge, Fast10 Observer, security/QA gates.

## 0. Вердикт

**Статус:** PARTIAL PASS / PROD BLOCKED.

Проект уже имеет сильные защитные границы: он объявлен forensic / execution-lab workspace, а не торговым ботом. Основные блокеры перехода дальше:

1. Live alpha не подтверждена live network CSV.
2. Paper mode заблокирован до Gate 2 PASS.
3. Supabase работает, но RLS включен без policies на 6 public tables.
4. Есть schema split: старые `dataset_*` таблицы питают Streamlit Bridge, новые `research_*` таблицы являются registry, но почти пустые.
5. Локальные тесты и secret scan должны быть запущены в clone/CI, потому что через GitHub connector был возможен только static/read audit.

## 1. Evidence map

### GitHub / repo

- `README.md`: фиксирует `LIVE_ALPHA: NOT VERIFIED` и запрет торгового бота до Observer/Paper PASS.
- `README_RUNBOOK.md`: фиксирует Gate 0-4 и safety boundary: monitoring only, no private keys, no signing, no swap/send endpoints.
- `docs/SECURITY.md`: запрещает коммитить API keys, Supabase service role keys, wallet private keys, seed phrases, private RPC endpoints.
- `.github/workflows/security-scan.yml`: запускает current-tree secret scan на PR/push/main.
- `.github/workflows/security-history-scan.yml`: запускает full-history scan вручную с `fetch-depth: 0`.
- `scripts/security_scan.py`: ищет `sb_secret_`, `sk-`, JWT-like keys, private key blocks, service-role assignments.
- `scripts/observer_gate_eval.py`: строгий gate evaluator для latency CSV.
- `app/agent_runtime_qa.py`: runtime QA для agent modes и запрет торговых директив.

### Supabase live

- Project `catntmobfcenkhkodnqv`: ACTIVE_HEALTHY, region `eu-west-3`, Postgres 17.
- Public tables:
  - `dataset_runs`
  - `dataset_artifacts`
  - `research_runs`
  - `research_artifacts`
  - `research_findings`
  - `execution_lab_metrics`
- RLS: enabled на всех 6 таблицах.
- Policies: отсутствуют.
- Counts:
  - `dataset_runs`: 2
  - `dataset_artifacts`: 11
  - `research_runs`: 1
  - `research_artifacts`: 0
  - `research_findings`: 0
  - `execution_lab_metrics`: 0
- Edge Functions: отсутствуют.
- Advisors:
  - security: RLS enabled no policy на 6 таблицах.
  - performance: unused indexes на `idx_dataset_runs_wallet`, `idx_dataset_artifacts_type`; Auth DB connection strategy notice.

## 2. Scope model: что значит “100% покрытие”

Абсолютное 100% покрытие невозможно честно обещать. Реальный контракт:

**100% coverage of declared audit scope** = каждый пункт ниже имеет PASS/FAIL/UNKNOWN и команду проверки.

| Layer | Coverage target | PASS condition |
|---|---|---|
| Repo identity | 100% | repo доступен, branch известен, статус documented |
| Secret exposure current tree | 100% declared patterns | `python scripts/security_scan.py` PASS |
| Secret exposure history | 100% git history | `security-history-scan` workflow PASS |
| Python deps install | 100% declared deps | `pip install -r requirements.txt` PASS |
| Agent runtime QA | 100% QA_CASES | `python scripts/agent_ci_smoke.py` PASS |
| Observer smoke | 100% smoke gate | `observer_gate_eval --run-mode smoke` returns SMOKE_ONLY |
| Observer live gate | 100% Gate 2 rows | live CSV evaluated PASS |
| Supabase schema | 100% public tables | schema inventory matches expected |
| Supabase RLS | 100% public tables | RLS true for all public tables |
| Supabase policies | 100% chosen access model | policies either intentionally absent or explicitly present |
| Streamlit navigation | 100% app entry | only intended pages exposed |
| Trading safety | 100% safety boundary | no private key, signing, swap/send endpoint in runtime path |

## 3. Blocking findings

### P0 — Do not enable Paper/Live yet

Reason: README and runbook both say Observer live run is pending and Paper mode remains blocked until Gate 2 PASS.

Required proof:

```bash
python scripts/fast10_observer.py \
  --input data/processed/fast10_live_candidates.csv \
  --output data/processed/observer_latency_live.csv \
  --limit 100

python scripts/observer_gate_eval.py \
  --input data/processed/observer_latency_live.csv \
  --run-mode live \
  --min-live-rows 50
```

PASS minimum:

```text
coverage >= 90%
p50 total_latency_ms < 500
p90 total_latency_ms < 1000
p50/p90 quote_latency_ms populated
p50/p90 detector_latency_ms populated
```

### P1 — Supabase access model undecided

Current state is service-only by effect: RLS enabled, no policies. This is safe for private lab, but blocks anon/auth reads.

Decision required:

- Option A: service-only private lab — keep no policies, Streamlit uses service role server-side behind PIN.
- Option B: authenticated read-only — add SELECT policies for authenticated users.
- Option C: public read-only metadata — expose only safe views, not raw artifact content.

Recommended now: **Option A** until Gate 2 PASS.

### P1 — Schema split

`dataset_*` contains existing app data; `research_*` registry exists but mostly empty. Decide canonical flow:

- keep `dataset_*` as UI cache / artifact storage;
- use `research_*` as audit registry / receipts;
- or migrate all UI to `research_*` views.

Recommended: create DB views that unify both worlds instead of rewriting UI immediately.

### P2 — Documentation stale

`docs/SUPABASE_SYNC_STATUS.md` says live DDL was blocked, but live DB now contains research registry tables. Update doc after verification.

## 4. Test matrix

### Local / CI commands

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
python scripts/security_scan.py
python scripts/agent_ci_smoke.py
python scripts/fast10_detector_emitter.py --output data/processed/observer_latency_live.csv --rows 1
python scripts/observer_gate_eval.py --input data/processed/observer_latency_live.csv --run-mode smoke
```

### Full history security scan

Run GitHub Actions manually:

```text
Actions -> Security history scan -> Run workflow -> max_commits empty
```

PASS: no high-risk historical secrets, or all found secrets rotated/revoked and incident closed.

### Supabase SQL inventory

```sql
select table_schema, table_name
from information_schema.tables
where table_schema = 'public'
order by table_name;
```

```sql
select tablename, rowsecurity
from pg_tables
where schemaname = 'public'
order by tablename;
```

```sql
select schemaname, tablename, policyname, permissive, roles, cmd
from pg_policies
where schemaname = 'public'
order by tablename, policyname;
```

```sql
select 'dataset_runs' as table_name, count(*) from public.dataset_runs
union all select 'dataset_artifacts', count(*) from public.dataset_artifacts
union all select 'research_runs', count(*) from public.research_runs
union all select 'research_artifacts', count(*) from public.research_artifacts
union all select 'research_findings', count(*) from public.research_findings
union all select 'execution_lab_metrics', count(*) from public.execution_lab_metrics
order by table_name;
```

## 5. “Что если?” matrix

### What if 1: RLS policies are added too early

Risk: accidental public exposure of `content_text` artifacts.

Mitigation:
- never expose raw `dataset_artifacts.content_text` to anon;
- create safe public views with only metadata columns;
- keep writes service-role only.

### What if 2: Gate 2 fails because quote latency dominates

Mitigation:
- keep-alive HTTP client;
- async connection pool;
- runner closer to Jupiter/RPC region;
- paid low-latency RPC;
- prefilter before quote;
- local rough quote pre-gate.

### What if 3: Gate 2 fails because detector latency dominates

Mitigation:
- streaming JSONL append;
- no pandas in hot path;
- rolling in-memory windows;
- async CSV writes;
- optional Rust hot path.

### What if 4: historical secret is found

Mitigation:
- treat as compromised;
- rotate/revoke provider key;
- remove tracked value;
- update Streamlit/GitHub/local secrets;
- run current scan and history scan;
- only then close P0.

### What if 5: UI says “active” but gate failed

Mitigation:
- UI must render `ACTIVE / GATE FAILED` as blocked state;
- never convert dashboard status into trading readiness;
- Paper mode requires evaluator PASS, not UI optimism.

## 6. Internet no-how / external best-practice synthesis

- Supabase official RLS docs: exposed schemas such as `public` should have RLS enabled, and after RLS is enabled, data is inaccessible via publishable key until policies exist.
- Streamlit official docs support `st.secrets` for app secrets; repo must keep only placeholders, not real keys.
- Operational no-how: prefer service-only until data model is stable; expose public read only via sanitized views, not raw artifact tables.
- Latency no-how: for sub-second quote loops, measure detector latency and quote latency separately; optimize the dominant term only after measurement.

## 7. Proposed architecture

### Current safe architecture

```text
Streamlit server
  -> st.secrets / env
  -> Supabase service role
  -> dataset_* tables
  -> UI widgets
```

Constraints:
- app protected by PIN;
- service role never exposed client-side;
- no public RLS policies;
- no signing or swap/send endpoints.

### Next architecture

```text
Fast10 detector/replay
  -> observer_latency_live.csv
  -> observer_gate_eval.py
  -> reports/observer_gate_report.{md,json}
  -> research_runs / research_artifacts / research_findings / execution_lab_metrics
  -> safe Streamlit dashboard
```

### Suggested safe views

If public/auth read is needed later, expose views only:

```sql
create or replace view public.safe_research_runs as
select run_key, target_wallet, phase, verdict, summary, created_at
from public.research_runs;

create or replace view public.safe_research_artifacts as
select run_key, artifact_path, artifact_kind, rows_count, bytes_count, sha256, created_at
from public.research_artifacts;
```

Do not expose raw `content_text` or service role writes.

## 8. Release gates

### Gate A — Private lab ready

- security scan PASS;
- agent CI smoke PASS;
- Supabase service-only model explicitly documented;
- Streamlit PIN configured;
- no public policies on raw artifact tables.

### Gate B — Observer ready

- Gate 0 package audit PASS;
- Gate 1 smoke returns SMOKE_ONLY;
- Gate 2 live returns PASS;
- report and JSON committed or uploaded with sha256 receipt.

### Gate C — Paper mode discussion allowed

- Gate B PASS;
- slippage replay complete;
- fail-safe behavior specified;
- private-key boundary design reviewed;
- explicit approval recorded.

### Gate D — Live execution discussion allowed

- Paper mode results stable;
- independent security review;
- key custody design;
- kill-switch and max-loss controls;
- manual approval.

## 9. Immediate task list

1. Run local/CI commands in section 4.
2. Update `docs/SUPABASE_SYNC_STATUS.md` to reflect live DB state.
3. Add a `reports/MEMBOT_FULL_AUDIT_2026_05_23.md` file to repo.
4. Decide Supabase access model: service-only recommended.
5. Add a small `docs/SUPABASE_ACCESS_MODEL.md` explaining why RLS has no policies yet.
6. Run Security history scan from GitHub Actions.
7. Produce a live network `observer_latency_live.csv` only with observer credentials, no wallet key.

## 10. DONE criteria

DONE is valid only when there is:

- report path;
- sha256;
- bytes;
- commands and exit codes;
- PASS/FAIL per gate;
- explicit remaining risks.
