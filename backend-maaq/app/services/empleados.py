from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.schemas.empleados import EmpleadoCreate, EmpleadoUpdate
from app.services.db import execute, fetch_all, fetch_one, require_one


def list_empleados(db: Session, q: str | None = None) -> list[dict]:
    params: dict[str, object] = {}
    where = ""
    if q:
        where = """
        WHERE e.Nombres LIKE :q
           OR e.ApellidoPaterno LIKE :q
           OR e.ApellidoMaterno LIKE :q
           OR e.NumeroDocumento LIKE :q
           OR e.Email LIKE :q
        """
        params["q"] = f"%{q}%"

    return fetch_all(
        db,
        f"""
        SELECT
            e.IDempleado,
            e.IDtipoDocumento,
            e.NumeroDocumento,
            e.ApellidoPaterno,
            e.ApellidoMaterno,
            e.Nombres,
            e.Email,
            e.Celular,
            d.Nombre AS Departamento,
            de.Area,
            contrato.IDproyecto,
            contrato.Obra AS ObraActual,
            te.TipoEmpleado,
            eq.Nombre AS Equipo,
            ee.FechaAsignacion,
            ee.FechaCulminacion
        FROM dbo.Empleado e
        LEFT JOIN dbo.Departamento_Empleado dept ON e.IDempleado = dept.IDempleado
        LEFT JOIN dbo.Departamento d ON dept.IDdepartamento = d.IDdepartamento
        LEFT JOIN dbo.Detalle_Empleado de ON e.IDempleado = de.IDempleado
        LEFT JOIN dbo.Tipo_Empleado te ON de.IDtipoEmpleado = te.IDtipoEmpleado
        LEFT JOIN dbo.Equipo_Empleado ee ON e.IDempleado = ee.IDempleado
        LEFT JOIN dbo.Equipo eq ON ee.IDequipo = eq.IDequipo
        OUTER APPLY (
            SELECT TOP 1 c.IDproyecto, c.Obra
            FROM dbo.RRHH_Contrato c
            WHERE c.IDempleado = e.IDempleado
              AND c.Estado <> 'liquidado'
            ORDER BY c.FechaInicio DESC, c.IDcontrato DESC
        ) contrato
        {where}
        ORDER BY e.IDempleado DESC
        """,
        params,
    )


def get_empleado(db: Session, id_empleado: int) -> dict:
    item = fetch_one(
        db,
        """
        SELECT *
        FROM dbo.Vista_Informacion_Completa_Empleado
        WHERE IDempleado = :id_empleado
        """,
        {"id_empleado": id_empleado},
    )
    if item is None:
        raise AppError("Empleado no encontrado", 404, "EMPLEADO_NOT_FOUND")
    return item


def _validate_duplicate(db: Session, numero_documento: str, exclude_id: int | None = None) -> None:
    params = {"numero_documento": numero_documento, "exclude_id": exclude_id or 0}
    exists = fetch_one(
        db,
        """
        SELECT IDempleado
        FROM dbo.Empleado
        WHERE NumeroDocumento = :numero_documento
          AND IDempleado <> :exclude_id
        """,
        params,
    )
    if exists:
        raise AppError("El documento del empleado ya esta registrado", 409, "DOCUMENTO_DUPLICADO", "numero_documento")


