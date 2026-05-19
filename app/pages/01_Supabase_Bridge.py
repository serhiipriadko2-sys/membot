from __future__ import annotations

import hashlib
import io
import os
from typing import Any

import pandas as pd
import streamlit as st

try:
    from supabase import create_client
except Exception:  # pragma: no cover
    create_client = None

SUPABASE_TABLE_RUNS = "dataset_runs"
SUPABASE_TABLE_ARTIFACTS = "dataset_artifacts"
DEFAULT_WALLET = "7BNaxx6KdUYrjACNQZ9He26NBFoFxujQMAfNLnArLGH5"

LABELS = {
    "wallet_swaps": "Raw swaps",
    "trades_paired": "FIFO trades",
    "daily_pnl_calendar": "Daily PnL",
    "priority_fee_jito_audit": "Fee/Jito audit",
    "trigger_tests": "Pre-buy triggers",
    "entry_exit_hypothesis_tests": "Entry/exit hypotheses",
    "entry_context": "Entry context",
    "control_points": "Control points",
    "daily_pnl_calendar_report": "Daily PnL report",
    "priority_fee_jito_audit_report": "Fee/Jito report",
    "entry_exit_hypothesis_report": "Entry/exit report",
    "other": "Other",
}

KNOWN_TYPES = list(LABELS.keys())

st.set_page_config(page_title="membot · Supabase Bridge", page_icon="DB", layout="wide")


def secret_value(name: str) -> str | None:
    try:
        value = st.secrets[name]
        if value:
            return str(value)
    except Exception:
        pass
    return os.environ.get(name) or None


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def content_format(file_name: str) -> str:
    lower = file_name.lower()
    if lower.endswith(".csv"):
        return "csv"
    if lower.endswith((".md", ".markdown")):
        return "markdown"
    if lower.endswith(".json"):
        return "json"
    return "text"


def dataframe_from_text(text: str) -> pd.DataFrame:
    try:
        return pd.read_csv(io.StringIO(text))
    except Exception as exc:
        return pd.DataFrame({"_load_error": [str(exc)]})


def infer_artifact_type(file_name: str) -> str:
    name = file_name.lower().replace("-", "_")
    aliases = {
        "daily_pnl_calendar_report": "daily_pnl_calendar_report",
        "priority_fee_jito_audit_report": "priority_fee_jito_audit_report",
        "entry_exit_hypothesis_report": "entry_exit_hypothesis_report",
        "daily_pnl_calendar": "daily_pnl_calendar",
        "priority_fee_jito_audit": "priority_fee_jito_audit",
        "entry_exit_hypothesis_tests": "entry_exit_hypothesis_tests",
        "trigger_tests": "trigger_tests",
        "wallet_swaps": "wallet_swaps",
        "trades_paired": "trades_paired",
        "entry_context": "entry_context",
        "control_points": "control_points",
    }
    for needle, artifact_type in aliases.items():
        if needle in name:
            return artifact_type
    return "other"


def app_unlocked() -> bool:
    required_pin = secret_value("APP_ACCESS_PIN")
    if not required_pin:
        return True
    return st.session_state.get("app_access_pin", "") == required_pin


def supabase_error() -> str | None:
    if create_client is None:
        return "Python package `supabase` is not installed."
    if not secret_value("SUPABASE_URL"):
        return "Missing secret `SUPABASE_URL`."
    if not (secret_value("SUPABASE_SERVICE_ROLE_KEY") or secret_value("SUPABASE_KEY")):
        return "Missing secret `SUPABASE_SERVICE_ROLE_KEY` or `SUPABASE_KEY`."
    if not app_unlocked():
        return "Enter the app PIN to unlock Supabase."
    return None


@st.cache_resource(show_spinner=False)
def supabase_client() -> Any | None:
    if create_client is None:
        return None
    url = secret_value("SUPABASE_URL")
    key = secret_value("SUPABASE_SERVICE_ROLE_KEY") or secret_value("SUPABASE_KEY")
    if not url or not key:
        return None
    return create_client(url, key)


def list_runs(limit: int = 50) -> list[dict[str, Any]]:
    err = supabase_error()
    if err:
        st.warning(err)
        return []
    client = supabase_client()
    if client is None:
        st.warning("Supabase client unavailable.")
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
        st.error(f"Supabase runs read failed: {exc}")
        return []


def load_artifacts(run_id: str) -> dict[str, dict[str, Any]]:
    err = supabase_error()
    if err:
        st.warning(err)
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
        st.error(f"Supabase artifacts read failed: {exc}")
        return {}

    artifacts: dict[str, dict[str, Any]] = {}
    for row in response.data or []:
        artifact_type = str(row.get("artifact_type") or "other")
        content_text = str(row.get("content_text") or "")
        # Iskra Forge expects session keys named after artifact types.
        artifacts[artifact_type] = {
            "file": row.get("file_name") or artifact_type,
            "format": row.get("content_format") or "text",
            "rows": int(row.get("row_count") or 0),
            "bytes": len(content_text.encode("utf-8")),
            "sha256": row.get("sha256"),
            "text": content_text,
            "source": "supabase",
            "id": row.get("id"),
            "created_at": row.get("created_at"),
            "metadata": row.get("metadata") or {},
        }
    return artifacts


