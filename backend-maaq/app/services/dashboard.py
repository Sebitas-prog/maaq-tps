from sqlalchemy.orm import Session

from app.services.db import fetch_all, scalar


def get_kpis(db: Session) -> dict:
    return {
        "clientes": scalar(db, "SELECT COUNT(1) FROM dbo.Cliente"),
        "empleados": scalar(db, "SELECT COUNT(1) FROM dbo.Empleado"),
        "socios": scalar(db, "SELECT COUNT(1) FROM dbo.Socio"),
        "asociaciones": scalar(db, "SELECT COUNT(1) FROM dbo.Asociacion"),
        "proyectos": scalar(db, "SELECT COUNT(1) FROM dbo.Proyecto"),
        "equipos": scalar(db, "SELECT COUNT(1) FROM dbo.Equipo"),
        "presupuesto_total": scalar(db, "SELECT COALESCE(SUM(Presupuesto), 0) FROM dbo.Proyecto"),
        "clientes_con_proyecto": scalar(db, "SELECT COUNT(DISTINCT IDcliente) FROM dbo.Cliente_Proyecto"),
    }


def get_project_status(db: Session) -> list[dict]:
    return fetch_all(
        db,
        """
        SELECT te.Estado, COUNT(1) AS total
        FROM dbo.Proyecto p
        JOIN dbo.Historial h ON p.IDhistorial = h.IDhistorial
        JOIN dbo.Tipo_Estado te ON h.IDtipoEstado = te.IDtipoEstado
        GROUP BY te.Estado
        ORDER BY total DESC
        """,
    )


def get_employee_departments(db: Session) -> list[dict]:
    return fetch_all(
        db,
        """
        SELECT d.Nombre AS departamento, COUNT(DISTINCT de.IDempleado) AS total
        FROM dbo.Departamento d
        LEFT JOIN dbo.Departamento_Empleado de ON d.IDdepartamento = de.IDdepartamento
        GROUP BY d.Nombre
        ORDER BY total DESC, d.Nombre
        """,
    )


def get_views(db: Session) -> dict[str, list[dict]]:
    return {
        "clientes": fetch_all(db, "SELECT TOP 200 * FROM dbo.Vista_Informacion_Clientes ORDER BY IDcliente DESC"),
        "socios_asociacion": fetch_all(db, "SELECT TOP 200 * FROM dbo.Vista_Socios_Asociacion ORDER BY IDsocio DESC"),
        "equipos_proyectos": fetch_all(db, "SELECT TOP 200 * FROM dbo.Vista_Equipos_Proyectos ORDER BY IDproyecto DESC"),
        "historial_proyectos": fetch_all(
            db,
            "SELECT TOP 200 * FROM dbo.Vista_Historial_Estado_Edificacion_Sector_Proyecto ORDER BY IDproyecto DESC",
        ),
        "empleados": fetch_all(db, "SELECT TOP 200 * FROM dbo.Vista_Informacion_Completa_Empleado ORDER BY IDempleado DESC"),
        "clientes_proyectos": fetch_all(db, "SELECT TOP 200 * FROM dbo.Vista_Clientes_Proyectos_Asignados ORDER BY IDcliente DESC"),
    }
