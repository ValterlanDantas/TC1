from __future__ import annotations
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, Request
from collections import Counter

from tc_01.core.security import auth_required

router = APIRouter(prefix="/api/v1")

@router.get("/categories", tags = ["core"])
def list_categories(request: Request, user=Depends(auth_required)):
    """
    Lista todas as categorias disponíveis com contagem de livros por categoria.
    """
    data: List[Dict[str, Any]] = request.app.state.DATA
    cats = [b.get("category") or "Uncategorized" for b in data]
    cnt = Counter(cats)
    items = [{"category": c, "count": cnt[c]} for c in sorted(cnt.keys(), key=str.lower)]
    return {"user": user["sub"], "total": len(items), "items": items}
