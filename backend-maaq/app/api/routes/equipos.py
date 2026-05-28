from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.common import ok
from app.schemas.empleados import EquipoEmpleadoAssign
from app.schemas.equipos import EquipoCreate
from app.services import equipos as service


router = APIRouter()


@router.get("")
def listar(db: Session = Depends(get_db)):
    return ok(service.list_equipos(db))


@router.post("", status_code=201)
def crear(payload: EquipoCreate, db: Session = Depends(get_db)):
    return ok(service.create_equipo(db, payload))


@router.post("/{id_equipo}/empleados", status_code=201)
def asignar_empleado(id_equipo: int, payload: EquipoEmpleadoAssign, db: Session = Depends(get_db)):
    return ok(service.assign_empleado(db, id_equipo, payload))


@router.delete("/{id_equipo}/empleados/{id_empleado}")
def quitar_empleado(id_equipo: int, id_empleado: int, db: Session = Depends(get_db)):
    return ok(service.remove_empleado(db, id_equipo, id_empleado))
