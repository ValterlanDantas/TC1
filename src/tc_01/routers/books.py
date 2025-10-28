from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple, Callable
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from tc_01.core.security import auth_required

router = APIRouter(prefix="/api/v1", tags=["books"])

# --------- helpers ---------
def _paginate(items: List[Dict[str, Any]], page: int, page_size: int) -> Tuple[int, List[Dict[str, Any]]]:
    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    return total, items[start:end]

def _parse_sort(sort: Optional[str]) -> List[Tuple[str, bool]]:
    """
    Converte 'rating_desc,price_asc' -> [('rating', False), ('price', True)]
    Campos permitidos: id, title, price, rating
    True = ascendente, False = descendente
    """
    if not sort:
        return []
    allowed = {"id", "title", "price", "rating"}
    result: List[Tuple[str, bool]] = []
    for part in sort.split(","):
        part = part.strip().lower()
        if part.endswith("_asc"):
            field = part[:-4]
            asc = True
        elif part.endswith("_desc"):
            field = part[:-5]
            asc = False
        else:
            field = part
            asc = True
        if field not in allowed:
            continue
        result.append((field, asc))
    return result

def _sort_items(items: List[Dict[str, Any]], sort_spec: List[Tuple[str, bool]]) -> List[Dict[str, Any]]:
    # aplica ordenação estável do Python do último critério para o primeiro
    out = list(items)
    for field, asc in reversed(sort_spec):
        out.sort(key=lambda x: (x.get(field) is None, x.get(field)), reverse=not asc)
    return out

# --------- endpoints ---------
@router.get("/books")
def list_books(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    sort: Optional[str] = Query(None, description="Ex.: rating_desc,price_asc"),
    user=Depends(auth_required),
):
    """
    Lista livros com paginação e ordenação.
    - Campos de ordenação: id, title, price, rating
    - Direções: _asc (padrão) ou _desc
      Ex.: ?sort=rating_desc,price_asc
    """
    data: List[Dict[str, Any]] = request.app.state.DATA
    items = data

    sort_spec = _parse_sort(sort)
    if sort_spec:
        items = _sort_items(items, sort_spec)

    total, page_items = _paginate(items, page, page_size)
    return {
        "user": user["sub"],
        "page": page,
        "page_size": page_size,
        "total": total,
        "items": page_items,
    }

@router.get("/books/{book_id}")
def get_book_by_id(
    book_id: int,
    request: Request,
    user=Depends(auth_required),
):
    """
    Retorna detalhes de um livro pelo ID.
    """
    data: List[Dict[str, Any]] = request.app.state.DATA
    for b in data:
        if b.get("id") == book_id:
            return {"user": user["sub"], "item": b}
    raise HTTPException(status_code=404, detail=f"Livro id={book_id} não encontrado")

@router.get("/books/search")
def search_books(
    request: Request,
    title: Optional[str] = Query(None, description="Busca contains, case-insensitive"),
    category: Optional[str] = Query(None, description="Busca contains, case-insensitive"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    sort: Optional[str] = Query(None, description="Ex.: rating_desc,price_asc"),
    user=Depends(auth_required),
):
    """
    Busca por título e/ou categoria (contains, case-insensitive) com paginação e ordenação.
    """
    data: List[Dict[str, Any]] = request.app.state.DATA

    def _match(b: Dict[str, Any]) -> bool:
        ok = True
        if title:
            ok = ok and (title.lower() in (b.get("title") or "").lower())
        if category:
            ok = ok and (category.lower() in (b.get("category") or "").lower())
        return ok

    filtered = [b for b in data if _match(b)]

    sort_spec = _parse_sort(sort)
    if sort_spec:
        filtered = _sort_items(filtered, sort_spec)

    total, page_items = _paginate(filtered, page, page_size)
    return {
        "user": user["sub"],
        "page": page,
        "page_size": page_size,
        "total": total,
        "items": page_items,
    }
