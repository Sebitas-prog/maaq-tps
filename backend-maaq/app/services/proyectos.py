from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.schemas.proyectos import ClienteProyectoCreate, EquipoProyectoCreate, ProyectoCreate, ProyectoEstadoUpdate
from app.services.db import execute, fetch_all, fetch_one, require_one


def list_proyectos(db: Session, q: str | None = None) -> list[dict]:
    params: dict[str, object] = {}
    where = ""
    if q:
        where = """
        WHERE p.Nombre LIKE :q
           OR p.JefeProyecto LIKE :q
           OR ts.Sector LIKE :q
           OR te.Estado LIKE :q
        """
        params["q"] = f"%{q}%"

    return fetch_all(
        db,
        f"""
        SELECT
            h.IDhistorial,
            h.Descripcion AS DescripcionHistorial,
            h.FechaActualizacion,
            te.Estado,
            p.IDproyecto,
            p.Nombre AS NombreProyecto,
            p.Objetivo,
            p.Presupuesto,
            p.JefeProyecto,
            tec.TipoEdificacion,
            ts.Sector
        FROM dbo.Historial h
        JOIN dbo.Tipo_Estado te ON h.IDtipoEstado = te.IDtipoEstado
        JOIN dbo.Proyecto p ON h.IDhistorial = p.IDhistorial
        JOIN dbo.Tipo_Edificacion tec ON p.IDtipoEdificacion = tec.IDtipoEdificacion
        JOIN dbo.Tipo_Sector ts ON p.IDsector = ts.IDsector
        {where}
        ORDER BY p.IDproyecto DESC
        """,
        params,
    )


def get_proyecto(db: Session, id_proyecto: int) -> dict:
    item = fetch_one(
        db,
        """
        SELECT *
        FROM dbo.Vista_Historial_Estado_Edificacion_Sector_Proyecto
        WHERE IDproyecto = :id_proyecto
        """,
        {"id_proyecto": id_proyecto},
    )
    if item is None:
        raise AppError("Proyecto no encontrado", 404, "PROYECTO_NOT_FOUND")
    return item


def create_proyecto(db: Session, payload: ProyectoCreate) -> dict:
    historial = fetch_one(
        db,
        """
        INSERT INTO dbo.Historial (Descripcion, FechaActualizacion, IDtipoEstado)
        OUTPUT INSERTED.IDhistorial AS IDhistorial
        VALUES (:historial_descripcion, :fecha_actualizacion, :id_tipo_estado)
        """,
        payload.model_dump(),
    )
    id_historial = int(historial["IDhistorial"])
    proyecto = fetch_one(
        db,
        """
        INSERT INTO dbo.Proyecto
            (IDsector, IDtipoEdificacion, Nombre, Objetivo, Presupuesto, JefeProyecto, IDhistorial)
        OUTPUT INSERTED.IDproyecto AS IDproyecto
        VALUES
            (:id_sector, :id_tipo_edificacion, :nombre, :objetivo, :presupuesto, :jefe_proyecto, :id_historial)
        """,
        {**payload.model_dump(), "id_historial": id_historial},
    )
    id_proyecto = int(proyecto["IDproyecto"])
    execute(
        db,
        """
        INSERT INTO dbo.Auditoria_Proyecto (IDproyecto, Accion, Fecha)
        VALUES (:id_proyecto, 'INSERT', GETDATE())
        """,
        {"id_proyecto": id_proyecto},
    )
    return get_proyecto(db, id_proyecto)


