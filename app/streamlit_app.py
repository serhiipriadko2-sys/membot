from __future__ import annotations

import hashlib
import io
import os
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
import streamlit as st

try:
    import plotly.express as px
except Exception:  # pragma: no cover - app should still open without plotly
    px = None

try:
    from supabase import create_client
except Exception:  # pragma: no cover - Supabase is optional until configured
    create_client = None

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "processed"
REPORTS_DIR = ROOT / "reports"

DATASETS = {
    "wallet_swaps": DATA_DIR / "wallet_swaps.csv",
    "trades_paired": DATA_DIR / "trades_paired.csv",
    "latency_sim": DATA_DIR / "latency_sim.csv",
    "fee_adjusted_pnl": DATA_DIR / "fee_adjusted_pnl.csv",
    "copy_stress_model": DATA_DIR / "copy_stress_model.csv",
    "entry_context": DATA_DIR / "entry_context.csv",
    "trigger_tests": DATA_DIR / "trigger_tests.csv",
    "open_positions": DATA_DIR / "open_positions.csv",
}

KNOWN_ARTIFACT_TYPES = [
    *DATASETS.keys(),
    "metrics_report",
    "entry_context_report",
    "readme",
    "other",
]

SUPABASE_TABLE_RUNS = "dataset_runs"
SUPABASE_TABLE_ARTIFACTS = "dataset_artifacts"

st.set_page_config(
    page_title="membot forensic app",
    page_icon="🧪",
    layout="wide",
)


@st.cache_data(show_spinner=False)
def load_csv(path: str) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(csv_path)
    except Exception as exc:
        return pd.DataFrame({"_load_error": [str(exc)]})


def secret_value(name: str) -> str | None:
    try:
        value = st.secrets[name]
        if value:
            return str(value)
    except Exception:
        pass
    value = os.environ.get(name)
    return value or None


def require_app_access() -> bool:
    """Protect Supabase reads/writes when the app is publicly reachable."""
    required_pin = secret_value("APP_ACCESS_PIN")
    if not required_pin:
        return False
    entered_pin = st.session_state.get("app_access_pin", "")
    return entered_pin == required_pin


@st.cache_resource(show_spinner=False)
def supabase_client() -> Any | None:
    if create_client is None:
        return None
    url = secret_value("SUPABASE_URL")
    # Server-side Streamlit only. Do not put service_role keys in GitHub or browser code.
    key = secret_value("SUPABASE_SERVICE_ROLE_KEY") or secret_value("SUPABASE_KEY")
    if not url or not key:
        return None
    return create_client(url, key)


def get_supabase_error() -> str | None:
    if create_client is None:
        return "Python package `supabase` is not installed. Run `pip install -r requirements.txt`."
    if not secret_value("SUPABASE_URL"):
        return "Missing Streamlit secret `SUPABASE_URL`."
    if not (secret_value("SUPABASE_SERVICE_ROLE_KEY") or secret_value("SUPABASE_KEY")):
        return "Missing Streamlit secret `SUPABASE_SERVICE_ROLE_KEY` or `SUPABASE_KEY`."
    if not secret_value("APP_ACCESS_PIN"):
        return "Missing Streamlit secret `APP_ACCESS_PIN`; Supabase access is locked for safety."
    if not require_app_access():
        return "Enter the correct APP access PIN in the sidebar to unlock Supabase."
    return None


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def decode_text(data: bytes) -> str:
    return data.decode("utf-8", errors="replace")


def infer_artifact_type(file_name: str) -> str:
    name = Path(file_name).stem.lower().replace("-", "_")
    for artifact_type in KNOWN_ARTIFACT_TYPES:
        if artifact_type != "other" and artifact_type in name:
            return artifact_type
    if name in {"metrics", "report", "metrics_report"}:
        return "metrics_report"
    return "other"


def infer_content_format(file_name: str) -> str:
    suffix = Path(file_name).suffix.lower()
    if suffix == ".csv":
        return "csv"
    if suffix == ".json":
        return "json"
    if suffix in {".md", ".markdown"}:
        return "markdown"
    return "text"


