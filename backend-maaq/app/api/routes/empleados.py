from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.common import ok
from app.schemas.empleados import EmpleadoCreate, EmpleadoUpdate
from app.services import empleados as service


router = APIRouter()


@router.get("")
def listar(q: str | None = None, db: Session = Depends(get_db)):
    data = service.list_empleados(db, q=q)
    return ok(data, {"total": len(data)})


@router.get("/historial-cambios")
def historial(db: Session = Depends(get_db)):
    return ok(service.list_historial(db))


@router.get("/{id_empleado}")
def detalle(id_empleado: int, db: Session = Depends(get_db)):
    return ok(service.get_empleado(db, id_empleado))


@router.post("", status_code=201)
def crear(payload: EmpleadoCreate, db: Session = Depends(get_db)):
    return ok(service.create_empleado(db, payload))


@router.patch("/{id_empleado}")
def actualizar(id_empleado: int, payload: EmpleadoUpdate, db: Session = Depends(get_db)):
    return ok(service.update_empleado(db, id_empleado, payload))


@router.delete("/{id_empleado}")
def eliminar(id_empleado: int, db: Session = Depends(get_db)):
    return ok(service.delete_empleado(db, id_empleado))
