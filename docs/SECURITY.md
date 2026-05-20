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

## If a secret is found

1. Treat it as compromised.
2. Rotate or revoke the key in the provider dashboard.
3. Remove the key from tracked files.
4. Move the value into GitHub Actions secrets, Streamlit secrets, or local `.env` ignored by git.
5. Consider Git history cleanup only after rotation, because history rewriting can disrupt clones and pull requests.

## Allowed placeholders

Examples must use placeholders only:

```text
SUPABASE_SERVICE_ROLE_KEY=<your-service-role-key>
OPENAI_API_KEY=<your-openai-key>
SOLANA_RPC_URL=<your-rpc-url>
```

Never use real-looking JWTs, `sb_secret_...`, `sk-...`, or private RPC URLs as examples.
