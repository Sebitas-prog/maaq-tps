from collections.abc import Mapping
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Result
from sqlalchemy.orm import Session

from app.core.errors import AppError


Params = Mapping[str, Any] | None


def rows(result: Result) -> list[dict[str, Any]]:
    return [dict(row._mapping) for row in result]


def fetch_all(db: Session, sql: str, params: Params = None) -> list[dict[str, Any]]:
    return rows(db.execute(text(sql), params or {}))


def fetch_one(db: Session, sql: str, params: Params = None) -> dict[str, Any] | None:
    row = db.execute(text(sql), params or {}).mappings().first()
    return dict(row) if row else None


def scalar(db: Session, sql: str, params: Params = None) -> Any:
    return db.execute(text(sql), params or {}).scalar()


def execute(db: Session, sql: str, params: Params = None) -> None:
    db.execute(text(sql), params or {})


def require_one(db: Session, sql: str, params: Params = None, message: str = "Registro no encontrado") -> dict[str, Any]:
    item = fetch_one(db, sql, params)
    if item is None:
        raise AppError(message, status_code=404, code="NOT_FOUND")
    return item