def update_estado(db: Session, id_proyecto: int, payload: ProyectoEstadoUpdate) -> dict:
    proyecto = require_one(
        db,
        "SELECT IDhistorial FROM dbo.Proyecto WHERE IDproyecto = :id_proyecto",
        {"id_proyecto": id_proyecto},
        "Proyecto no encontrado",
    )
    execute(
        db,
        """
        UPDATE dbo.Historial
        SET Descripcion = :descripcion,
            FechaActualizacion = :fecha_actualizacion,
            IDtipoEstado = :id_tipo_estado
        WHERE IDhistorial = :id_historial
        """,
        {**payload.model_dump(), "id_historial": proyecto["IDhistorial"]},
    )
    execute(
        db,
        "INSERT INTO dbo.Auditoria_Proyecto (IDproyecto, Accion, Fecha) VALUES (:id_proyecto, 'ESTADO', GETDATE())",
        {"id_proyecto": id_proyecto},
    )
    return get_proyecto(db, id_proyecto)


def asignar_cliente(db: Session, id_proyecto: int, payload: ClienteProyectoCreate) -> dict:
    require_one(db, "SELECT IDproyecto FROM dbo.Proyecto WHERE IDproyecto = :id_proyecto", {"id_proyecto": id_proyecto}, "Proyecto no encontrado")
    require_one(db, "SELECT IDcliente FROM dbo.Cliente WHERE IDcliente = :id_cliente", {"id_cliente": payload.id_cliente}, "Cliente no encontrado")
    row = fetch_one(
        db,
        """
        INSERT INTO dbo.Cliente_Proyecto
            (IDproyecto, IDcliente, FechaInicio, FechaFin, MontoBase, IDpais)
        OUTPUT INSERTED.IDclienteProyecto AS IDclienteProyecto
        VALUES
            (:id_proyecto, :id_cliente, :fecha_inicio, :fecha_fin, :monto_base, :id_pais)
        """,
        {**payload.model_dump(), "id_proyecto": id_proyecto},
    )
    execute(
        db,
        "INSERT INTO dbo.Auditoria_Proyecto (IDproyecto, Accion, Fecha) VALUES (:id_proyecto, 'CLIENTE', GETDATE())",
        {"id_proyecto": id_proyecto},
    )
    return {"id_cliente_proyecto": row["IDclienteProyecto"], "id_proyecto": id_proyecto, **payload.model_dump()}


def asignar_equipo(db: Session, id_proyecto: int, payload: EquipoProyectoCreate) -> dict:
    require_one(db, "SELECT IDproyecto FROM dbo.Proyecto WHERE IDproyecto = :id_proyecto", {"id_proyecto": id_proyecto}, "Proyecto no encontrado")
    require_one(db, "SELECT IDequipo FROM dbo.Equipo WHERE IDequipo = :id_equipo", {"id_equipo": payload.id_equipo}, "Equipo no encontrado")
    exists = fetch_one(
        db,
        """
        SELECT IDequipoProyecto
        FROM dbo.Equipo_Proyecto
        WHERE IDproyecto = :id_proyecto AND IDequipo = :id_equipo
        """,
        {"id_proyecto": id_proyecto, "id_equipo": payload.id_equipo},
    )
    if exists:
        raise AppError("El equipo ya esta asignado al proyecto", 409, "EQUIPO_DUPLICADO")
    row = fetch_one(
        db,
        """
        INSERT INTO dbo.Equipo_Proyecto (IDequipo, IDproyecto)
        OUTPUT INSERTED.IDequipoProyecto AS IDequipoProyecto
        VALUES (:id_equipo, :id_proyecto)
        """,
        {"id_equipo": payload.id_equipo, "id_proyecto": id_proyecto},
    )
    execute(
        db,
        "INSERT INTO dbo.Auditoria_Proyecto (IDproyecto, Accion, Fecha) VALUES (:id_proyecto, 'EQUIPO', GETDATE())",
        {"id_proyecto": id_proyecto},
    )
    return {"id_equipo_proyecto": row["IDequipoProyecto"], "id_proyecto": id_proyecto, "id_equipo": payload.id_equipo}


def list_auditoria(db: Session) -> list[dict]:
    return fetch_all(db, "SELECT TOP 200 * FROM dbo.Auditoria_Proyecto ORDER BY IDauditoria DESC")
