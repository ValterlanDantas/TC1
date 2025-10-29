#Dashboard desenvolvido com Streamlit para visualização de métricas da API de livros.
# src/tc_01/dashboard/app.py
from __future__ import annotations

import os
import re
import json
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

# --- Paths ---
# __file__ = .../src/tc_01/dashboard/app.py
# parents[0]=dashboard, [1]=tc_01, [2]=src, [3]=<PROJETO (TC1)>
PROJECT_ROOT = Path(__file__).resolve().parents[3]
# Use a var de ambiente LOG_FILE se existir; senão, padrão na raiz do projeto
LOG_FILE = Path(os.getenv("LOG_FILE", PROJECT_ROOT / "api_logs.log"))

st.set_page_config(page_title="Books API - Dashboard", layout="wide")
st.title("📊 Books API – Monitoramento & Analytics")
st.caption(f"Arquivo de log alvo: {LOG_FILE}")

if not LOG_FILE.exists():
    st.warning(f"Nenhum log encontrado em: {LOG_FILE}")
    st.info("Dica: inicie a API com a mesma variável de ambiente LOG_FILE e gere tráfego nas rotas.")
    st.stop()

@st.cache_data(ttl=10)
def load_df(log_path: Path) -> pd.DataFrame:
    """
    Lê arquivo de log em TEXTO (não JSONL) no formato:
    2025-10-28 19:29:05,013 - INFO - GET /api/v1/health status=403 0.001s

    Retorna DataFrame com colunas:
    ts (datetime), method, path, status (int), latency_s (float)
    """
    rows = []
    parsed, skipped = 0, 0

    # Ex.: 2025-10-28 19:29:05,013 - INFO - GET /api/v1/health status=403 0.001s
    rx = re.compile(
        r"""^(?P<ts>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2},\d{3})\s+-\s+\w+\s+-\s+
            (?P<method>GET|POST|PUT|DELETE|PATCH|OPTIONS|HEAD)\s+
            (?P<path>\S+)\s+
            status=(?P<status>\d{3})\s+
            (?P<latency_s>\d+(?:\.\d+)?)s\s*$""",
        re.VERBOSE
    )

    with log_path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            m = rx.match(line)
            if m:
                rows.append({
                    "ts": m.group("ts"),
                    "method": m.group("method"),
                    "path": m.group("path"),
                    "status": int(m.group("status")),
                    "latency_s": float(m.group("latency_s")),
                })
                parsed += 1
            else:
                skipped += 1

    df = pd.DataFrame(rows)

    # normalizações
    if not df.empty:
        df["ts"] = pd.to_datetime(df["ts"], format="%Y-%m-%d %H:%M:%S,%f", errors="coerce")
        df["status"] = pd.to_numeric(df["status"], errors="coerce")
        df["latency_s"] = pd.to_numeric(df["latency_s"], errors="coerce")
        for col in ["method", "path"]:
            if col not in df.columns:
                df[col] = pd.NA

    st.caption(f"✔️ Linhas parseadas: {parsed} · ⛔ Ignoradas: {skipped}")
    return df

df = load_df(LOG_FILE)
if df.empty:
    st.warning("Sem registros por enquanto. Gere algumas requisições na API e atualize a página.")
    st.stop()

# ---------------- Filtros ----------------
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
    f = f[f["path"].str.contains(path_contains, case=False, na=False)]
f = f[(f["status"] >= status_min) & (f["status"] <= status_max)]

# ---------------- KPIs ----------------
c1, c2, c3, c4 = st.columns(4)
total = len(f)
avg_t = round(float(f["latency_s"].mean()), 4) if total else 0
p95_t = round(float(f["latency_s"].quantile(0.95)), 4) if total else 0
err_rate = round(float(((f["status"] >= 400).sum()) / total), 3) if total else 0

c1.metric("Total requests", total)
c2.metric("Média (s)", avg_t)
c3.metric("P95 (s)", p95_t)
c4.metric("Error rate", err_rate)

st.divider()

# ---------------- Gráfico: Requisições por endpoint ----------------
top_n = st.slider("Top endpoints por volume", 5, 20, 10)
endpoint_counts = (
    f.groupby("path", dropna=True)
     .size()
     .reset_index(name="count")
     .sort_values("count", ascending=False)
     .head(top_n)
)
chart1 = (
    alt.Chart(endpoint_counts)
       .mark_bar()
       .encode(
           x=alt.X("count:Q", title="Requisições"),
           y=alt.Y("path:N", sort="-x", title="Endpoint"),
           tooltip=["path", "count"]
       )
       .properties(
           height=30 * max(1, min(top_n, len(endpoint_counts))),
           title="Requisições por Endpoint"
       )
)
st.altair_chart(chart1, use_container_width=True)

# ---------------- Gráfico: Latência ao longo do tempo ----------------
if "ts" in f.columns and f["ts"].notna().any():
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
                   tooltip=["ts:T", "latency_mean_s:Q"]
               )
               .properties(height=300, title="Latência média por minuto")
        )
        st.altair_chart(chart2, use_container_width=True)

# ---------------- Gráfico: Proporção por classe HTTP ----------------
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
           .properties(height=300, title="Proporção de Respostas por Método e Classe HTTP")
    )
    st.altair_chart(chart3, use_container_width=True)

# ---------------- Tabela: últimas requisições ----------------
st.subheader("Últimas requisições")
cols_show = ["ts","method","path","status","latency_s"]
st.dataframe(
    f.sort_values("ts", ascending=False)[cols_show].head(50),
    use_container_width=True
)
