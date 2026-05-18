# Mobile-friendly deployment guide

## Recommended path

```text
Phase 1: Streamlit Community Cloud
Phase 2: Supabase/Postgres or managed object storage for datasets
Phase 3: Render/Railway/Fly/VPS only when background jobs and persistence are required
```

## Why Streamlit Community Cloud first

The current app is a read-only dashboard over CSV/Markdown artifacts. Streamlit Community Cloud is the lowest-friction path because it can deploy directly from GitHub and run `app/streamlit_app.py` without requiring a server that you maintain from a phone.

## Security rules

```text
DO NOT commit .env
DO NOT commit .streamlit/secrets.toml
DO NOT commit API keys
DO NOT commit private keys
DO NOT enable trading endpoints
```

Only use placeholders in the repo. Add real secrets through the hosting provider UI.

## Streamlit Cloud deployment steps

1. Push the repo to GitHub.
2. Open Streamlit Community Cloud.
3. Create a new app from GitHub.
4. Repository: `serhiipriadko2-sys/membot`.
5. Branch: `main`.
6. Main file path:

```text
app/streamlit_app.py
```

7. Deploy.
8. Open the generated URL from mobile.

## Secrets

If future versions need RPC/API access inside the app, add secrets in Streamlit Cloud settings, not in GitHub.

Example secret names:

```toml
SOLANA_RPC_URL = "https://mainnet.helius-rpc.com/?api-key=..."
HELIUS_API_KEY = "..."
```

Do not use these secrets for trading. Read-only data access only.

## Dataset problem

The current `.gitignore` excludes `data/` and `output/`, so the deployed app will not automatically have local generated CSV files.

There are three safe options:

### Option A — demo dataset branch

Commit a small scrubbed demo dataset under:

```text
sample_data/processed/*.csv
```

Then later update the app to read sample data when `data/processed` is empty.

### Option B — upload CSV through the app

Add a Streamlit file uploader and parse CSV in memory. This is best for mobile if you can export files and upload them.

### Option C — database/object storage

Store generated outputs in Supabase/Postgres or object storage, then let the app read from there. This is best for real ongoing mobile use.

## Platform comparison

| Platform | Best for | Tradeoff |
|---|---|---|
| Streamlit Community Cloud | fastest read-only dashboard | weak persistence for generated datasets |
| Hugging Face Spaces | shareable demo with Streamlit | also needs dataset/storage plan |
| Render/Railway/Fly | service with persistent disk/jobs | more ops work |
| VPS | maximum control | inconvenient from mobile |

## Current command

```bash
streamlit run app/streamlit_app.py
```

## Next recommended implementation

```text
1. Add sample_data/processed with scrubbed demo CSV fixtures.
2. Add data source selector in Streamlit sidebar:
   - local data/processed
   - sample_data/processed
   - uploaded CSV
3. Add upload controls for wallet_swaps.csv and trades_paired.csv.
4. Add read-only secrets support later.
```