def dataframe_from_text(content_text: str) -> pd.DataFrame:
    try:
        return pd.read_csv(io.StringIO(content_text))
    except Exception as exc:
        return pd.DataFrame({"_load_error": [str(exc)]})


def artifact_to_dataframe(artifact: dict[str, Any] | None) -> pd.DataFrame:
    if not artifact:
        return pd.DataFrame()
    if artifact.get("content_format") != "csv":
        return pd.DataFrame()
    return dataframe_from_text(str(artifact.get("content_text") or ""))


def local_dataset_status() -> pd.DataFrame:
    rows = []
    for name, path in DATASETS.items():
        exists = path.exists()
        rows.append(
            {
                "dataset": name,
                "path": str(path.relative_to(ROOT)),
                "exists": exists,
                "bytes": path.stat().st_size if exists else 0,
                "rows": len(load_csv(str(path))) if exists else 0,
                "source": "local",
            }
        )
    return pd.DataFrame(rows)


def artifact_status(source: str, artifacts: dict[str, dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for name in DATASETS.keys():
        artifact = artifacts.get(name)
        rows.append(
            {
                "dataset": name,
                "path": artifact.get("file_name") if artifact else "—",
                "exists": artifact is not None,
                "bytes": artifact.get("bytes", 0) if artifact else 0,
                "rows": artifact.get("row_count", 0) if artifact else 0,
                "source": source,
            }
        )
    return pd.DataFrame(rows)


def uploaded_artifacts() -> dict[str, dict[str, Any]]:
    return st.session_state.get("uploaded_artifacts", {})


def selected_supabase_artifacts() -> dict[str, dict[str, Any]]:
    return st.session_state.get("supabase_artifacts", {})


def current_source() -> str:
    return st.session_state.get("data_source", "Local CSV")


def dataset_status() -> pd.DataFrame:
    source = current_source()
    if source == "Uploaded files":
        return artifact_status("upload", uploaded_artifacts())
    if source == "Supabase":
        return artifact_status("supabase", selected_supabase_artifacts())
    return local_dataset_status()


def get_dataset_df(name: str) -> pd.DataFrame:
    source = current_source()
    if source == "Uploaded files":
        return artifact_to_dataframe(uploaded_artifacts().get(name))
    if source == "Supabase":
        return artifact_to_dataframe(selected_supabase_artifacts().get(name))
    path = DATASETS.get(name)
    return load_csv(str(path)) if path else pd.DataFrame()


def find_col(df: pd.DataFrame, candidates: Iterable[str]) -> str | None:
    existing = set(df.columns)
    for col in candidates:
        if col in existing:
            return col
    return None


def metric_number(value: object, fallback: str = "—") -> str:
    if value is None:
        return fallback
    try:
        if pd.isna(value):
            return fallback
    except Exception:
        pass
    if isinstance(value, float):
        return f"{value:,.4f}".rstrip("0").rstrip(".")
    return str(value)


def render_missing(name: str, path: Path | None = None) -> None:
    source = current_source()
    if source == "Local CSV" and path is not None:
        st.info(
            f"`{name}` не найден: `{path.relative_to(ROOT)}`. "
            "Сначала запусти pipeline или положи CSV в `data/processed/`."
        )
    else:
        st.info(f"`{name}` не найден в источнике `{source}`.")


def pnl_column(df: pd.DataFrame) -> str | None:
    return find_col(
        df,
        [
            "net_pnl_sol",
            "pnl_sol",
            "gross_pnl_sol",
            "net_pnl_usd",
            "copy_net_pnl_usd",
            "verified_fifo_unrealized_pnl_usd",
        ],
    )


def list_supabase_runs(limit: int = 50) -> list[dict[str, Any]]:
    error = get_supabase_error()
    if error:
        st.warning(error)
        return []
    client = supabase_client()
    if client is None:
        st.warning("Supabase client is not available.")
        return []
    try:
        response = (
            client.table(SUPABASE_TABLE_RUNS)
            .select("id,created_at,wallet,label,source,status,stats,notes")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return list(response.data or [])
    except Exception as exc:
        st.error(f"Supabase list_runs failed: {exc}")
        return []


def load_supabase_artifacts(run_id: str) -> dict[str, dict[str, Any]]:
    error = get_supabase_error()
    if error:
        st.warning(error)
        return {}
    client = supabase_client()
    if client is None:
        return {}
    try:
        response = (
            client.table(SUPABASE_TABLE_ARTIFACTS)
            .select("id,artifact_type,file_name,content_format,row_count,sha256,content_text,metadata,created_at")
            .eq("run_id", run_id)
            .order("created_at", desc=False)
            .execute()
        )
    except Exception as exc:
        st.error(f"Supabase load_artifacts failed: {exc}")
        return {}

    artifacts: dict[str, dict[str, Any]] = {}
    for row in response.data or []:
        artifact_type = str(row.get("artifact_type") or "other")
        content_text = str(row.get("content_text") or "")
        artifacts[artifact_type] = {
            "id": row.get("id"),
            "artifact_type": artifact_type,
            "file_name": row.get("file_name") or artifact_type,
            "content_format": row.get("content_format") or "text",
            "row_count": row.get("row_count") or 0,
            "sha256": row.get("sha256"),
            "content_text": content_text,
            "metadata": row.get("metadata") or {},
            "bytes": len(content_text.encode("utf-8")),
            "created_at": row.get("created_at"),
        }
    return artifacts


def save_artifacts_to_supabase(
    *,
    wallet: str,
    label: str,
    source: str,
    notes: str,
    artifacts: dict[str, dict[str, Any]],
) -> str | None:
    error = get_supabase_error()
    if error:
        st.error(error)
        return None
    if not artifacts:
        st.error("No uploaded artifacts to save.")
        return None

    client = supabase_client()
    if client is None:
        st.error("Supabase client is not available.")
        return None

    stats = {
        "artifact_count": len(artifacts),
        "row_count_total": sum(int(a.get("row_count") or 0) for a in artifacts.values()),
        "artifact_types": sorted(artifacts.keys()),
    }
    try:
        run_response = (
            client.table(SUPABASE_TABLE_RUNS)
            .insert(
                {
                    "wallet": wallet,
                    "label": label or None,
                    "source": source or "streamlit_upload",
                    "status": "completed",
                    "stats": stats,
                    "notes": notes or None,
                }
            )
            .execute()
        )
        run_id = run_response.data[0]["id"]

        rows = []
        for artifact_type, artifact in artifacts.items():
            rows.append(
                {
                    "run_id": run_id,
                    "artifact_type": artifact_type,
                    "file_name": artifact.get("file_name") or f"{artifact_type}.txt",
                    "content_format": artifact.get("content_format") or "text",
                    "row_count": int(artifact.get("row_count") or 0),
                    "sha256": artifact.get("sha256"),
                    "content_text": artifact.get("content_text") or "",
                    "metadata": artifact.get("metadata") or {},
                }
            )
        client.table(SUPABASE_TABLE_ARTIFACTS).insert(rows).execute()
        return run_id
    except Exception as exc:
        st.error(f"Supabase save failed: {exc}")
        return None


def render_sidebar() -> None:
    with st.sidebar:
        st.header("Guardrails")
        st.write("✅ Reads CSV/MD artifacts")
        st.write("✅ No private keys")
        st.write("✅ No trading execution")
        st.write("⚠️ Dashboard metrics are not final algorithm claims")

        st.divider()
        st.header("Data source")
        st.selectbox(
            "Source",
            ["Local CSV", "Uploaded files", "Supabase"],
            key="data_source",
            help="Supabase requires Streamlit secrets and APP_ACCESS_PIN.",
        )

        st.text_input("APP access PIN", type="password", key="app_access_pin")

        if current_source() == "Supabase":
            runs = list_supabase_runs()
            if runs:
                labels = [
                    f"{r.get('created_at', '')[:19]} | {r.get('wallet', '')[:8]} | {r.get('label') or r.get('source') or 'run'}"
                    for r in runs
                ]
                selected_idx = st.selectbox("Supabase run", range(len(labels)), format_func=lambda i: labels[i])
                selected_run = runs[int(selected_idx)]
                selected_run_id = str(selected_run["id"])
                if st.session_state.get("supabase_run_id") != selected_run_id:
                    st.session_state["supabase_run_id"] = selected_run_id
                    st.session_state["supabase_artifacts"] = load_supabase_artifacts(selected_run_id)
                if st.button("Refresh Supabase artifacts"):
                    st.session_state["supabase_artifacts"] = load_supabase_artifacts(selected_run_id)
                    st.rerun()
            else:
                st.info("No Supabase runs available yet.")

        if st.button("Clear cache"):
            st.cache_data.clear()
            st.cache_resource.clear()
            st.rerun()


def render_upload_and_save() -> None:
    st.subheader("Upload CSV/MD and save to Supabase")
    st.write(
        "Загружай `wallet_swaps.csv`, `trades_paired.csv`, `latency_sim.csv`, "
        "`trigger_tests.csv`, `metrics_report.md` и другие артефакты. "
        "Файлы читаются в память; секреты не нужны в CSV."
    )

    uploaded_files = st.file_uploader(
        "Upload artifacts",
        type=["csv", "md", "markdown", "json", "txt"],
        accept_multiple_files=True,
    )

    parsed: dict[str, dict[str, Any]] = {}
    if uploaded_files:
        st.markdown("### Uploaded artifacts")
        for uploaded_file in uploaded_files:
            data = uploaded_file.getvalue()
            digest = sha256_bytes(data)
            content_text = decode_text(data)
            auto_type = infer_artifact_type(uploaded_file.name)
            format_type = infer_content_format(uploaded_file.name)
            key = f"artifact_type_{uploaded_file.name}_{digest[:8]}"
            artifact_type = st.selectbox(
                f"Artifact type for `{uploaded_file.name}`",
                KNOWN_ARTIFACT_TYPES,
                index=KNOWN_ARTIFACT_TYPES.index(auto_type),
                key=key,
            )

            row_count = 0
            if format_type == "csv":
                preview_df = dataframe_from_text(content_text)
                row_count = 0 if preview_df.empty else len(preview_df)
                with st.expander(f"Preview {uploaded_file.name}", expanded=False):
                    st.dataframe(preview_df.head(50), use_container_width=True)
            elif format_type == "markdown":
                with st.expander(f"Preview {uploaded_file.name}", expanded=False):
                    st.markdown(content_text[:8000])
            else:
                with st.expander(f"Preview {uploaded_file.name}", expanded=False):
                    st.code(content_text[:8000])

            parsed[artifact_type] = {
                "artifact_type": artifact_type,
                "file_name": uploaded_file.name,
                "content_format": format_type,
                "row_count": row_count,
                "sha256": digest,
                "content_text": content_text,
                "metadata": {"uploaded_via": "streamlit_app"},
                "bytes": len(data),
            }

        st.session_state["uploaded_artifacts"] = parsed
    elif not uploaded_artifacts():
        st.info("No files uploaded yet.")

    artifacts = uploaded_artifacts()
    if artifacts:
        st.markdown("### Current uploaded artifact map")
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "artifact_type": key,
                        "file_name": value.get("file_name"),
                        "format": value.get("content_format"),
                        "rows": value.get("row_count"),
                        "bytes": value.get("bytes"),
                        "sha256": value.get("sha256"),
                    }
                    for key, value in artifacts.items()
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("### Save to Supabase")
        access_error = get_supabase_error()
        if access_error:
            st.warning(access_error)
        with st.form("save_artifacts_form"):
            wallet = st.text_input("Wallet", value="7BNaxx6KdUYrjACNQZ9He26NBFoFxujQMAfNLnArLGH5")
            label = st.text_input("Run label", value="mobile-upload")
            source = st.text_input("Source", value="streamlit_upload")
            notes = st.text_area("Notes", value="Uploaded from mobile Streamlit app.")
            submitted = st.form_submit_button("Save uploaded artifacts to Supabase")

        if submitted:
            run_id = save_artifacts_to_supabase(
                wallet=wallet,
                label=label,
                source=source,
                notes=notes,
                artifacts=artifacts,
            )
            if run_id:
                st.success(f"Saved to Supabase dataset_runs.id = `{run_id}`")
                st.session_state["data_source"] = "Supabase"
                st.session_state["supabase_run_id"] = run_id
                st.session_state["supabase_artifacts"] = load_supabase_artifacts(run_id)


def render_overview() -> None:
    status = dataset_status()
    st.subheader("Data health")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Datasets present", int(status["exists"].sum()))
    c2.metric("Known datasets", len(status))
    c3.metric("Total rows", int(status["rows"].sum()))
    c4.metric("Total bytes", int(status["bytes"].sum()))
    st.dataframe(status, use_container_width=True, hide_index=True)

    swaps = get_dataset_df("wallet_swaps")
    paired = get_dataset_df("trades_paired")

    st.subheader("Pipeline snapshot")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("wallet_swaps rows", len(swaps) if not swaps.empty else 0)
    k2.metric("paired trades", len(paired) if not paired.empty else 0)

    side_col = find_col(swaps, ["side", "swap_side"])
    if side_col and not swaps.empty:
        k3.metric("BUY rows", int((swaps[side_col].astype(str).str.upper() == "BUY").sum()))
        k4.metric("SELL rows", int((swaps[side_col].astype(str).str.upper() == "SELL").sum()))
    else:
        k3.metric("BUY rows", "—")
        k4.metric("SELL rows", "—")

    pcol = pnl_column(paired)
    if pcol and not paired.empty:
        pnl = pd.to_numeric(paired[pcol], errors="coerce")
        wins = (pnl > 0).sum()
        total = pnl.sum()
        st.metric("Paired total PnL", metric_number(float(total)))
        st.metric("Win rate", f"{wins / max(1, pnl.notna().sum()):.1%}")


def render_swaps() -> None:
    df = get_dataset_df("wallet_swaps")
    if df.empty:
        render_missing("wallet_swaps", DATASETS.get("wallet_swaps"))
        return

    st.subheader("Normalized wallet swaps")
    side_col = find_col(df, ["side", "swap_side"])
    confidence_col = find_col(df, ["parse_confidence", "confidence"])

    c1, c2, c3 = st.columns(3)
    c1.metric("Rows", len(df))
    c2.metric("Unique mints", df["token_mint"].nunique() if "token_mint" in df.columns else "—")
    c3.metric("Failed rows", int((df[side_col].astype(str).str.upper() == "FAILED").sum()) if side_col else "—")

    if side_col and px is not None:
        st.plotly_chart(px.histogram(df, x=side_col, title="Side distribution"), use_container_width=True)
    if confidence_col and px is not None:
        st.plotly_chart(px.histogram(df, x=confidence_col, title="Parse confidence"), use_container_width=True)

    st.dataframe(df.head(500), use_container_width=True)


def render_trades() -> None:
    df = get_dataset_df("trades_paired")
    if df.empty:
        render_missing("trades_paired", DATASETS.get("trades_paired"))
        return

    st.subheader("Paired FIFO trades")
    pcol = pnl_column(df)
    hold_col = find_col(df, ["hold_seconds", "holding_seconds"])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Trades", len(df))
    if pcol:
        pnl = pd.to_numeric(df[pcol], errors="coerce")
        c2.metric("Total PnL", metric_number(float(pnl.sum())))
        c3.metric("Win rate", f"{(pnl > 0).sum() / max(1, pnl.notna().sum()):.1%}")
        c4.metric("Profit factor", metric_number(pnl[pnl > 0].sum() / abs(pnl[pnl < 0].sum()) if (pnl < 0).any() else None))
    else:
        c2.metric("Total PnL", "—")
        c3.metric("Win rate", "—")
        c4.metric("Profit factor", "—")

    if pcol and px is not None:
        st.plotly_chart(px.histogram(df, x=pcol, nbins=80, title="PnL distribution"), use_container_width=True)
    if hold_col and px is not None:
        st.plotly_chart(px.histogram(df, x=hold_col, nbins=80, title="Hold seconds distribution"), use_container_width=True)

    st.dataframe(df.head(500), use_container_width=True)


def render_latency_and_copy() -> None:
    st.subheader("Latency / copy-stress")
    for name in ["latency_sim", "copy_stress_model", "fee_adjusted_pnl"]:
        df = get_dataset_df(name)
        with st.expander(name, expanded=not df.empty):
            if df.empty:
                render_missing(name, DATASETS.get(name))
                continue
            st.dataframe(df.head(500), use_container_width=True)
            scenario_col = find_col(df, ["scenario", "delay_label"])
            pcol = pnl_column(df)
            if scenario_col and pcol and px is not None:
                plot_df = df.copy()
                plot_df[pcol] = pd.to_numeric(plot_df[pcol], errors="coerce")
                grouped = plot_df.groupby(scenario_col, as_index=False)[pcol].sum()
                st.plotly_chart(px.bar(grouped, x=scenario_col, y=pcol, title=f"{name}: PnL by scenario"), use_container_width=True)


def render_entry_context() -> None:
    st.subheader("Entry context / trigger tests")
    for name in ["entry_context", "trigger_tests"]:
        df = get_dataset_df(name)
        with st.expander(name, expanded=not df.empty):
            if df.empty:
                render_missing(name, DATASETS.get(name))
                continue
            st.dataframe(df.head(500), use_container_width=True)


def markdown_artifacts_for_source() -> dict[str, str]:
    source = current_source()
    if source == "Uploaded files":
        artifacts = uploaded_artifacts()
    elif source == "Supabase":
        artifacts = selected_supabase_artifacts()
    else:
        artifacts = {}
    return {
        key: str(value.get("content_text") or "")
        for key, value in artifacts.items()
        if value.get("content_format") in {"markdown", "text"}
    }


def render_reports() -> None:
    st.subheader("Markdown reports")
    markdown_artifacts = markdown_artifacts_for_source()
    if markdown_artifacts:
        selected = st.selectbox("Artifact report", sorted(markdown_artifacts.keys()))
        st.markdown(markdown_artifacts[selected])
        return

    if not REPORTS_DIR.exists():
        st.info("`reports/` пока не найден.")
        return
    reports = sorted(REPORTS_DIR.glob("*.md"))
    if not reports:
        st.info("В `reports/` пока нет `.md` отчётов.")
        return
    selected = st.selectbox("Report", [str(p.relative_to(ROOT)) for p in reports])
    report_path = ROOT / selected
    st.markdown(report_path.read_text(encoding="utf-8", errors="replace"))


def main() -> None:
    st.title("membot forensic app")
    st.caption("Read-only dashboard for Solana wallet replay outputs. Upload/save artifacts. No trading. No private keys.")
    render_sidebar()

    tabs = st.tabs([
        "Overview",
        "Swaps",
        "Paired trades",
        "Latency / copy",
        "Entry context",
        "Reports",
        "Upload / Supabase",
    ])
    with tabs[0]:
        render_overview()
    with tabs[1]:
        render_swaps()
    with tabs[2]:
        render_trades()
    with tabs[3]:
        render_latency_and_copy()
    with tabs[4]:
        render_entry_context()
    with tabs[5]:
        render_reports()
    with tabs[6]:
        render_upload_and_save()


if __name__ == "__main__":
    main()