def save_artifacts(wallet: str, label: str, source: str, notes: str, artifacts: dict[str, dict[str, Any]]) -> str | None:
    err = supabase_error()
    if err:
        st.error(err)
        return None
    client = supabase_client()
    if client is None:
        st.error("Supabase client unavailable.")
        return None
    if not artifacts:
        st.error("No artifacts to save.")
        return None
    stats = {
        "artifact_count": len(artifacts),
        "row_count_total": sum(int(a.get("rows") or 0) for a in artifacts.values()),
        "artifact_types": sorted(artifacts.keys()),
    }
    try:
        run_response = (
            client.table(SUPABASE_TABLE_RUNS)
            .insert({
                "wallet": wallet,
                "label": label or None,
                "source": source or "streamlit_upload",
                "status": "completed",
                "stats": stats,
                "notes": notes or None,
            })
            .execute()
        )
        run_id = run_response.data[0]["id"]
        rows = []
        for artifact_type, artifact in artifacts.items():
            rows.append({
                "run_id": run_id,
                "artifact_type": artifact_type,
                "file_name": artifact.get("file") or f"{artifact_type}.txt",
                "content_format": artifact.get("format") or "text",
                "row_count": int(artifact.get("rows") or 0),
                "sha256": artifact.get("sha256"),
                "content_text": artifact.get("text") or "",
                "metadata": artifact.get("metadata") or {},
            })
        client.table(SUPABASE_TABLE_ARTIFACTS).insert(rows).execute()
        return str(run_id)
    except Exception as exc:
        st.error(f"Supabase save failed: {exc}")
        return None


def render_loaded_artifacts(artifacts: dict[str, dict[str, Any]]) -> None:
    if not artifacts:
        st.info("No artifacts selected yet.")
        return
    rows = []
    for key, value in artifacts.items():
        rows.append({
            "Type": LABELS.get(key, key),
            "Code": key,
            "File": value.get("file"),
            "Format": value.get("format"),
            "Rows": value.get("rows"),
            "Bytes": value.get("bytes"),
            "SHA256": value.get("sha256"),
            "Source": value.get("source", "session"),
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def main() -> None:
    st.title("Supabase Bridge")
    st.caption("Restores Supabase source selection for Iskra Forge without bringing back the old dashboard shell.")

    with st.sidebar:
        st.header("Access")
        st.text_input("PIN", type="password", key="app_access_pin")
        if st.button("Clear Supabase cache", use_container_width=True):
            st.cache_resource.clear()
            st.rerun()

    tab_load, tab_upload = st.tabs(["Load from Supabase", "Upload/save artifacts"])

    with tab_load:
        runs = list_runs()
        if runs:
            labels = [
                f"{str(r.get('created_at') or '')[:19]} | {str(r.get('wallet') or '')[:8]} | {r.get('label') or r.get('source') or 'run'}"
                for r in runs
            ]
            selected = st.selectbox("Run", range(len(labels)), format_func=lambda i: labels[i])
            run = runs[int(selected)]
            st.json(run.get("stats") or {}, expanded=False)
            if st.button("Load selected run into Iskra Forge", use_container_width=True):
                artifacts = load_artifacts(str(run["id"]))
                st.session_state["sf_uploaded"] = artifacts
                st.session_state["supabase_run_id"] = str(run["id"])
                st.success("Loaded into session. Open the `Iskra Forge` page to render live widgets.")
            render_loaded_artifacts(st.session_state.get("sf_uploaded", {}))
        else:
            st.info("No runs found, or Supabase is locked/unconfigured.")

    with tab_upload:
        files = st.file_uploader("CSV / MD / JSON / TXT", type=["csv", "md", "markdown", "json", "txt"], accept_multiple_files=True)
        parsed: dict[str, dict[str, Any]] = {}
        for file in files or []:
            data = file.getvalue()
            text = data.decode("utf-8", errors="replace")
            fmt = content_format(file.name)
            auto = infer_artifact_type(file.name)
            selected_type = st.selectbox(
                f"Type: {file.name}",
                KNOWN_TYPES,
                index=KNOWN_TYPES.index(auto),
                key=f"artifact_type_{file.name}_{sha256_bytes(data)[:8]}",
                format_func=lambda x: LABELS.get(x, x),
            )
            rows = len(dataframe_from_text(text)) if fmt == "csv" else 0
            parsed[selected_type] = {
                "file": file.name,
                "format": fmt,
                "rows": rows,
                "bytes": len(data),
                "sha256": sha256_bytes(data),
                "text": text,
                "source": "upload",
                "metadata": {"uploaded_via": "supabase_bridge"},
            }
        if parsed:
            st.session_state["sf_uploaded"] = parsed
        render_loaded_artifacts(st.session_state.get("sf_uploaded", {}))

        with st.form("save_to_supabase"):
            wallet = st.text_input("Wallet", value=DEFAULT_WALLET)
            label = st.text_input("Run label", value="streamlit-upload")
            source = st.text_input("Source", value="streamlit_upload")
            notes = st.text_area("Notes", value="Uploaded via Supabase Bridge.")
            submitted = st.form_submit_button("Save current session artifacts to Supabase")
        if submitted:
            run_id = save_artifacts(wallet, label, source, notes, st.session_state.get("sf_uploaded", {}))
            if run_id:
                st.success(f"Saved run: {run_id}")


if __name__ == "__main__":
    main()
