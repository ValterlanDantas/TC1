# Dashboard Streamlit para métricas da Books API
from __future__ import annotations
import os
from typing import Iterable, Tuple, Optional, Dict, Any

import altair as alt
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="Books API - Dashboard", layout="wide")
st.title("📊 Books API – Monitoramento & Analytics")

# ---------------- Config ----------------
def _get_api_base_url():
    v = os.getenv("API_BASE_URL")
    if v: return v
    try:
        return st.secrets["API_BASE_URL"]
    except Exception:
        # fallback local (nome do serviço do compose)
        return "http://tc01_api:8000"

API_BASE_URL = _get_api_base_url()

# Endpoint agregado (o que você já tem) e opcional de entradas (se existir)
ENDPOINT_OVERVIEW = os.getenv("METRICS_ENDPOINT", "/api/v1/metrics/overview").strip()
ENDPOINT_ENTRIES  = os.getenv("METRICS_ENTRIES",  "/api/v1/metrics/entries").strip()

# auto-refresh 30s
if getattr(st, "autorefresh", None):
    st.autorefresh(interval=30_000, key="data_refresh")

st.caption(f"Fonte (overview): {API_BASE_URL}{ENDPOINT_OVERVIEW}")

# ---------------- Fetch helpers ----------------
def http_get_json(url: str, timeout: int = 20) -> Dict[str, Any]:
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    return r.json()

def try_fetch_entries(api_base: str, endpoint: str) -> Optional[pd.DataFrame]:
    """Tenta buscar uma lista de logs (entradas). Retorna DataFrame ou None."""
    try:
        url = f"{api_base.rstrip('/')}{endpoint}"
        payload = http_get_json(url)
    except Exception:
        return None

    rows = None
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        for k in ("entries", "items", "logs", "data", "rows"):
            v = payload.get(k)
            if isinstance(v, list):
                rows = v
                break

    if not rows:
        return None

    df = pd.DataFrame(rows)
    rename_map = {
        "timestamp": "ts",
        "time": "ts",
        "route": "path",
        "code": "status",
        "latency": "latency_s",
        "duration": "latency_s",
        "duration_s": "latency_s",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns and v not in df.columns})

    if "ts" in df.columns:       df["ts"] = pd.to_datetime(df["ts"], errors="coerce")
    if "status" in df.columns:   df["status"] = pd.to_numeric(df["status"], errors="coerce")
    if "latency_s" in df.columns:df["latency_s"] = pd.to_numeric(df["latency_s"], errors="coerce")

    for col in ("ts","method","path","status","latency_s"):
        if col not in df.columns: df[col] = pd.NA

    return df.dropna(how="all", subset=["method","path","status"])

def fetch_overview(api_base: str, endpoint: str) -> Dict[str, Any]:
    url = f"{api_base.rstrip('/')}{endpoint}"
    return http_get_json(url)

# ---------------- Load data ----------------
overview = fetch_overview(API_BASE_URL, ENDPOINT_OVERVIEW)

# KPIs do overview (sempre disponíveis)
total_requests = int(overview.get("total_requests", 0) or 0)
avg_resp_s     = float(overview.get("avg_response_time_s", 0) or 0)
errors         = overview.get("errors", {}) or {}
err_rate       = float(errors.get("error_rate", 0) or 0)

# Top endpoints agregados (dict path->count)
top_endpoints: Dict[str, int] = overview.get("top_endpoints", {}) or {}

# Tenta entradas detalhadas (opcional)
df = try_fetch_entries(API_BASE_URL, ENDPOINT_ENTRIES)

# ---------------- KPIs ----------------
c1, c2, c3 = st.columns(3)
c1.metric("Total requests", total_requests)
c2.metric("Avg resp (s)", round(avg_resp_s, 4))
c3.metric("Error rate", round(err_rate, 4))

st.divider()

# ---------------- Gráfico: Top endpoints (sempre, via overview) ----------------
st.subheader("Top endpoints (volume)")
if top_endpoints:
    top_df = pd.DataFrame(
        [{"path": p, "count": c} for p, c in top_endpoints.items()]
    ).sort_values("count", ascending=False)
    top_n = st.slider("Quantos exibir", 5, 20, min(10, len(top_df)))
    chart1 = (
        alt.Chart(top_df.head(top_n))
           .mark_bar()
           .encode(
               x=alt.X("count:Q", title="Requisições"),
               y=alt.Y("path:N", sort="-x", title="Endpoint"),
               tooltip=["path","count"]
           )
           .properties(height=30 * max(1, min(top_n, len(top_df))))
    )
    st.altair_chart(chart1, use_container_width=True)
else:
    st.info("Ainda não há top_endpoints no overview. Gere tráfego na API.")

# ---------------- Se houver entradas, plota análises temporais e tabela ----------------
if df is not None and not df.empty:
    st.divider()
    st.subheader("Detalhes (logs) – caso o endpoint de entradas esteja disponível")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        methods = st.multiselect("Métodos", sorted(df["method"].dropna().unique().tolist()))
    with col_b:
        path_contains = st.text_input("Path contém", "")
    with col_c:
        status_min, status_max = st.slider("Faixa de status", 100, 599, (200, 499))

    f = df.copy()
    if methods:
        f = f[f["method"].isin(methods)]
    if path_contains:
        f = f[f["path"].astype(str).str.contains(path_contains, case=False, na=False)]
    f = f[(f["status"] >= status_min) & (f["status"] <= status_max)]

    # Latência no tempo (se houver ts)
    if "ts" in f.columns and f["ts"].notna().any() and "latency_s" in f.columns:
        f2 = (
            f.dropna(subset=["ts"])
             .set_index("ts")
             .resample("1min")
             .agg({"latency_s": "mean"})
             .rename(columns={"latency_s": "latency_mean_s"})
             .reset_index()
        )
        if not f2.empty:
            chart2 = (
                alt.Chart(f2)
                   .mark_line()
                   .encode(
                       x=alt.X("ts:T", title="Tempo"),
                       y=alt.Y("latency_mean_s:Q", title="Latência média (s)"),
                       tooltip=["ts:T","latency_mean_s:Q"]
                   )
                   .properties(height=300, title="Latência média por minuto")
            )
            st.altair_chart(chart2, use_container_width=True)

    # Proporção por classe HTTP
    if "status" in f.columns:
        status_counts = (
            f.assign(class_=pd.cut(f["status"], bins=[0,199,299,399,499,599], labels=["1xx","2xx","3xx","4xx","5xx"]))
             .groupby(["class_", "method"], dropna=True)
             .size()
             .reset_index(name="count")
        )
        if not status_counts.empty:
            chart3 = (
                alt.Chart(status_counts)
                   .mark_bar()
                   .encode(
                       x=alt.X("method:N", title="Método"),
                       y=alt.Y("count:Q", stack="normalize", title="Proporção"),
                       color=alt.Color("class_:N", title="Classe HTTP"),
                       tooltip=["method","class_","count"]
                   )
                   .properties(height=300, title="Proporção por Método e Classe HTTP")
            )
            st.altair_chart(chart3, use_container_width=True)

    st.subheader("Últimas requisições (se entradas estiverem disponíveis)")
    cols_show = [c for c in ["ts","method","path","status","latency_s"] if c in f.columns]
    st.dataframe(
        f.sort_values("ts", ascending=False, na_position="last")[cols_show].head(50),
        use_container_width=True
    )
else:
    st.info("Logs detalhados não disponíveis. O dashboard está usando apenas o overview agregado.")

