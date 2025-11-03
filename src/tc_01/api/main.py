# src/tc_01/api/main.py
import os
import jwt
from fastapi import FastAPI, HTTPException, Query
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin
import csv, re, statistics
from pathlib import Path
from datetime import datetime, timedelta
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import FastAPI
from tc_01.routers.auth import router as auth_router
from tc_01.routers.admin import router as admin_router
from tc_01.core.security import auth_required
from tc_01.routers.books import router as books_router
from tc_01.routers.categories import router as categories_router
from tc_01.routers.metrics import router as metrics_router



# Onde está o CSV?
# __file__ = .../src/tc_01/api/main.py
# parents[0]=api, [1]=tc_01, [2]=src, [3]=raiz do projeto
PKG_DIR = Path(__file__).resolve().parents[1]   # .../src/tc_01
DATA_DIR = PKG_DIR / "data"
CSV_FILE = DATA_DIR / "books_data.csv"

URL_BASE = "https://books.toscrape.com/"
RATING_MAP = {"One":1, "Two":2, "Three":3, "Four":4, "Five":5}

def parse_price(s: Optional[str]) -> Optional[float]:
    if not s:
        return None
    try:
        return float(s.replace("£","").strip())
    except Exception:
        return None

def parse_rating(s: Optional[str]) -> Optional[int]:
    if not s:
        return None
    return RATING_MAP.get(s.strip(), None)

def parse_availability(s: Optional[str]) -> Dict[str, Any]:
    """
    "In stock (19 available)" -> {"in_stock": True, "stock_qty": 19}
    """
    if not s:
        return {"in_stock": False, "stock_qty": 0}
    s_low = s.lower()
    in_stock = "in stock" in s_low
    qty_match = re.search(r"\((\d+)\s+available\)", s_low)
    qty = int(qty_match.group(1)) if qty_match else 0
    return {"in_stock": in_stock, "stock_qty": qty}

def absolutize_image(url_fragment: Optional[str]) -> Optional[str]:
    if not url_fragment:
        return None
    # alguns CSV vêm com "../../..", removemos os ../ e resolvemos com urljoin
    return urljoin(URL_BASE, url_fragment.replace("../", ""))

def load_books(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"CSV não encontrado em: {path}")
    items: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            try:
                book_id = int(row.get("id", "").strip()) if row.get("id") else None
            except Exception:
                book_id = None
            price = parse_price(row.get("price"))
            rating_num = parse_rating(row.get("rating"))
            avail = parse_availability(row.get("availability"))
            image_abs = absolutize_image(row.get("image"))
            items.append({
                "id": book_id,
                "title": (row.get("title") or "").strip(),
                "price": price,
                "rating": rating_num,
                "availability_raw": row.get("availability"),
                "in_stock": avail["in_stock"],
                "stock_qty": avail["stock_qty"],
                "category": (row.get("category") or "").strip(),
                "image": image_abs,
            })
    items.sort(key=lambda x: (x["id"] if x["id"] is not None else 1_000_000))
    return items

app = FastAPI(
    title="Books API",
    version="1.0.0",
    description="API pública do Tech Challenge.",
    openapi_tags=[
        # 1. SEGURANÇA / ADMIN
        {
            "name": "auth",
            "description": "Autenticação JWT (login e refresh).",
        },
        {
            "name": "admin",
            "description": "Rotas administrativas protegidas.",
        },
        # 2. Health
        {
            "name": "health"
        },
        # 3. ENDPOINTS CORE
        {
            "name": "core",
            "description": "Endpoints obrigatórios da API (livros, categorias, health).",
        },
        # 4. ENDPOINTS OPCIONAIS (INSIGHTS / MÉTRICAS)
        {
            "name": "insights",
            "description": "Endpoints opcionais de métricas, estatísticas e filtros.",
        },
    ],
    docs_url="/docs",
    redoc_url=None,
    swagger_ui_parameters={
        "docExpansion": "list",
        "persistAuthorization": True,
    },
)

from tc_01.core.logs import LogRequestsMiddleware
app.add_middleware(LogRequestsMiddleware)
from tc_01.routers.scraping import router as scraping_router

app.include_router(scraping_router)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(books_router)
app.include_router(categories_router)
app.include_router(metrics_router)


DATA = load_books(CSV_FILE)
app.state.DATA = DATA   

@app.get("/api/v1/health", tags=["health"])
def health(user=Depends(auth_required)):
    return {"status": "ok", "total_books": len(DATA), "user": user["sub"]}

@app.get("/api/v1/stats/overview", tags=["insights"])
def stats_overview(user=Depends(auth_required)):
    prices = [b["price"] for b in DATA if isinstance(b["price"], (int, float))]
    ratings = [b["rating"] for b in DATA if isinstance(b["rating"], int)]
    cats = [b["category"] for b in DATA if b.get("category")]

    overview = {
        "total_books": len(DATA),
        "categories_count": len(set(cats)),
        "in_stock_count": sum(1 for b in DATA if b["in_stock"]),
        "price_min": min(prices) if prices else None,
        "price_max": max(prices) if prices else None,
        "price_avg": round(statistics.mean(prices), 2) if prices else None,
        "rating_distribution": {str(k): 0 for k in range(1, 6)}
    }
    for r in ratings:
        overview["rating_distribution"][str(r)] += 1
    return {**overview, "user": user["sub"]}

@app.get("/api/v1/stats/categories", tags=["insights"])
def stats_categories(user=Depends(auth_required)):
    agg: Dict[str, Dict[str, Any]] = {}
    for b in DATA:
        cat = b.get("category") or "Uncategorized"
        if cat not in agg:
            agg[cat] = {
                "category": cat,
                "count": 0,
                "prices": [],
                "in_stock": 0,
                "avg_rating_acc": 0,
                "avg_rating_n": 0,
            }
        a = agg[cat]
        a["count"] += 1
        if isinstance(b["price"], (int, float)):
            a["prices"].append(b["price"])
        if b["in_stock"]:
            a["in_stock"] += 1
        if isinstance(b["rating"], int):
            a["avg_rating_acc"] += b["rating"]
            a["avg_rating_n"] += 1

    result = []
    for cat, a in sorted(agg.items(), key=lambda x: x[0].lower()):
        prices = a["prices"]
        avg_price = round(statistics.mean(prices), 2) if prices else None
        min_price = min(prices) if prices else None
        max_price = max(prices) if prices else None
        stock_rate = a["in_stock"] / a["count"] if a["count"] > 0 else 0
        avg_rating = (a["avg_rating_acc"] / a["avg_rating_n"]
                      if a["avg_rating_n"] > 0 else None)
        result.append({
            "category": a["category"],
            "books_count": a["count"],
            "in_stock_count": a["in_stock"],
            "in_stock_rate": round(stock_rate, 3),
            "price_avg": avg_price,
            "price_min": min_price,
            "price_max": max_price,
            "rating_avg": round(avg_rating, 3) if avg_rating is not None else None
        })
    return {"categories": result, "user": user["sub"]}

@app.get("/api/v1/books?sort=rating_desc,price_asc", tags=["insights"])
def top_rated(limit: int = Query(10, ge=1, le=100), user=Depends(auth_required)):
    ranked = sorted(
        [b for b in DATA if isinstance(b["rating"], int)],
        key=lambda x: (-x["rating"], x["price"] if x["price"] is not None else 1e9)
    )
    return {"total": len(ranked), "items": ranked[:limit]}
