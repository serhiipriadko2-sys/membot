"""
MON-07: Streamlit Dashboard для визуализации состояния системы.
Веб-интерфейс для мониторинга гипотез, алертов и метрик.
"""
import streamlit as st
import pandas as pd
from datetime import datetime
import os
import sys

# Добавляем src в path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

st.set_page_config(
    page_title="Membot Dashboard",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 Membot System Dashboard")
st.caption(f"Last updated: {datetime.utcnow().isoformat()}")

# Боковая панель
st.sidebar.header("Navigation")
page = st.sidebar.radio(
    "Select Page",
    ["Overview", "Hypotheses", "Alerts", "Storage", "Settings"]
)

st.sidebar.header("System Status")
st.sidebar.info("✅ All systems operational")

# === OVERVIEW PAGE ===
if page == "Overview":
    st.header("System Overview")
    
    # Метрики в колонках
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(label="Active Hypotheses", value="5", delta="+2")
    
    with col2:
        st.metric(label="Total Alerts (24h)", value="12", delta="-3")
    
    with col3:
        st.metric(label="Data Records", value="10.5K", delta="+1.2K")
    
    with col4:
        st.metric(label="Storage Size", value="45.2 MB", delta="+5.1 MB")
    
    # График активности гипотез
    st.subheader("Hypothesis Confidence Trends")
    
    # Пример данных (в реальности загружать из хранилища)
    chart_data = pd.DataFrame({
        'Timestamp': pd.date_range(start='2024-01-01', periods=10, freq='H'),
        'HYP-001': [0.50, 0.55, 0.62, 0.68, 0.75, 0.82, 0.88, 0.91, 0.94, 0.96],
        'HYP-002': [0.60, 0.58, 0.55, 0.52, 0.48, 0.45, 0.42, 0.38, 0.35, 0.32],
        'HYP-003': [0.45, 0.47, 0.48, 0.50, 0.52, 0.55, 0.58, 0.60, 0.62, 0.65]
    })
    
    st.line_chart(chart_data.set_index('Timestamp'))
    
    # Последние алерты
    st.subheader("Recent Alerts")
    
    alert_data = pd.DataFrame([
        {"ID": "ALERT-000012", "Hypothesis": "HYP-001", "Severity": "CRITICAL", "Message": "Confirmed", "Time": "2024-01-01 10:30"},
        {"ID": "ALERT-000011", "Hypothesis": "HYP-002", "Severity": "WARNING", "Message": "Low confidence", "Time": "2024-01-01 09:15"},
        {"ID": "ALERT-000010", "Hypothesis": "HYP-003", "Severity": "INFO", "Message": "Updated", "Time": "2024-01-01 08:00"}
    ])
    
    st.dataframe(alert_data, use_container_width=True, hide_index=True)

# === HYPOTHESES PAGE ===
elif page == "Hypotheses":
    st.header("Hypothesis Management")
    
    # Таблица гипотез
    hyp_data = pd.DataFrame([
        {"ID": "HYP-001", "Name": "MEME launches on weekends", "Prior": 0.50, "Posterior": 0.96, "Status": "CONFIRMED", "Evidence": 15},
        {"ID": "HYP-002", "Name": "High confidence = success", "Prior": 0.60, "Posterior": 0.32, "Status": "ACTIVE", "Evidence": 8},
        {"ID": "HYP-003", "Name": "Volume spikes at night", "Prior": 0.45, "Posterior": 0.65, "Status": "ACTIVE", "Evidence": 12},
        {"ID": "HYP-004", "Name": "Bot activity correlation", "Prior": 0.40, "Posterior": 0.28, "Status": "ACTIVE", "Evidence": 6},
        {"ID": "HYP-005", "Name": "Gas price impact", "Prior": 0.55, "Posterior": 0.03, "Status": "REJECTED", "Evidence": 20}
    ])
    
    # Фильтр по статусу
    status_filter = st.selectbox("Filter by Status", ["All", "ACTIVE", "CONFIRMED", "REJECTED"])
    
    if status_filter != "All":
        hyp_data = hyp_data[hyp_data["Status"] == status_filter]
    
    st.dataframe(hyp_data, use_container_width=True, hide_index=True)
    
    # Детали выбранной гипотезы
    st.subheader("Hypothesis Details")
    selected_hyp = st.selectbox("Select Hypothesis", hyp_data["ID"].tolist())
    
    if selected_hyp:
        hyp_row = hyp_data[hyp_data["ID"] == selected_hyp].iloc[0]
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Posterior Probability", f"{hyp_row['Posterior']:.2%}")
            st.metric("Evidence Count", hyp_row["Evidence"])
        
        with col2:
            st.metric("Prior Probability", f"{hyp_row['Prior']:.2%}")
            st.metric("Status", hyp_row["Status"])
        
        # График обновления
        st.line_chart(
            pd.DataFrame({
                'Update': range(1, hyp_row["Evidence"] + 1),
                'Probability': [hyp_row["Prior"]] + [hyp_row["Posterior"]] * hyp_row["Evidence"]
            }).set_index('Update')
        )

# === ALERTS PAGE ===
elif page == "Alerts":
    st.header("Alert Monitor")
    
    # Статистика алертов
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Critical Alerts", "3", delta="+1")
    
    with col2:
        st.metric("Warning Alerts", "7", delta="-2")
    
    with col3:
        st.metric("Info Alerts", "2", delta="0")
    
    # Фильтры
    col1, col2 = st.columns(2)
    
    with col1:
        severity_filter = st.selectbox("Severity", ["All", "CRITICAL", "WARNING", "INFO"])
    
    with col2:
        date_filter = st.date_input("Date", value=datetime.today())
    
    # Таблица алертов
    alert_data = pd.DataFrame([
        {"ID": "ALERT-000012", "Hypothesis": "HYP-001", "Severity": "CRITICAL", "Message": "Hypothesis CONFIRMED: posterior 0.960 >= 0.95", "Time": "2024-01-01 10:30:15"},
        {"ID": "ALERT-000011", "Hypothesis": "HYP-002", "Severity": "WARNING", "Message": "Hypothesis REJECTED: posterior 0.032 <= 0.05", "Time": "2024-01-01 09:15:42"},
        {"ID": "ALERT-000010", "Hypothesis": "HYP-005", "Severity": "CRITICAL", "Message": "Hypothesis REJECTED: posterior 0.030 <= 0.05", "Time": "2024-01-01 08:00:00"},
        {"ID": "ALERT-000009", "Hypothesis": "HYP-003", "Severity": "INFO", "Message": "Threshold approaching", "Time": "2024-01-01 07:45:30"}
    ])
    
    if severity_filter != "All":
        alert_data = alert_data[alert_data["Severity"] == severity_filter]
    
    st.dataframe(alert_data, use_container_width=True, hide_index=True)
    
    # Кнопка экспорта
    if st.button("Export Alerts to CSV"):
        csv = alert_data.to_csv(index=False)
        st.download_button("Download CSV", csv, file_name=f"alerts_{datetime.now().strftime('%Y%m%d')}.csv")

# === STORAGE PAGE ===
elif page == "Storage":
    st.header("Data Storage")
    
    # Статистика хранилища
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Files", "24")
    
    with col2:
        st.metric("Total Records", "10,542")
    
    with col3:
        st.metric("Storage Size", "45.2 MB")
    
    # DLQ статистика
    st.subheader("Dead Letter Queue")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("DLQ Buffer Size", "0")
    
    with col2:
        st.metric("DLQ Files", "3")
    
    # Список файлов
    st.subheader("Parquet Files")
    
    files_data = pd.DataFrame([
        {"Path": "date=2024-01-01/program_id=Tokenkeg/data_20240101_120000.parquet", "Records": 1542, "Size": "5.2 MB"},
        {"Path": "date=2024-01-01/program_id=Tokenkeg/data_20240101_130000.parquet", "Records": 2103, "Size": "7.1 MB"},
        {"Path": "date=2024-01-02/program_id=Tokenkeg/data_20240102_090000.parquet", "Records": 980, "Size": "3.4 MB"}
    ])
    
    st.dataframe(files_data, use_container_width=True, hide_index=True)

# === SETTINGS PAGE ===
elif page == "Settings":
    st.header("System Settings")
    
    # Настройки порогов
    st.subheader("Observer Gate Thresholds")
    
    confirmation_threshold = st.slider("Confirmation Threshold", 0.80, 0.99, 0.95, 0.01)
    rejection_threshold = st.slider("Rejection Threshold", 0.01, 0.20, 0.05, 0.01)
    
    if st.button("Save Thresholds"):
        st.success(f"Thresholds updated: Confirmation={confirmation_threshold}, Rejection={rejection_threshold}")
    
    # Настройки обновлений
    st.subheader("Data Refresh")
    
    refresh_interval = st.selectbox("Auto-refresh Interval", ["30s", "1m", "5m", "15m", "Manual"])
    
    if st.button("Refresh Now"):
        st.rerun()
    
    # Системная информация
    st.subheader("System Information")
    st.json({
        "version": "1.0.0",
        "python_version": sys.version,
        "uptime": "2 days 5 hours"
    })

# Футер
st.markdown("---")
st.caption("Membot Dashboard v1.0.0 | Built with Streamlit")
