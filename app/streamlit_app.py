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

RU_DATASET_LABELS = {
    "wallet_swaps": "Свапы кошелька",
    "trades_paired": "FIFO-сделки",
    "latency_sim": "Latency replay",
    "fee_adjusted_pnl": "PnL с комиссиями",
    "copy_stress_model": "Copy-stress модель",
    "entry_context": "Контекст входа",
    "trigger_tests": "Тесты триггеров",
    "open_positions": "Открытые позиции",
    "metrics_report": "Отчёт метрик",
    "entry_context_report": "Отчёт контекста входа",
    "readme": "README / заметки",
    "other": "Другое",
}

KNOWN_ARTIFACT_TYPES = [
    *DATASETS.keys(),
    "metrics_report",
    "entry_context_report",
    "readme",
    "other",
]

SOURCE_LABELS = {
    "Локальные CSV": "local",
    "Загруженные файлы": "upload",
    "Supabase": "supabase",
}

SUPABASE_TABLE_RUNS = "dataset_runs"
SUPABASE_TABLE_ARTIFACTS = "dataset_artifacts"
DEFAULT_WALLET = "7BNaxx6KdUYrjACNQZ9He26NBFoFxujQMAfNLnArLGH5"

st.set_page_config(
    page_title="membot — forensic dashboard",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded",
)


def inject_css() -> None:
    st.markdown(
        """
        <style>
        :root {
          --membot-bg-card: rgba(15, 23, 42, 0.72);
          --membot-border: rgba(148, 163, 184, 0.22);
          --membot-cyan: #38bdf8;
          --membot-green: #22c55e;
          --membot-orange: #f97316;
          --membot-red: #ef4444;
        }
        .block-container {padding-top: 1.2rem; padding-bottom: 3rem; max-width: 1380px;}
        [data-testid="stMetric"] {
          background: linear-gradient(180deg, rgba(15,23,42,.85), rgba(17,24,39,.70));
          border: 1px solid var(--membot-border);
          border-radius: 18px;
          padding: 14px 16px;
          box-shadow: 0 12px 30px rgba(0,0,0,.18);
        }
        [data-testid="stMetricLabel"] {font-size: .82rem; color: #cbd5e1;}
        [data-testid="stMetricValue"] {font-size: 1.42rem;}
        div[data-testid="stExpander"] {
          border: 1px solid var(--membot-border);
          border-radius: 16px;
          overflow: hidden;
        }
        .membot-hero {
          border: 1px solid rgba(56,189,248,.25);
          border-radius: 24px;
          padding: 20px 22px;
          margin: 0 0 18px 0;
          background:
            radial-gradient(circle at top left, rgba(56,189,248,.22), transparent 28%),
            linear-gradient(135deg, rgba(2,6,23,.95), rgba(15,23,42,.82));
          box-shadow: 0 18px 48px rgba(0,0,0,.22);
        }
        .membot-hero h1 {margin: 0 0 6px 0; font-size: 2.1rem; line-height: 1.1;}
        .membot-hero p {margin: 4px 0; color: #cbd5e1; font-size: .98rem;}
        .membot-badges {display: flex; flex-wrap: wrap; gap: 8px; margin-top: 14px;}
        .membot-badge {
          display: inline-flex; align-items: center; gap: 6px;
          border: 1px solid rgba(148,163,184,.26);
          border-radius: 999px; padding: 6px 10px;
          background: rgba(15,23,42,.75); color: #e5e7eb; font-size: .78rem;
        }
        .membot-badge.good {border-color: rgba(34,197,94,.35); color: #bbf7d0;}
        .membot-badge.warn {border-color: rgba(249,115,22,.40); color: #fed7aa;}
        .membot-badge.lock {border-color: rgba(56,189,248,.40); color: #bae6fd;}
        .membot-card {
          border: 1px solid var(--membot-border);
          border-radius: 20px;
          padding: 16px 18px;
          background: var(--membot-bg-card);
          margin-bottom: 12px;
        }
        .membot-card h3 {margin-top: 0; margin-bottom: 8px; font-size: 1.05rem;}
        .membot-muted {color: #94a3b8; font-size: .9rem;}
        .membot-small {font-size: .82rem; color: #94a3b8;}
        .membot-ok {color: #86efac; font-weight: 600;}
        .membot-warn {color: #fdba74; font-weight: 600;}
        .membot-danger {color: #fca5a5; font-weight: 600;}
        @media (max-width: 640px) {
          .block-container {padding-left: .8rem; padding-right: .8rem; padding-top: .8rem;}
          .membot-hero {padding: 16px 15px; border-radius: 18px;}
          .membot-hero h1 {font-size: 1.55rem;}
          [data-testid="stMetric"] {padding: 10px 12px; border-radius: 14px;}
          [data-testid="stMetricValue"] {font-size: 1.1rem;}
          .membot-card {padding: 13px 14px; border-radius: 16px;}
        }
        </style>
        """,
        unsafe_allow_html=True,
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
    key = secret_value("SUPABASE_SERVICE_ROLE_KEY") or secret_value("SUPABASE_KEY")
    if not url or not key:
        return None
    return create_client(url, key)


def get_supabase_error() -> str | None:
    if create_client is None:
        return "Пакет `supabase` не установлен. Проверь `requirements.txt` и перезапусти деплой."
    if not secret_value("SUPABASE_URL"):
        return "Не найден secret `SUPABASE_URL`."
    if not (secret_value("SUPABASE_SERVICE_ROLE_KEY") or secret_value("SUPABASE_KEY")):
        return "Не найден secret `SUPABASE_SERVICE_ROLE_KEY` или `SUPABASE_KEY`."
    if not secret_value("APP_ACCESS_PIN"):
        return "Не найден secret `APP_ACCESS_PIN`; доступ к Supabase заблокирован."
    if not require_app_access():
        return "Введи правильный PIN в сайдбаре, чтобы открыть Supabase."
    return None


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def decode_text(data: bytes) -> str:
    return data.decode("utf-8", errors="replace")


def ru_label(name: str) -> str:
    return RU_DATASET_LABELS.get(name, name)


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
                "Артефакт": ru_label(name),
                "Код": name,
                "Файл": str(path.relative_to(ROOT)),
                "Есть": exists,
                "Байт": path.stat().st_size if exists else 0,
                "Строк": len(load_csv(str(path))) if exists else 0,
                "Источник": "локально",
            }
        )
    return pd.DataFrame(rows)


