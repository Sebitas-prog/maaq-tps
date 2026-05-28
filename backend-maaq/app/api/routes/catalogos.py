from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.common import ok
from app.services import catalogos as service


router = APIRouter()


@router.get("")
def listar_todos(db: Session = Depends(get_db)):
    return ok(service.list_all_catalogs(db))


@router.get("/{nombre}")
def listar(nombre: str, db: Session = Depends(get_db)):
    return ok(service.list_catalog(db, nombre))


@router.post("/{nombre}", status_code=201)
def crear(nombre: str, payload: dict[str, Any], db: Session = Depends(get_db)):
    return ok(service.create_catalog_item(db, nombre, payload))