def create_empleado(db: Session, payload: EmpleadoCreate) -> dict:
    _validate_duplicate(db, payload.numero_documento)
    row = fetch_one(
        db,
        """
        INSERT INTO dbo.Empleado
            (IDtipoDocumento, NumeroDocumento, ApellidoPaterno, ApellidoMaterno, Nombres, Email, Celular)
        OUTPUT INSERTED.IDempleado AS IDempleado
        VALUES
            (:id_tipo_documento, :numero_documento, :apellido_paterno, :apellido_materno, :nombres, :email, :celular)
        """,
        payload.model_dump(),
    )
    id_empleado = int(row["IDempleado"])

    if payload.id_tipo_empleado:
        execute(
            db,
            """
            INSERT INTO dbo.Detalle_Empleado (IDempleado, IDtipoEmpleado, Area)
            VALUES (:id_empleado, :id_tipo_empleado, :area)
            """,
            {"id_empleado": id_empleado, "id_tipo_empleado": payload.id_tipo_empleado, "area": payload.area},
        )

    if payload.id_departamento:
        execute(
            db,
            """
            INSERT INTO dbo.Departamento_Empleado (IDdepartamento, IDempleado)
            VALUES (:id_departamento, :id_empleado)
            """,
            {"id_departamento": payload.id_departamento, "id_empleado": id_empleado},
        )

    if payload.id_equipo:
        if not payload.fecha_asignacion or not payload.fecha_culminacion:
            raise AppError("Las fechas son obligatorias para asignar equipo", 422, "FECHAS_REQUERIDAS")
        execute(
            db,
            """
            INSERT INTO dbo.Equipo_Empleado (IDempleado, IDequipo, FechaAsignacion, FechaCulminacion)
            VALUES (:id_empleado, :id_equipo, :fecha_asignacion, :fecha_culminacion)
            """,
            {
                "id_empleado": id_empleado,
                "id_equipo": payload.id_equipo,
                "fecha_asignacion": payload.fecha_asignacion,
                "fecha_culminacion": payload.fecha_culminacion,
            },
        )

    execute(
        db,
        """
        INSERT INTO dbo.Historial_Cambios_Empleado (IDempleado, Accion, Fecha, Usuario, EmailAnterior, EmailNuevo)
        VALUES (:id_empleado, 'INSERT', GETDATE(), SUSER_SNAME(), NULL, :email)
        """,
        {"id_empleado": id_empleado, "email": payload.email},
    )
    return get_empleado(db, id_empleado)


def update_empleado(db: Session, id_empleado: int, payload: EmpleadoUpdate) -> dict:
    current = require_one(
        db,
        "SELECT * FROM dbo.Empleado WHERE IDempleado = :id_empleado",
        {"id_empleado": id_empleado},
        "Empleado no encontrado",
    )
    updates = payload.model_dump(exclude_unset=True)
    usuario = updates.pop("usuario", "sistema")
    if "numero_documento" in updates and updates["numero_documento"]:
        _validate_duplicate(db, updates["numero_documento"], exclude_id=id_empleado)
    if not updates:
        return get_empleado(db, id_empleado)

    column_map = {
        "id_tipo_documento": "IDtipoDocumento",
        "numero_documento": "NumeroDocumento",
        "apellido_paterno": "ApellidoPaterno",
        "apellido_materno": "ApellidoMaterno",
        "nombres": "Nombres",
        "email": "Email",
        "celular": "Celular",
    }
    set_sql = ", ".join(f"{column_map[key]} = :{key}" for key in updates)
    execute(db, f"UPDATE dbo.Empleado SET {set_sql} WHERE IDempleado = :id_empleado", {**updates, "id_empleado": id_empleado})

    if "email" in updates and updates["email"] != current["Email"]:
        execute(
            db,
            """
            INSERT INTO dbo.Historial_Cambios_Empleado (IDempleado, Accion, Fecha, Usuario, EmailAnterior, EmailNuevo)
            VALUES (:id_empleado, 'UPDATE', GETDATE(), :usuario, :old_email, :new_email)
            """,
            {"id_empleado": id_empleado, "usuario": usuario, "old_email": current["Email"], "new_email": updates["email"]},
        )
    return get_empleado(db, id_empleado)


def delete_empleado(db: Session, id_empleado: int) -> dict:
    current = require_one(
        db,
        "SELECT Email FROM dbo.Empleado WHERE IDempleado = :id_empleado",
        {"id_empleado": id_empleado},
        "Empleado no encontrado",
    )
    execute(db, "DELETE FROM dbo.Equipo_Empleado WHERE IDempleado = :id_empleado", {"id_empleado": id_empleado})
    execute(db, "DELETE FROM dbo.Departamento_Empleado WHERE IDempleado = :id_empleado", {"id_empleado": id_empleado})
    execute(db, "DELETE FROM dbo.Detalle_Empleado WHERE IDempleado = :id_empleado", {"id_empleado": id_empleado})
    execute(db, "DELETE FROM dbo.Empleado WHERE IDempleado = :id_empleado", {"id_empleado": id_empleado})
    execute(
        db,
        """
        INSERT INTO dbo.Historial_Cambios_Empleado (IDempleado, Accion, Fecha, Usuario, EmailAnterior, EmailNuevo)
        VALUES (:id_empleado, 'DELETE', GETDATE(), SUSER_SNAME(), :old_email, NULL)
        """,
        {"id_empleado": id_empleado, "old_email": current["Email"]},
    )
    return {"id_empleado": id_empleado, "eliminado": True}


def list_historial(db: Session) -> list[dict]:
    return fetch_all(db, "SELECT TOP 200 * FROM dbo.Historial_Cambios_Empleado ORDER BY IDlog DESC")
