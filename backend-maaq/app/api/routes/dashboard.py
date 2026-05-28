from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.common import ok
from app.services import dashboard as service


router = APIRouter()


@router.get("/kpis")
def kpis(db: Session = Depends(get_db)):
    return ok(
        {
            "kpis": service.get_kpis(db),
            "proyectos_por_estado": service.get_project_status(db),
            "empleados_por_departamento": service.get_employee_departments(db),
        }
    )


@router.get("/vistas")
def vistas(db: Session = Depends(get_db)):
    return ok(service.get_views(db))


@router.get("/db-health")
def db_health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return ok({"database": "ok"})
