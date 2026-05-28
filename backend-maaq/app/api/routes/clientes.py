from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.clientes import (
    ClienteJuridicoCreate,
    ClienteNaturalCreate,
    ContactoJuridicoUpdate,
    ContactoNaturalUpdate,
    DireccionClienteUpdate,
)
from app.schemas.common import ok
from app.services import clientes as service


router = APIRouter()


@router.get("")
def listar(
    tipo: str | None = Query(default=None, pattern="^(natural|juridico)$"),
    q: str | None = None,
    db: Session = Depends(get_db),
):
    data = service.list_clientes(db, tipo=tipo, q=q)
    return ok(data, {"total": len(data)})


@router.get("/{id_cliente}")
def detalle(id_cliente: int, db: Session = Depends(get_db)):
    return ok(service.get_cliente(db, id_cliente))


@router.post("/natural", status_code=201)
def crear_natural(payload: ClienteNaturalCreate, db: Session = Depends(get_db)):
    return ok(service.create_natural(db, payload))


@router.post("/juridico", status_code=201)
def crear_juridico(payload: ClienteJuridicoCreate, db: Session = Depends(get_db)):
    return ok(service.create_juridico(db, payload))


@router.put("/{id_cliente}/direccion")
def actualizar_direccion(id_cliente: int, payload: DireccionClienteUpdate, db: Session = Depends(get_db)):
    return ok(service.update_direccion(db, id_cliente, payload))


@router.put("/{id_cliente}/contacto-natural")
def actualizar_contacto_natural(id_cliente: int, payload: ContactoNaturalUpdate, db: Session = Depends(get_db)):
    return ok(service.update_contacto_natural(db, id_cliente, payload))


@router.put("/{id_cliente}/contacto-juridico")
def actualizar_contacto_juridico(id_cliente: int, payload: ContactoJuridicoUpdate, db: Session = Depends(get_db)):
    return ok(service.update_contacto_juridico(db, id_cliente, payload))
