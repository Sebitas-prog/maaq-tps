from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.schemas.empleados import EquipoEmpleadoAssign
from app.schemas.equipos import EquipoCreate
from app.services.db import execute, fetch_all, fetch_one, require_one


def list_equipos(db: Session) -> list[dict]:
    return fetch_all(
        db,
        """
        SELECT
            eq.IDequipo,
            eq.Nombre,
            eq.Descripcion,
            (SELECT COUNT(1) FROM dbo.Equipo_Empleado ee WHERE ee.IDequipo = eq.IDequipo) AS TotalEmpleados,
            (SELECT COUNT(1) FROM dbo.Equipo_Proyecto ep WHERE ep.IDequipo = eq.IDequipo) AS TotalProyectos
        FROM dbo.Equipo eq
        ORDER BY eq.IDequipo DESC
        """,
    )


def create_equipo(db: Session, payload: EquipoCreate) -> dict:
    row = fetch_one(
        db,
        """
        INSERT INTO dbo.Equipo (Nombre, Descripcion)
        OUTPUT INSERTED.IDequipo AS IDequipo
        VALUES (:nombre, :descripcion)
        """,
        payload.model_dump(),
    )
    return require_one(db, "SELECT * FROM dbo.Equipo WHERE IDequipo = :id_equipo", {"id_equipo": row["IDequipo"]}, "Equipo no encontrado")


def assign_empleado(db: Session, id_equipo: int, payload: EquipoEmpleadoAssign) -> dict:
    require_one(db, "SELECT IDequipo FROM dbo.Equipo WHERE IDequipo = :id_equipo", {"id_equipo": id_equipo}, "Equipo no encontrado")
    require_one(db, "SELECT IDempleado FROM dbo.Empleado WHERE IDempleado = :id_empleado", {"id_empleado": payload.id_empleado}, "Empleado no encontrado")
    exists = fetch_one(
        db,
        """
        SELECT IDequipoEmpleado
        FROM dbo.Equipo_Empleado
        WHERE IDequipo = :id_equipo
          AND IDempleado = :id_empleado
          AND FechaCulminacion >= :fecha_asignacion
        """,
        {"id_equipo": id_equipo, **payload.model_dump()},
    )
    if exists:
        raise AppError("El empleado ya tiene una asignacion activa en ese equipo", 409, "ASIGNACION_DUPLICADA")
    row = fetch_one(
        db,
        """
        INSERT INTO dbo.Equipo_Empleado (IDempleado, IDequipo, FechaAsignacion, FechaCulminacion)
        OUTPUT INSERTED.IDequipoEmpleado AS IDequipoEmpleado
        VALUES (:id_empleado, :id_equipo, :fecha_asignacion, :fecha_culminacion)
        """,
        {"id_equipo": id_equipo, **payload.model_dump()},
    )
    return {"id_equipo_empleado": row["IDequipoEmpleado"], "id_equipo": id_equipo, **payload.model_dump()}


def remove_empleado(db: Session, id_equipo: int, id_empleado: int) -> dict:
    execute(
        db,
        """
        DELETE FROM dbo.Equipo_Empleado
        WHERE IDequipo = :id_equipo AND IDempleado = :id_empleado
        """,
        {"id_equipo": id_equipo, "id_empleado": id_empleado},
    )
    return {"id_equipo": id_equipo, "id_empleado": id_empleado, "eliminado": True}
