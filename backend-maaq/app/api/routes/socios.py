from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.common import ok
from app.schemas.socios import AsociacionCreate, SocioAsociacionCreate, SocioCreate
from app.services import socios as service


router = APIRouter()


@router.get("")
def listar_socios(q: str | None = None, db: Session = Depends(get_db)):
    data = service.list_socios(db, q=q)
    return ok(data, {"total": len(data)})


@router.post("", status_code=201)
def crear_socio(payload: SocioCreate, db: Session = Depends(get_db)):
    return ok(service.create_socio(db, payload))


@router.get("/asociaciones")
def listar_asociaciones(db: Session = Depends(get_db)):
    return ok(service.list_asociaciones(db))


@router.post("/asociaciones", status_code=201)
def crear_asociacion(payload: AsociacionCreate, db: Session = Depends(get_db)):
    return ok(service.create_asociacion(db, payload))


@router.get("/vinculos")
def listar_vinculos(db: Session = Depends(get_db)):
    return ok(service.list_vinculos(db))


@router.post("/vinculos", status_code=201)
def vincular(payload: SocioAsociacionCreate, db: Session = Depends(get_db)):
    return ok(service.link_socio_asociacion(db, payload))
