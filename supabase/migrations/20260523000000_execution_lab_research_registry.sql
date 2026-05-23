-- MEMBOT execution-lab research registry
-- Date: 2026-05-23
-- Purpose: store research metadata, artifact receipts, and lab metrics.
-- Safety: metadata only. No secrets, private keys, or trading credentials.

create table if not exists public.research_runs (
  id uuid primary key default gen_random_uuid(),
  run_key text not null unique,
  target_wallet text not null,
  phase text not null,
  verdict text not null,
  summary text,
  created_at timestamptz not null default now()
);

create table if not exists public.research_artifacts (
  id uuid primary key default gen_random_uuid(),
  run_key text not null references public.research_runs(run_key) on delete cascade,
  artifact_path text not null,
  artifact_kind text not null,
  rows_count bigint,
  bytes_count bigint,
  sha256 text not null,
  notes text,
  created_at timestamptz not null default now(),
  unique(run_key, artifact_path)
);

create table if not exists public.research_findings (
  id uuid primary key default gen_random_uuid(),
  run_key text not null references public.research_runs(run_key) on delete cascade,
  finding_key text not null,
  truth_label text not null check (truth_label in ('FACT','INTERP','HYP','RISK')),
  verdict text not null,
  confidence numeric check (confidence >= 0 and confidence <= 1),
  evidence text,
  created_at timestamptz not null default now(),
  unique(run_key, finding_key)
);

create table if not exists public.execution_lab_metrics (
  id uuid primary key default gen_random_uuid(),
  run_key text not null references public.research_runs(run_key) on delete cascade,
  metric_group text not null,
  metric_key text not null,
  metric_value numeric,
  unit text,
  notes text,
  created_at timestamptz not null default now(),
  unique(run_key, metric_group, metric_key)
);

alter table public.research_runs enable row level security;
alter table public.research_artifacts enable row level security;
alter table public.research_findings enable row level security;
alter table public.execution_lab_metrics enable row level security;

-- Read access is intentionally not granted here. Add policies only after deciding
-- whether this metadata is public, authenticated-only, or service-only.
