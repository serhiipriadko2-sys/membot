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

Required for Supabase-backed artifact storage:

```toml
APP_ACCESS_PIN = "change-this-pin"
SUPABASE_URL = "https://catntmobfcenkhkodnqv.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "paste-only-in-streamlit-cloud-secrets"
```

Optional read-only RPC/API examples for later versions:

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

Use the `Upload / Supabase` tab. It can parse CSV/MD/JSON/TXT in memory and show previews. This is best for mobile if you can export files and upload them.

### Option C — Supabase artifact storage

The project has these Postgres tables:

```text
public.dataset_runs
public.dataset_artifacts
```

The app can save uploaded CSV/MD artifacts into Supabase and later reload them through the `Supabase` data source in the sidebar.

## Supabase workflow from mobile

1. Open the deployed Streamlit URL.
2. Enter `APP_ACCESS_PIN` in the sidebar.
3. Open `Upload / Supabase`.
4. Upload one or more files:

```text
wallet_swaps.csv
trades_paired.csv
latency_sim.csv
fee_adjusted_pnl.csv
copy_stress_model.csv
entry_context.csv
trigger_tests.csv
metrics_report.md
```

5. Check the preview.
6. Fill wallet, run label, source, notes.
7. Click `Save uploaded artifacts to Supabase`.
8. Switch sidebar source to `Supabase` and select the saved run.

## Supabase security notes

- RLS is enabled on `dataset_runs` and `dataset_artifacts`.
- The dashboard uses Supabase only server-side inside Streamlit.
- Keep `SUPABASE_SERVICE_ROLE_KEY` only in Streamlit secrets.
- `APP_ACCESS_PIN` is an extra app-level gate for public Streamlit URLs.
- Do not open broad anon read policies until the dataset is intentionally public.

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

## Current implementation

```text
- data source selector: Local CSV / Uploaded files / Supabase
- upload controls for CSV/MD/JSON/TXT artifacts
- save uploaded artifacts into Supabase dataset tables
- reload saved runs from Supabase
- render CSV dashboards and Markdown reports from Supabase
```

## Next recommended implementation

```text
1. Add Streamlit smoke test or CI import check.
2. Add Supabase artifact delete/archive action.
3. Add sample_data/processed with scrubbed demo CSV fixtures.
4. Add controlled server-side pipeline runner only after access/auth is stronger.
```