def artifact_status(source: str, artifacts: dict[str, dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for name in DATASETS.keys():
        artifact = artifacts.get(name)
        rows.append(
            {
                "Артефакт": ru_label(name),
                "Код": name,
                "Файл": artifact.get("file_name") if artifact else "—",
                "Есть": artifact is not None,
                "Байт": artifact.get("bytes", 0) if artifact else 0,
                "Строк": artifact.get("row_count", 0) if artifact else 0,
                "Источник": source,
            }
        )
    return pd.DataFrame(rows)


def uploaded_artifacts() -> dict[str, dict[str, Any]]:
    return st.session_state.get("uploaded_artifacts", {})


def selected_supabase_artifacts() -> dict[str, dict[str, Any]]:
    return st.session_state.get("supabase_artifacts", {})


def current_source() -> str:
    return st.session_state.get("data_source", "Локальные CSV")


def dataset_status() -> pd.DataFrame:
    source = current_source()
    if source == "Загруженные файлы":
        return artifact_status("загрузка", uploaded_artifacts())
    if source == "Supabase":
        return artifact_status("supabase", selected_supabase_artifacts())
    return local_dataset_status()


def get_dataset_df(name: str) -> pd.DataFrame:
    source = current_source()
    if source == "Загруженные файлы":
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


def numeric_series(df: pd.DataFrame, col: str | None) -> pd.Series:
    if not col or col not in df.columns:
        return pd.Series(dtype=float)
    return pd.to_numeric(df[col], errors="coerce")


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
    label = ru_label(name)
    if source == "Локальные CSV" and path is not None:
        st.info(
            f"`{label}` пока не найден: `{path.relative_to(ROOT)}`. "
            "Запусти pipeline или загрузи CSV через вкладку `Загрузка / Supabase`."
        )
    else:
        st.info(f"`{label}` пока не найден в источнике `{source}`.")


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


def time_column(df: pd.DataFrame) -> str | None:
    return find_col(df, ["entry_time_utc", "block_time_utc", "timestamp", "buy_time", "sell_time"])


def list_supabase_runs(limit: int = 50) -> list[dict[str, Any]]:
    error = get_supabase_error()
    if error:
        st.warning(error)
        return []
    client = supabase_client()
    if client is None:
        st.warning("Supabase client недоступен.")
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
        st.error(f"Ошибка чтения runs из Supabase: {exc}")
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
        st.error(f"Ошибка чтения артефактов Supabase: {exc}")
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
        st.error("Нет артефактов для сохранения.")
        return None

    client = supabase_client()
    if client is None:
        st.error("Supabase client недоступен.")
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
        st.error(f"Ошибка сохранения в Supabase: {exc}")
        return None


def render_hero() -> None:
    st.markdown(
        """
        <div class="membot-hero">
          <h1>🧪 membot forensic</h1>
          <p>Русский read-only dashboard для анализа Solana-кошелька: swaps → FIFO → latency → entry context.</p>
          <p class="membot-muted">Это исследовательская панель. Она не торгует, не хранит приватные ключи и не объявляет “алгоритм раскрыт”.</p>
          <div class="membot-badges">
            <span class="membot-badge good">✅ Read-only</span>
            <span class="membot-badge lock">🔐 Supabase через secrets</span>
            <span class="membot-badge warn">⚠️ Метрики ≠ финальный claim</span>
            <span class="membot-badge">📱 Mobile-first</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> None:
    with st.sidebar:
        st.title("membot")
        st.caption("Панель управления источником данных")

        st.markdown("### Источник")
        st.selectbox(
            "Откуда читать данные",
            ["Локальные CSV", "Загруженные файлы", "Supabase"],
            key="data_source",
            help="Для мобильного режима удобнее: загрузка файлов или Supabase.",
        )

        st.text_input("PIN доступа", type="password", key="app_access_pin")

        if current_source() == "Supabase":
            st.markdown("### Supabase runs")
            runs = list_supabase_runs()
            if runs:
                labels = [
                    f"{r.get('created_at', '')[:19]} | {str(r.get('wallet', ''))[:8]} | {r.get('label') or r.get('source') or 'run'}"
                    for r in runs
                ]
                selected_idx = st.selectbox("Выбери прогон", range(len(labels)), format_func=lambda i: labels[i])
                selected_run = runs[int(selected_idx)]
                selected_run_id = str(selected_run["id"])
                if st.session_state.get("supabase_run_id") != selected_run_id:
                    st.session_state["supabase_run_id"] = selected_run_id
                    st.session_state["supabase_artifacts"] = load_supabase_artifacts(selected_run_id)
                if st.button("Обновить Supabase", use_container_width=True):
                    st.session_state["supabase_artifacts"] = load_supabase_artifacts(selected_run_id)
                    st.rerun()
            else:
                st.info("Сохранённых прогонов пока нет или Supabase закрыт.")

        st.markdown("### Безопасность")
        st.write("✅ Только чтение/загрузка артефактов")
        st.write("✅ Без приватных ключей")
        st.write("✅ Без торговых операций")
        st.write("⚠️ Dashboard не является торговым советом")

        if st.button("Очистить кэш", use_container_width=True):
            st.cache_data.clear()
            st.cache_resource.clear()
            st.rerun()


def render_research_status() -> None:
    st.markdown("### Контур исследования")
    cols = st.columns(4)
    cards = [
        ("1", "Raw replay", "signatures → transactions → swaps", "ok"),
        ("2", "FIFO accounting", "paired trades / PnL / hold time", "ok"),
        ("3", "Latency & copy", "stress ≠ real latency replay", "warn"),
        ("4", "Entry context", "нужны controls до claims", "warn"),
    ]
    for col, (num, title, text, mode) in zip(cols, cards):
        klass = "membot-ok" if mode == "ok" else "membot-warn"
        col.markdown(
            f"""
            <div class="membot-card">
              <div class="membot-small">Этап {num}</div>
              <h3>{title}</h3>
              <div class="{klass}">{text}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_quality_notes() -> None:
    with st.expander("Как читать панель — guardrails", expanded=False):
        st.markdown(
            """
            - `wallet_swaps` показывает нормализованные buy/sell события, но не доказывает алгоритм.
            - `trades_paired` — это FIFO-бухгалтерия, а не предсказание покупки.
            - `copy_stress_model` — стресс-модель комиссий/проскальзывания, не настоящий latency replay.
            - `entry_context` становится сильным только вместе с `control_points` и out-of-sample проверкой.
            - Любой `UNKNOWN` лучше, чем красивый ложный вывод.
            """
        )


def render_upload_and_save() -> None:
    st.subheader("📤 Загрузка файлов и сохранение в Supabase")
    st.markdown(
        "Загружай CSV/MD/JSON/TXT артефакты с телефона. Панель покажет preview, посчитает SHA256 и сможет сохранить набор в Supabase."
    )

    uploaded_files = st.file_uploader(
        "Выбери файлы",
        type=["csv", "md", "markdown", "json", "txt"],
        accept_multiple_files=True,
    )

    parsed: dict[str, dict[str, Any]] = {}
    if uploaded_files:
        st.markdown("### Загруженные артефакты")
        for uploaded_file in uploaded_files:
            data = uploaded_file.getvalue()
            digest = sha256_bytes(data)
            content_text = decode_text(data)
            auto_type = infer_artifact_type(uploaded_file.name)
            format_type = infer_content_format(uploaded_file.name)
            key = f"artifact_type_{uploaded_file.name}_{digest[:8]}"
            artifact_type = st.selectbox(
                f"Тип артефакта для `{uploaded_file.name}`",
                KNOWN_ARTIFACT_TYPES,
                index=KNOWN_ARTIFACT_TYPES.index(auto_type),
                key=key,
                format_func=ru_label,
            )

            row_count = 0
            if format_type == "csv":
                preview_df = dataframe_from_text(content_text)
                row_count = 0 if preview_df.empty else len(preview_df)
                with st.expander(f"Preview: {uploaded_file.name}", expanded=False):
                    st.dataframe(preview_df.head(50), use_container_width=True, hide_index=True)
            elif format_type == "markdown":
                with st.expander(f"Preview: {uploaded_file.name}", expanded=False):
                    st.markdown(content_text[:8000])
            else:
                with st.expander(f"Preview: {uploaded_file.name}", expanded=False):
                    st.code(content_text[:8000])

            parsed[artifact_type] = {
                "artifact_type": artifact_type,
                "file_name": uploaded_file.name,
                "content_format": format_type,
                "row_count": row_count,
                "sha256": digest,
                "content_text": content_text,
                "metadata": {"uploaded_via": "streamlit_app", "ui_language": "ru"},
                "bytes": len(data),
            }

        st.session_state["uploaded_artifacts"] = parsed
    elif not uploaded_artifacts():
        st.info("Файлы ещё не загружены.")

    artifacts = uploaded_artifacts()
    if artifacts:
        st.markdown("### Карта текущих артефактов")
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Тип": ru_label(key),
                        "Код": key,
                        "Файл": value.get("file_name"),
                        "Формат": value.get("content_format"),
                        "Строк": value.get("row_count"),
                        "Байт": value.get("bytes"),
                        "SHA256": value.get("sha256"),
                    }
                    for key, value in artifacts.items()
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("### Сохранить в Supabase")
        access_error = get_supabase_error()
        if access_error:
            st.warning(access_error)
        with st.form("save_artifacts_form"):
            wallet = st.text_input("Кошелёк", value=DEFAULT_WALLET)
            label = st.text_input("Название прогона", value="mobile-upload")
            source = st.text_input("Источник", value="streamlit_upload")
            notes = st.text_area("Заметки", value="Загружено через мобильный Streamlit dashboard.")
            submitted = st.form_submit_button("Сохранить артефакты в Supabase")

        if submitted:
            run_id = save_artifacts_to_supabase(
                wallet=wallet,
                label=label,
                source=source,
                notes=notes,
                artifacts=artifacts,
            )
            if run_id:
                st.success(f"Сохранено в Supabase: `dataset_runs.id = {run_id}`")
                st.session_state["data_source"] = "Supabase"
                st.session_state["supabase_run_id"] = run_id
                st.session_state["supabase_artifacts"] = load_supabase_artifacts(run_id)


def render_overview() -> None:
    status = dataset_status()
    st.subheader("📊 Состояние данных")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Артефактов найдено", int(status["Есть"].sum()))
    c2.metric("Ожидается", len(status))
    c3.metric("Всего строк", int(status["Строк"].sum()))
    c4.metric("Всего байт", int(status["Байт"].sum()))
    st.dataframe(status, use_container_width=True, hide_index=True)

    swaps = get_dataset_df("wallet_swaps")
    paired = get_dataset_df("trades_paired")

    st.subheader("🧭 Быстрый снимок pipeline")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Строк swaps", len(swaps) if not swaps.empty else 0)
    k2.metric("FIFO-сделок", len(paired) if not paired.empty else 0)

    side_col = find_col(swaps, ["side", "swap_side"])
    if side_col and not swaps.empty:
        side = swaps[side_col].astype(str).str.upper()
        k3.metric("BUY", int((side == "BUY").sum()))
        k4.metric("SELL", int((side == "SELL").sum()))
    else:
        k3.metric("BUY", "—")
        k4.metric("SELL", "—")

    pcol = pnl_column(paired)
    if pcol and not paired.empty:
        pnl = pd.to_numeric(paired[pcol], errors="coerce")
        wins = (pnl > 0).sum()
        total = pnl.sum()
        m1, m2, m3 = st.columns(3)
        m1.metric("PnL FIFO", metric_number(float(total)))
        m2.metric("Win rate", f"{wins / max(1, pnl.notna().sum()):.1%}")
        if (pnl < 0).any():
            m3.metric("Profit factor", metric_number(float(pnl[pnl > 0].sum() / abs(pnl[pnl < 0].sum()))))
        else:
            m3.metric("Profit factor", "—")

    render_research_status()
    render_quality_notes()


def render_swaps() -> None:
    df = get_dataset_df("wallet_swaps")
    if df.empty:
        render_missing("wallet_swaps", DATASETS.get("wallet_swaps"))
        return

    st.subheader("🔁 Нормализованные свапы")
    side_col = find_col(df, ["side", "swap_side"])
    confidence_col = find_col(df, ["parse_confidence", "confidence"])
    mint_col = find_col(df, ["token_mint", "mint"])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Строк", len(df))
    c2.metric("Уникальных mint", df[mint_col].nunique() if mint_col else "—")
    c3.metric("FAILED", int((df[side_col].astype(str).str.upper() == "FAILED").sum()) if side_col else "—")
    c4.metric("UNKNOWN", int((df[side_col].astype(str).str.upper() == "UNKNOWN").sum()) if side_col else "—")

    if side_col and px is not None:
        st.plotly_chart(px.histogram(df, x=side_col, title="Распределение BUY / SELL / FAILED"), use_container_width=True)
    if confidence_col and px is not None:
        st.plotly_chart(px.histogram(df, x=confidence_col, title="Качество парсинга"), use_container_width=True)

    st.dataframe(df.head(500), use_container_width=True, hide_index=True)


def render_trades() -> None:
    df = get_dataset_df("trades_paired")
    if df.empty:
        render_missing("trades_paired", DATASETS.get("trades_paired"))
        return

    st.subheader("🧾 FIFO-сделки")
    pcol = pnl_column(df)
    hold_col = find_col(df, ["hold_seconds", "holding_seconds"])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Сделок", len(df))
    pnl = numeric_series(df, pcol)
    if not pnl.empty:
        c2.metric("PnL", metric_number(float(pnl.sum())))
        c3.metric("Win rate", f"{(pnl > 0).sum() / max(1, pnl.notna().sum()):.1%}")
        c4.metric("Profit factor", metric_number(float(pnl[pnl > 0].sum() / abs(pnl[pnl < 0].sum()))) if (pnl < 0).any() else "—")
    else:
        c2.metric("PnL", "—")
        c3.metric("Win rate", "—")
        c4.metric("Profit factor", "—")

    if pcol and px is not None:
        st.plotly_chart(px.histogram(df, x=pcol, nbins=80, title="Распределение PnL"), use_container_width=True)
    if hold_col and px is not None:
        st.plotly_chart(px.histogram(df, x=hold_col, nbins=80, title="Время удержания, секунд"), use_container_width=True)

    st.dataframe(df.head(500), use_container_width=True, hide_index=True)


def render_latency_and_copy() -> None:
    st.subheader("⏱️ Latency / copy-stress")
    st.caption("Copy-stress — это экономическая стресс-модель. Это не настоящий latency replay без price_series coverage.")
    for name in ["latency_sim", "copy_stress_model", "fee_adjusted_pnl"]:
        df = get_dataset_df(name)
        with st.expander(ru_label(name), expanded=not df.empty):
            if df.empty:
                render_missing(name, DATASETS.get(name))
                continue
            st.dataframe(df.head(500), use_container_width=True, hide_index=True)
            scenario_col = find_col(df, ["scenario", "delay_label"])
            pcol = pnl_column(df)
            if scenario_col and pcol and px is not None:
                plot_df = df.copy()
                plot_df[pcol] = pd.to_numeric(plot_df[pcol], errors="coerce")
                grouped = plot_df.groupby(scenario_col, as_index=False)[pcol].sum()
                st.plotly_chart(px.bar(grouped, x=scenario_col, y=pcol, title=f"{ru_label(name)}: PnL по сценариям"), use_container_width=True)


def render_entry_context() -> None:
    st.subheader("🧠 Контекст входа и триггеры")
    st.caption("Prediction claim разрешён только после сравнения entry points с control points и out-of-sample проверки.")
    for name in ["entry_context", "trigger_tests"]:
        df = get_dataset_df(name)
        with st.expander(ru_label(name), expanded=not df.empty):
            if df.empty:
                render_missing(name, DATASETS.get(name))
                continue
            st.dataframe(df.head(500), use_container_width=True, hide_index=True)

            coverage_col = find_col(df, ["feature_coverage_pct", "context_coverage", "coverage_pct"])
            if coverage_col and px is not None:
                st.plotly_chart(px.histogram(df, x=coverage_col, title="Покрытие признаков"), use_container_width=True)


def markdown_artifacts_for_source() -> dict[str, str]:
    source = current_source()
    if source == "Загруженные файлы":
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
    st.subheader("📄 Отчёты")
    markdown_artifacts = markdown_artifacts_for_source()
    if markdown_artifacts:
        selected = st.selectbox("Отчёт из артефактов", sorted(markdown_artifacts.keys()), format_func=ru_label)
        st.markdown(markdown_artifacts[selected])
        return

    if not REPORTS_DIR.exists():
        st.info("Папка `reports/` пока не найдена.")
        return
    reports = sorted(REPORTS_DIR.glob("*.md"))
    if not reports:
        st.info("В `reports/` пока нет `.md` отчётов.")
        return
    selected = st.selectbox("Отчёт", [str(p.relative_to(ROOT)) for p in reports])
    report_path = ROOT / selected
    st.markdown(report_path.read_text(encoding="utf-8", errors="replace"))


def main() -> None:
    inject_css()
    render_hero()
    render_sidebar()

    tabs = st.tabs(
        [
            "🏠 Обзор",
            "🔁 Свапы",
            "🧾 FIFO",
            "⏱️ Latency / copy",
            "🧠 Entry context",
            "📄 Отчёты",
            "📤 Загрузка / Supabase",
        ]
    )
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
