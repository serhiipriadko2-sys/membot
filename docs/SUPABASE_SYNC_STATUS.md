# Supabase Sync Status — MEMBOT

## Verdict

GitHub documentation has been updated to the current execution-lab state. Supabase live synchronization is **not completed in this environment** because the currently available connector set exposes GitHub write tools but not Supabase DDL/apply-migration tools.

The correct Supabase action is to apply the migration in `supabase/migrations/20260523000000_execution_lab_research_registry.sql` and then insert/update artifact registry rows from the current hashes.

## Known project

```text
project ref: catntmobfcenkhkodnqv
name: membot
url: https://catntmobfcenkhkodnqv.supabase.co
```

## Required live checks

After Supabase tools or CLI access is restored:

```sql
select table_schema, table_name
from information_schema.tables
where table_schema = 'public'
order by table_name;
```

Then verify:

```sql
select tablename, rowsecurity
from pg_tables
where schemaname = 'public';
```

And policies:

```sql
select schemaname, tablename, policyname, permissive, roles, cmd
from pg_policies
where schemaname = 'public'
order by tablename, policyname;
```

## Tables proposed by migration

- `research_runs`
- `research_artifacts`
- `research_findings`
- `execution_lab_metrics`

These are metadata tables only. They do not contain private keys, wallet secrets, or trading credentials.

## Security rule

RLS must be enabled before any client-exposed access. Service-role writes must remain server-only.

## Current blocker

Supabase live DDL was not applied by this assistant turn. Treat DB state as:

```text
GITHUB_SCHEMA_PROPOSED: YES
LIVE_SUPABASE_APPLIED: NO / BLOCKED
```
