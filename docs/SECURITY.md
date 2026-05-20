# Security policy: secrets and Supabase keys

## Scope

This project is a forensic/research scaffold. It must not commit API keys, Supabase service role keys, wallet private keys, seed phrases, RPC private endpoints, or other credentials.

## Supabase key boundary

- Supabase project URL is not a secret by itself.
- Publishable/anon keys can be used in public clients only when Row Level Security policies are correct.
- Secret keys and service role keys must never be committed.
- Service role keys bypass Row Level Security and must stay server-side only.

## Required environment variables

Use environment variables or platform secrets:

```text
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
SOLANA_RPC_URL=
OPENAI_API_KEY=
```

Only set the variables required by the specific script or deployment target.

## Local scanning

Run before committing:

```bash
python scripts/security_scan.py
```

The scan redacts candidate values and reports file + line only. Do not paste real secrets into issues, PR comments, screenshots, or chat logs.

## CI scanning

The `Security scan` GitHub Actions workflow runs `scripts/security_scan.py` on pull requests and pushes to `main`.

## Manual history scanning

After a known leak is removed from the current tree and the provider key is rotated, run the manual `Security history scan` workflow.

The workflow checks out full git history with `fetch-depth: 0` and runs:

```bash
python scripts/security_history_scan.py
```

Use the optional `max_commits` workflow input only for debugging. A full incident review should leave it empty.

History scan output is redacted. Do not paste raw secrets into issues, PR comments, screenshots, or chat logs.

## If a secret is found

1. Treat it as compromised.
2. Rotate or revoke the key in the provider dashboard.
3. Remove the key from tracked files.
4. Move the value into GitHub Actions secrets, Streamlit secrets, or local `.env` ignored by git.
5. Run current-tree security scan.
6. Run history scan.
7. Consider Git history cleanup only after rotation, because history rewriting can disrupt clones and pull requests.

## Supabase rotation checklist

1. Open Supabase dashboard for the affected project.
2. Rotate/revoke the exposed service role / secret key.
3. Update deployment secrets:
   - Streamlit secrets;
   - GitHub Actions secrets;
   - local `.env` only if needed.
4. Re-run:
   - `Security scan`;
   - `Agent CI smoke`;
   - `Security history scan`.
5. Close the P0 issue only after the old key is revoked and workflows are green.

## Allowed placeholders

Examples must use placeholders only:

```text
SUPABASE_SERVICE_ROLE_KEY=<your-service-role-key>
OPENAI_API_KEY=<your-openai-key>
SOLANA_RPC_URL=<your-rpc-url>
```

Never use real-looking JWTs, `sb_secret_...`, `sk-...`, or private RPC URLs as examples.
