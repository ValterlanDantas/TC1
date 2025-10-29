from fastapi import APIRouter
import pandas as pd
import os

router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])

LOG_PATH = "api_logs.log"

@router.get("/overview")
def get_metrics():
    """Retorna métricas gerais com base no arquivo de log."""
    if not os.path.exists(LOG_PATH):
        return {"error": f"Arquivo de log não encontrado em {LOG_PATH}"}

    try:
        # Lê o log com separador " - "
        df = pd.read_csv(
            LOG_PATH,
            sep=" - ",
            header=None,
            engine="python",
            names=["timestamp", "level", "message"],
            on_bad_lines="skip"
        )

        # Extrai método, endpoint, tempo e status
        df["method"] = df["message"].str.extract(r"(GET|POST|PUT|DELETE)")
        df["endpoint"] = df["message"].str.extract(r" (\/api\/v1\/[a-zA-Z0-9\/\-\_\?=]*) ")
        df["time"] = df["message"].str.extract(r"([0-9]+\.[0-9]+)s").astype(float, errors="ignore")
        df["status"] = df["message"].str.extract(r"status=([0-9]{3})")
        df["status"] = pd.to_numeric(df["status"], errors="coerce")

        # Métricas básicas
        total_requests = len(df)
        avg_time = round(df["time"].mean(), 3) if df["time"].notnull().any() else None
        top_endpoints = df["endpoint"].value_counts().head(5).to_dict()

        # Erros
        errors_4xx = df[df["status"].between(400, 499, inclusive="both")]
        errors_5xx = df[df["status"].between(500, 599, inclusive="both")]

        error_summary = {
            "4xx_count": len(errors_4xx),
            "5xx_count": len(errors_5xx),
            "error_rate": round((len(errors_4xx) + len(errors_5xx)) / total_requests, 3)
            if total_requests else 0
        }

        return {
            "total_requests": total_requests,
            "avg_response_time_s": avg_time,
            "top_endpoints": top_endpoints,
            "errors": error_summary
        }

    except Exception as e:
        return {"error": f"Falha ao processar métricas: {str(e)}"}
