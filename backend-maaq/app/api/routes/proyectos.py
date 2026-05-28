from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.common import ok
from app.schemas.proyectos import ClienteProyectoCreate, EquipoProyectoCreate, ProyectoCreate, ProyectoEstadoUpdate
from app.services import proyectos as service


router = APIRouter()


@router.get("")
def listar(q: str | None = None, db: Session = Depends(get_db)):
    data = service.list_proyectos(db, q=q)
    return ok(data, {"total": len(data)})


@router.get("/auditoria")
def auditoria(db: Session = Depends(get_db)):
    return ok(service.list_auditoria(db))


@router.get("/{id_proyecto}")
def detalle(id_proyecto: int, db: Session = Depends(get_db)):
    return ok(service.get_proyecto(db, id_proyecto))


@router.post("", status_code=201)
def crear(payload: ProyectoCreate, db: Session = Depends(get_db)):
    return ok(service.create_proyecto(db, payload))


@router.put("/{id_proyecto}/estado")
def actualizar_estado(id_proyecto: int, payload: ProyectoEstadoUpdate, db: Session = Depends(get_db)):
    return ok(service.update_estado(db, id_proyecto, payload))


@router.post("/{id_proyecto}/clientes", status_code=201)
def asignar_cliente(id_proyecto: int, payload: ClienteProyectoCreate, db: Session = Depends(get_db)):
    return ok(service.asignar_cliente(db, id_proyecto, payload))


@router.post("/{id_proyecto}/equipos", status_code=201)
def asignar_equipo(id_proyecto: int, payload: EquipoProyectoCreate, db: Session = Depends(get_db)):
    return ok(service.asignar_equipo(db, id_proyecto, payload))
