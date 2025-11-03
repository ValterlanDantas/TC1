from __future__ import annotations
import os, re
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Query, HTTPException

router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])

# Arquivo de log (mesmo usado no middleware). Permite sobrescrever por ENV.
PROJECT_ROOT = Path(__file__).resolve().parents[2]  # .../src/tc_01
LOG_FILE = Path(os.getenv("LOG_FILE", PROJECT_ROOT.parent / "api_logs.log"))

# ---- helpers ----
_line_rx = re.compile(
    r"""^(?P<ts>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2},\d{3})\s+-\s+\w+\s+-\s+
        (?P<method>GET|POST|PUT|DELETE|PATCH|OPTIONS|HEAD)\s+
        (?P<path>\S+)\s+
        status=(?P<status>\d{3})\s+
        (?P<latency_s>\d+(?:\.\d+)?)s\s*$""",
    re.VERBOSE
)

def _parse_log(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            m = _line_rx.match(line.strip())
            if not m:
                continue
            rows.append({
                "timestamp": m.group("ts"),
                "method": m.group("method"),
                "path": m.group("path"),
                "status": int(m.group("status")),
                "latency_s": float(m.group("latency_s")),
            })
    return rows

# ---- agregado (o que você já tem) ----
@router.get("/overview")
def metrics_overview() -> Dict[str, Any]:
    entries = _parse_log(LOG_FILE)
    total = len(entries)
    avg_resp = round(sum(e["latency_s"] for e in entries) / total, 6) if total else 0.0

    # top endpoints
    top: Dict[str, int] = {}
    for e in entries:
        top[e["path"]] = top.get(e["path"], 0) + 1
    top_sorted = dict(sorted(top.items(), key=lambda kv: kv[1], reverse=True)[:20])

    # erros
    err_count = sum(1 for e in entries if e["status"] >= 400)
    err_rate = round(err_count / total, 6) if total else 0.0
    c4xx = sum(1 for e in entries if 400 <= e["status"] <= 499)
    c5xx = sum(1 for e in entries if 500 <= e["status"] <= 599)

    return {
        "total_requests": total,
        "avg_response_time_s": avg_resp,
        "top_endpoints": top_sorted,
        "errors": {"4xx_count": c4xx, "5xx_count": c5xx, "error_rate": err_rate},
    }

# ---- detalhado (novo) ----
@router.get("/entries")
def metrics_entries(
    limit: int = Query(1000, ge=1, le=10000),
    method: Optional[str] = Query(None, regex="^(GET|POST|PUT|DELETE|PATCH|OPTIONS|HEAD)$"),
    path_contains: Optional[str] = None,
    status_min: int = Query(100, ge=100, le=599),
    status_max: int = Query(599, ge=100, le=599),
) -> Dict[str, Any]:
    entries = _parse_log(LOG_FILE)

    # filtros
    if method:
        entries = [e for e in entries if e["method"] == method]
    if path_contains:
        s = path_contains.lower()
        entries = [e for e in entries if s in e["path"].lower()]
    entries = [e for e in entries if status_min <= e["status"] <= status_max]

    entries = entries[-limit:] if len(entries) > limit else entries
    return {"entries": entries, "count": len(entries)}

