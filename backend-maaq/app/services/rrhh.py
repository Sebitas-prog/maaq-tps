import json
import html as html_lib
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import LongTable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.schemas.rrhh import AsistenciaCreate, ContratacionCreate, DestajoCreate
from app.services.db import execute, fetch_all, fetch_one, require_one


EMPRESA = {
    "nombre": "Constructora MAAQ Arquitectos e Ingenieros S.A.C.",
    "ruc": "20600000000",
    "direccion": "Tingo Maria, Leoncio Prado, Huanuco",
    "representante": "Administrador MAAQ",
    "dni_representante": "00000000",
}

SALARIOS_MENSUALES_AREA = {
    "gerencia": Decimal("4500.00"),
    "administracion": Decimal("2300.00"),
    "recursos humanos": Decimal("2500.00"),
    "operaciones": Decimal("2800.00"),
    "logistica": Decimal("2200.00"),
    "ingenieria y planeamiento": Decimal("3500.00"),
    "ejecucion de obras": Decimal("3000.00"),
    "seguridad y salud": Decimal("2600.00"),
}

PREFIJOS_CONTRATO_AREA = {
    "administracion": "ADM",
    "gerencia": "GER",
    "recursos humanos": "RRH",
    "operaciones": "OPE",
    "logistica": "LOG",
    "ingenieria y planeamiento": "INP",
    "ejecucion de obras": "EOB",
    "seguridad y salud": "SSO",
    "sin area": "SNA",
}


def _audit(
    db: Session,
    modulo: str,
    accion: str,
    entidad: str,
    entidad_id: int | None,
    descripcion: str,
    payload: dict[str, Any] | None = None,
) -> None:
    execute(
        db,
        """
        INSERT INTO dbo.RRHH_Auditoria (Modulo, Accion, Entidad, EntidadID, Descripcion, Payload)
        VALUES (:modulo, :accion, :entidad, :entidad_id, :descripcion, :payload)
        """,
        {
            "modulo": modulo,
            "accion": accion,
            "entidad": entidad,
            "entidad_id": entidad_id,
            "descripcion": descripcion,
            "payload": json.dumps(payload or {}, ensure_ascii=True),
        },
    )


def _decimal(value: Any) -> Decimal:
    return Decimal(str(value or 0))


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _area_key(area: str | None) -> str:
    return (area or "").strip().lower()


def salario_mensual_area(area: str | None, salario_diario_base: Any = None) -> Decimal:
    if _area_key(area) in SALARIOS_MENSUALES_AREA:
        return SALARIOS_MENSUALES_AREA[_area_key(area)]
    salario_diario = _decimal(salario_diario_base)
    if salario_diario > 0:
        return _money(salario_diario * Decimal("30"))
    return Decimal("1800.00")


def salario_diario_area(area: str | None, salario_diario_base: Any = None) -> Decimal:
    return _money(salario_mensual_area(area, salario_diario_base) / Decimal("30"))


def _prefijo_contrato_area(area: str | None) -> str:
    key = _area_key(area) or "sin area"
    if key in PREFIJOS_CONTRATO_AREA:
        return PREFIJOS_CONTRATO_AREA[key]
    words = [word for word in key.replace("-", " ").split() if word]
    return ("".join(word[0] for word in words)[:3] or "GEN").upper()


def _siguiente_codigo_contrato(db: Session, area: str | None) -> str:
    prefix = _prefijo_contrato_area(area)
    row = fetch_one(
        db,
        """
        SELECT ISNULL(MAX(TRY_CONVERT(int, SUBSTRING(CodigoContrato, LEN(:prefix) + 2, 20))), 0) AS ultimo
        FROM dbo.RRHH_Contrato
        WHERE CodigoContrato LIKE :like_pattern
        """,
        {"prefix": prefix, "like_pattern": f"{prefix}-%"},
    )
    siguiente = int(row["ultimo"] or 0) + 1
    return f"{prefix}-{siguiente:03d}"


def _fmt_money(value: Any) -> str:
    return f"S/ {_money(_decimal(value)):,.2f}"


def _fmt_date(value: Any) -> str:
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")
    return str(value or "-")


def _fecha_larga(value: date) -> str:
    meses = [
        "enero",
        "febrero",
        "marzo",
        "abril",
        "mayo",
        "junio",
        "julio",
        "agosto",
        "septiembre",
        "octubre",
        "noviembre",
        "diciembre",
    ]
    return f"{value.day:02d} de {meses[value.month - 1]} de {value.year}"


def _txt(value: Any) -> str:
    if isinstance(value, (date, datetime)):
        value = _fmt_date(value)
    if value is None or value == "":
        value = "-"
    return html_lib.escape(str(value))


def _pdf_text(value: Any) -> str:
    return _txt(value).replace("\n", "<br/>")


def _pdf_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "normal": ParagraphStyle(
            "MaaqNormal",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            alignment=TA_JUSTIFY,
            spaceAfter=7,
        ),
        "small": ParagraphStyle(
            "MaaqSmall",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#4b5563"),
        ),
        "title": ParagraphStyle(
            "MaaqTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=17,
            leading=22,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#111827"),
            spaceAfter=16,
        ),
        "subtitle": ParagraphStyle(
            "MaaqSubtitle",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#111827"),
            spaceBefore=8,
            spaceAfter=4,
        ),
        "right": ParagraphStyle(
            "MaaqRight",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            alignment=TA_RIGHT,
        ),
    }


def _p(text: Any, style: ParagraphStyle) -> Paragraph:
    return Paragraph(_pdf_text(text), style)


def _pdf_document(story: list[Any], pagesize: tuple[float, float] = A4) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=pagesize,
        rightMargin=1.6 * cm,
        leftMargin=1.6 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )
    doc.build(story)
    return buffer.getvalue()


def _pdf_header(styles: dict[str, ParagraphStyle]) -> Table:
    table = Table(
        [
            [
                Paragraph(f"<b>{_pdf_text(EMPRESA['nombre'])}</b><br/>RUC {_pdf_text(EMPRESA['ruc'])}<br/>{_pdf_text(EMPRESA['direccion'])}", styles["small"]),
                Paragraph(f"<b>TPS MAAQ</b><br/>{_pdf_text(_fmt_date(date.today()))}", styles["right"]),
            ]
        ],
        colWidths=[12.4 * cm, 4.2 * cm],
    )
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (0, 0), (-1, -1), 1, colors.HexColor("#111827")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    return table


def _info_table(rows: list[tuple[str, Any]], styles: dict[str, ParagraphStyle]) -> Table:
    table = Table(
        [[Paragraph(f"<b>{_pdf_text(label)}</b>", styles["small"]), _p(value, styles["small"])] for label, value in rows],
        colWidths=[4.2 * cm, 12.4 * cm],
        hAlign="LEFT",
    )
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d1d5db")),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eef1df")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def _signature_table(left: str, right: str) -> Table:
    table = Table(
        [["", ""], [left, right]],
        colWidths=[7.4 * cm, 7.4 * cm],
        rowHeights=[1.6 * cm, 0.7 * cm],
        hAlign="CENTER",
    )
    table.setStyle(
        TableStyle(
            [
                ("LINEABOVE", (0, 1), (0, 1), 0.7, colors.black),
                ("LINEABOVE", (1, 1), (1, 1), 0.7, colors.black),
                ("ALIGN", (0, 1), (-1, 1), "CENTER"),
                ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 1), (-1, 1), 9),
            ]
        )
    )
    return table


def _json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def _validate_documento_unico(db: Session, numero_documento: str) -> None:
    exists = fetch_one(
        db,
        "SELECT IDempleado FROM dbo.Empleado WHERE NumeroDocumento = :numero_documento",
        {"numero_documento": numero_documento},
    )
    if exists:
        raise AppError("El DNI/documento ya esta registrado en empleados", 409, "DOCUMENTO_DUPLICADO", "numero_documento")


def _require_empleado(db: Session, id_empleado: int) -> dict:
    return require_one(
        db,
        """
        SELECT IDempleado, NumeroDocumento, ApellidoPaterno, ApellidoMaterno, Nombres, Email, Celular
        FROM dbo.Empleado
        WHERE IDempleado = :id_empleado
        """,
        {"id_empleado": id_empleado},
        "Empleado no encontrado",
    )


def _resolve_contrato_context(db: Session, id_empleado: int, obra: str, id_contrato: int | None = None) -> dict | None:
    if id_contrato:
        row = fetch_one(
            db,
            """
            SELECT c.IDcontrato, COALESCE(p.Nombre, c.Obra) AS Obra
            FROM dbo.RRHH_Contrato c
            LEFT JOIN dbo.Proyecto p ON c.IDproyecto = p.IDproyecto
            WHERE c.IDcontrato = :id_contrato
              AND c.IDempleado = :id_empleado
              AND c.Estado <> 'liquidado'
            """,
            {"id_contrato": id_contrato, "id_empleado": id_empleado},
        )
        if not row:
            raise AppError("Contrato activo no encontrado para el empleado", 404, "CONTRATO_NOT_FOUND")
        return row

    row = fetch_one(
        db,
        """
        SELECT TOP 1 c.IDcontrato, COALESCE(p.Nombre, c.Obra) AS Obra
        FROM dbo.RRHH_Contrato c
        LEFT JOIN dbo.Proyecto p ON c.IDproyecto = p.IDproyecto
        WHERE c.IDempleado = :id_empleado
          AND COALESCE(p.Nombre, c.Obra) = :obra
          AND c.Estado <> 'liquidado'
        ORDER BY c.FechaInicio DESC, c.IDcontrato DESC
        """,
        {"id_empleado": id_empleado, "obra": obra},
    )
    return row


def _resolve_contrato(db: Session, id_empleado: int, obra: str, id_contrato: int | None = None) -> int | None:
    row = _resolve_contrato_context(db, id_empleado, obra, id_contrato)
    return int(row["IDcontrato"]) if row else None


def _default_tipo_empleado(db: Session) -> int:
    row = fetch_one(
        db,
        """
        SELECT TOP 1 IDtipoEmpleado
        FROM dbo.Tipo_Empleado
        ORDER BY CASE WHEN TipoEmpleado = 'Administrativo' THEN 0 ELSE 1 END, IDtipoEmpleado ASC
        """,
    )
    if not row:
        row = fetch_one(
            db,
            """
            INSERT INTO dbo.Tipo_Empleado (TipoEmpleado)
            OUTPUT INSERTED.IDtipoEmpleado AS IDtipoEmpleado
            VALUES ('Administrativo')
            """,
        )
    return int(row["IDtipoEmpleado"])


def _contrato_supports_proyecto(db: Session) -> bool:
    row = fetch_one(db, "SELECT COL_LENGTH('dbo.RRHH_Contrato', 'IDproyecto') AS exists_column")
    return bool(row and row["exists_column"] is not None)


def _resolve_obra_contratacion(db: Session, id_proyecto: int | None, obra: str) -> tuple[int | None, str]:
    if id_proyecto:
        proyecto = require_one(
            db,
            "SELECT IDproyecto, Nombre FROM dbo.Proyecto WHERE IDproyecto = :id_proyecto",
            {"id_proyecto": id_proyecto},
            "Obra/proyecto no encontrado",
        )
        return int(proyecto["IDproyecto"]), str(proyecto["Nombre"]).strip()

    obra_nombre = obra.strip()
    proyecto = fetch_one(
        db,
        "SELECT TOP 1 IDproyecto, Nombre FROM dbo.Proyecto WHERE Nombre = :obra",
        {"obra": obra_nombre},
    )
    if proyecto:
        return int(proyecto["IDproyecto"]), str(proyecto["Nombre"]).strip()
    return None, obra_nombre


def list_obras(db: Session) -> list[dict]:
    has_id_proyecto = _contrato_supports_proyecto(db)
    join_condition = "c.IDproyecto = p.IDproyecto OR (c.IDproyecto IS NULL AND c.Obra = p.Nombre)" if has_id_proyecto else "c.Obra = p.Nombre"
    proyectos = fetch_all(
        db,
        f"""
        SELECT
            p.IDproyecto AS id,
            p.IDproyecto,
            p.Nombre AS NombreObra,
            p.Nombre AS label,
            'proyecto' AS Origen,
            COUNT(c.IDcontrato) AS TotalContratos
        FROM dbo.Proyecto p
        LEFT JOIN dbo.RRHH_Contrato c ON {join_condition}
        GROUP BY p.IDproyecto, p.Nombre
        """,
    )

    pendientes_where = "c.IDproyecto IS NULL AND" if has_id_proyecto else ""
    pendientes = fetch_all(
        db,
        f"""
        SELECT
            CAST(NULL AS int) AS id,
            CAST(NULL AS int) AS IDproyecto,
            c.Obra AS NombreObra,
            c.Obra AS label,
            'contrato' AS Origen,
            COUNT(*) AS TotalContratos
        FROM dbo.RRHH_Contrato c
        WHERE {pendientes_where} NOT EXISTS (
            SELECT 1
            FROM dbo.Proyecto p
            WHERE p.Nombre = c.Obra
        )
        GROUP BY c.Obra
        """,
    )

    return sorted([*proyectos, *pendientes], key=lambda item: str(item["NombreObra"]).lower())


def actualizar_area_empleado(db: Session, id_empleado: int, area: str, id_tipo_empleado: int | None = None) -> dict:
    _require_empleado(db, id_empleado)
    tipo = id_tipo_empleado or _default_tipo_empleado(db)
    current = fetch_one(
        db,
        """
        SELECT TOP 1 IDdetalleEmpleado
        FROM dbo.Detalle_Empleado
        WHERE IDempleado = :id_empleado
        ORDER BY IDdetalleEmpleado DESC
        """,
        {"id_empleado": id_empleado},
    )
    if current:
        execute(
            db,
            """
            UPDATE dbo.Detalle_Empleado
            SET Area = :area,
                IDtipoEmpleado = :id_tipo_empleado
            WHERE IDdetalleEmpleado = :id_detalle
            """,
            {"area": area, "id_tipo_empleado": tipo, "id_detalle": current["IDdetalleEmpleado"]},
        )
    else:
        execute(
            db,
            """
            INSERT INTO dbo.Detalle_Empleado (IDempleado, IDtipoEmpleado, Area)
            VALUES (:id_empleado, :id_tipo_empleado, :area)
            """,
            {"id_empleado": id_empleado, "id_tipo_empleado": tipo, "area": area},
        )
    _audit(
        db,
        "capital_humano",
        "ACTUALIZAR_AREA",
        "Detalle_Empleado",
        id_empleado,
        f"Area actualizada a {area}",
        {"area": area, "id_tipo_empleado": tipo},
    )
    return require_one(
        db,
        """
        SELECT
            e.IDempleado,
            e.NumeroDocumento,
            e.Nombres,
            e.ApellidoPaterno,
            e.ApellidoMaterno,
            e.Email,
            e.Celular,
            de.Area
        FROM dbo.Empleado e
        LEFT JOIN dbo.Detalle_Empleado de ON e.IDempleado = de.IDempleado
        WHERE e.IDempleado = :id_empleado
        """,
        {"id_empleado": id_empleado},
    )


def get_dashboard(db: Session) -> dict:
    kpis = fetch_one(
        db,
        """
        SELECT
            (SELECT COUNT(DISTINCT IDempleado) FROM dbo.RRHH_Contrato WHERE Estado <> 'liquidado') AS personal_activo,
            (SELECT COUNT(*) FROM dbo.RRHH_Contrato WHERE Estado <> 'liquidado' AND DATEDIFF(DAY, CAST(GETDATE() AS date), FechaFin) BETWEEN 0 AND 30) AS contratos_por_vencer,
            (SELECT COUNT(*) FROM dbo.RRHH_Contrato WHERE Estado <> 'liquidado' AND FechaFin < CAST(GETDATE() AS date)) AS contratos_vencidos,
            (SELECT COUNT(*) FROM dbo.RRHH_Asistencia WHERE Fecha = CAST(GETDATE() AS date)) AS asistencias_hoy,
            (SELECT ISNULL(SUM(TotalPlanilla), 0) FROM dbo.Vista_RRHH_Planilla_Resumen WHERE YEAR(Fecha) = YEAR(GETDATE()) AND MONTH(Fecha) = MONTH(GETDATE())) AS planilla_mes,
            (SELECT COUNT(*) FROM dbo.RRHH_Contrato WHERE YEAR(FechaCreacion) = YEAR(GETDATE()) AND MONTH(FechaCreacion) = MONTH(GETDATE())) AS altas_mes
        """,
    ) or {}
    semaforo = fetch_all(
        db,
        """
        SELECT Semaforo, COUNT(*) AS total
        FROM dbo.Vista_RRHH_Contratos_Alertas
        GROUP BY Semaforo
        ORDER BY CASE Semaforo WHEN 'rojo' THEN 1 WHEN 'amarillo' THEN 2 WHEN 'verde' THEN 3 ELSE 4 END
        """,
    )
    ultimos_contratos = fetch_all(
        db,
        """
        SELECT TOP 6 *
        FROM dbo.Vista_RRHH_Contratos_Alertas
        ORDER BY IDcontrato DESC
        """,
    )
    return {"kpis": kpis, "semaforo": semaforo, "ultimos_contratos": ultimos_contratos}


def contratar(db: Session, payload: ContratacionCreate) -> dict:
    _validate_documento_unico(db, payload.numero_documento)
    id_proyecto, obra_nombre = _resolve_obra_contratacion(db, payload.id_proyecto, payload.obra)
    empleado = fetch_one(
        db,
        """
        INSERT INTO dbo.Empleado
            (IDtipoDocumento, NumeroDocumento, ApellidoPaterno, ApellidoMaterno, Nombres, Email, Celular)
        OUTPUT INSERTED.IDempleado AS IDempleado
        VALUES
            (:id_tipo_documento, :numero_documento, :apellido_paterno, :apellido_materno, :nombres, :email, :celular)
        """,
        {
            "id_tipo_documento": payload.id_tipo_documento,
            "numero_documento": payload.numero_documento,
            "apellido_paterno": payload.apellido_paterno,
            "apellido_materno": payload.apellido_materno,
            "nombres": payload.nombres,
            "email": payload.email,
            "celular": payload.celular,
        },
    )
    id_empleado = int(empleado["IDempleado"])

    if payload.id_tipo_empleado or payload.area:
        id_tipo_empleado = payload.id_tipo_empleado or _default_tipo_empleado(db)
        execute(
            db,
            """
            INSERT INTO dbo.Detalle_Empleado (IDempleado, IDtipoEmpleado, Area)
            VALUES (:id_empleado, :id_tipo_empleado, :area)
            """,
            {"id_empleado": id_empleado, "id_tipo_empleado": id_tipo_empleado, "area": payload.area},
        )

    codigo = _siguiente_codigo_contrato(db, payload.area)
    salario_diario = salario_diario_area(payload.area, payload.salario_diario)
    has_id_proyecto = _contrato_supports_proyecto(db)
    proyecto_column = ", IDproyecto" if has_id_proyecto else ""
    proyecto_value = ", :id_proyecto" if has_id_proyecto else ""
    contrato = fetch_one(
        db,
        f"""
        INSERT INTO dbo.RRHH_Contrato
            (IDempleado, CodigoContrato{proyecto_column}, Obra, Cargo, FechaInicio, FechaFin, SalarioDiario)
        OUTPUT INSERTED.IDcontrato AS IDcontrato
        VALUES
            (:id_empleado, :codigo{proyecto_value}, :obra, :cargo, :fecha_inicio, :fecha_fin, :salario_diario)
        """,
        {
            "id_empleado": id_empleado,
            "codigo": codigo,
            "id_proyecto": id_proyecto,
            "obra": obra_nombre,
            "cargo": payload.cargo,
            "fecha_inicio": payload.fecha_inicio,
            "fecha_fin": payload.fecha_fin,
            "salario_diario": salario_diario,
        },
    )
    id_contrato = int(contrato["IDcontrato"])

    execute(
        db,
        """
        INSERT INTO dbo.Historial_Cambios_Empleado (IDempleado, Accion, Fecha, Usuario, EmailAnterior, EmailNuevo)
        VALUES (:id_empleado, 'INSERT', GETDATE(), SUSER_SNAME(), NULL, :email)
        """,
        {"id_empleado": id_empleado, "email": payload.email},
    )
    _audit(
        db,
        "contratacion",
        "ALTA",
        "RRHH_Contrato",
        id_contrato,
        f"Alta de {payload.nombres} {payload.apellido_paterno} con contrato {codigo}",
        {
            **payload.model_dump(mode="json"),
            "id_proyecto_aplicado": id_proyecto,
            "obra_aplicada": obra_nombre,
            "salario_mensual_simulado": str(salario_mensual_area(payload.area, payload.salario_diario)),
            "salario_diario_aplicado": str(salario_diario),
        },
    )
    return require_one(
        db,
        "SELECT * FROM dbo.Vista_RRHH_Contratos_Alertas WHERE IDcontrato = :id_contrato",
        {"id_contrato": id_contrato},
    )


def list_altas(db: Session, limit: int = 100) -> list[dict]:
    return fetch_all(
        db,
        """
        SELECT TOP (:limit) *
        FROM dbo.Vista_RRHH_Contratos_Alertas
        ORDER BY IDcontrato DESC
        """,
        {"limit": limit},
    )


def list_contratos(db: Session, q: str | None = None) -> list[dict]:
    where = ""
    params: dict[str, Any] = {}
    if q:
        where = """
        WHERE Empleado LIKE :q
           OR NumeroDocumento LIKE :q
           OR Obra LIKE :q
           OR Cargo LIKE :q
           OR CodigoContrato LIKE :q
           OR Area LIKE :q
        """
        params["q"] = f"%{q}%"
    return fetch_all(
        db,
        f"""
        SELECT *
        FROM dbo.Vista_RRHH_Contratos_Alertas
        {where}
        ORDER BY
            Area ASC,
            CASE Semaforo WHEN 'rojo' THEN 1 WHEN 'amarillo' THEN 2 WHEN 'verde' THEN 3 ELSE 4 END,
            FechaFin ASC
        """,
        params,
    )


def alertas_contratos(db: Session, dias: int = 30) -> list[dict]:
    return fetch_all(
        db,
        """
        SELECT *
        FROM dbo.Vista_RRHH_Contratos_Alertas
        WHERE Estado <> 'liquidado'
          AND DiasRestantes <= :dias
        ORDER BY Area ASC, DiasRestantes ASC
        """,
        {"dias": dias},
    )


def renovar_contrato(db: Session, id_contrato: int, fecha_fin: date) -> dict:
    contrato = require_one(
        db,
        "SELECT * FROM dbo.RRHH_Contrato WHERE IDcontrato = :id_contrato",
        {"id_contrato": id_contrato},
        "Contrato no encontrado",
    )
    if contrato["Estado"] == "liquidado":
        raise AppError("No se puede renovar un contrato liquidado", 409, "CONTRATO_LIQUIDADO")
    if fecha_fin < contrato["FechaInicio"]:
        raise AppError("La nueva fecha fin no puede ser anterior al inicio", 422, "FECHA_INVALIDA", "fecha_fin")

    execute(
        db,
        """
        UPDATE dbo.RRHH_Contrato
        SET FechaFin = :fecha_fin, Estado = 'renovado'
        WHERE IDcontrato = :id_contrato
        """,
        {"id_contrato": id_contrato, "fecha_fin": fecha_fin},
    )
    _audit(
        db,
        "contratos",
        "RENOVAR",
        "RRHH_Contrato",
        id_contrato,
        f"Contrato renovado hasta {fecha_fin.isoformat()}",
        {"fecha_fin_anterior": str(contrato["FechaFin"]), "fecha_fin_nueva": fecha_fin.isoformat()},
    )
    return require_one(
        db,
        "SELECT * FROM dbo.Vista_RRHH_Contratos_Alertas WHERE IDcontrato = :id_contrato",
        {"id_contrato": id_contrato},
    )


def liquidar_contrato(db: Session, id_contrato: int) -> dict:
    contrato = require_one(
        db,
        "SELECT * FROM dbo.RRHH_Contrato WHERE IDcontrato = :id_contrato",
        {"id_contrato": id_contrato},
        "Contrato no encontrado",
    )
    if contrato["Estado"] == "liquidado":
        return {
            "contrato": require_one(db, "SELECT * FROM dbo.Vista_RRHH_Contratos_Alertas WHERE IDcontrato = :id_contrato", {"id_contrato": id_contrato}),
            "calculo": {"total": contrato["TotalLiquidacion"] or Decimal("0.00")},
        }

    fecha_inicio = contrato["FechaInicio"]
    fecha_liquidacion = min(date.today(), contrato["FechaFin"])
    dias = max(0, (fecha_liquidacion - fecha_inicio).days + 1)
    anios = Decimal(dias) / Decimal("365")
    salario = _decimal(contrato["SalarioDiario"])
    cts = _money(salario * Decimal("15") * anios)
    vacaciones = _money(salario * Decimal("15") * anios)
    gratificacion = _money(salario * Decimal("30") * anios)
    total = _money(cts + vacaciones + gratificacion)

    execute(
        db,
        """
        UPDATE dbo.RRHH_Contrato
        SET Estado = 'liquidado',
            FechaLiquidacion = :fecha_liquidacion,
            TotalLiquidacion = :total
        WHERE IDcontrato = :id_contrato
        """,
        {"id_contrato": id_contrato, "fecha_liquidacion": fecha_liquidacion, "total": total},
    )
    calculo = {
        "dias_calculados": dias,
        "cts": cts,
        "vacaciones": vacaciones,
        "gratificacion": gratificacion,
        "total": total,
    }
    _audit(
        db,
        "contratos",
        "LIQUIDAR",
        "RRHH_Contrato",
        id_contrato,
        f"Contrato liquidado por S/ {total}",
        {key: str(value) for key, value in calculo.items()},
    )
    return {
        "contrato": require_one(db, "SELECT * FROM dbo.Vista_RRHH_Contratos_Alertas WHERE IDcontrato = :id_contrato", {"id_contrato": id_contrato}),
        "calculo": calculo,
    }


def registrar_asistencia(db: Session, payload: AsistenciaCreate) -> dict:
    _require_empleado(db, payload.id_empleado)
    contrato = _resolve_contrato_context(db, payload.id_empleado, payload.obra, payload.id_contrato)
    id_contrato = int(contrato["IDcontrato"]) if contrato else None
    obra = str(contrato["Obra"]) if contrato else payload.obra
    current = fetch_one(
        db,
        """
        SELECT IDasistencia
        FROM dbo.RRHH_Asistencia
        WHERE IDempleado = :id_empleado
          AND Fecha = :fecha
          AND Obra = :obra
        """,
        {"id_empleado": payload.id_empleado, "fecha": payload.fecha, "obra": obra},
    )
    params = {
        "id_empleado": payload.id_empleado,
        "id_contrato": id_contrato,
        "fecha": payload.fecha,
        "obra": obra,
        "estado": payload.estado,
        "horas": payload.horas,
        "extras": payload.extras,
        "observacion": payload.observacion,
    }
    if current:
        id_asistencia = int(current["IDasistencia"])
        execute(
            db,
            """
            UPDATE dbo.RRHH_Asistencia
            SET IDcontrato = :id_contrato,
                Estado = :estado,
                Horas = :horas,
                Extras = :extras,
                Observacion = :observacion
            WHERE IDasistencia = :id_asistencia
            """,
            {**params, "id_asistencia": id_asistencia},
        )
        accion = "ACTUALIZAR_ASISTENCIA"
    else:
        row = fetch_one(
            db,
            """
            INSERT INTO dbo.RRHH_Asistencia
                (IDempleado, IDcontrato, Fecha, Obra, Estado, Horas, Extras, Observacion)
            OUTPUT INSERTED.IDasistencia AS IDasistencia
            VALUES
                (:id_empleado, :id_contrato, :fecha, :obra, :estado, :horas, :extras, :observacion)
            """,
            params,
        )
        id_asistencia = int(row["IDasistencia"])
        accion = "REGISTRAR_ASISTENCIA"

    _audit(
        db,
        "asistencia",
        accion,
        "RRHH_Asistencia",
        id_asistencia,
        f"Asistencia {payload.estado} registrada para empleado {payload.id_empleado}",
        payload.model_dump(mode="json"),
    )
    return require_one(
        db,
        """
        SELECT a.*, e.NumeroDocumento, CONCAT(e.Nombres, ' ', e.ApellidoPaterno) AS Empleado
        FROM dbo.RRHH_Asistencia a
        JOIN dbo.Empleado e ON a.IDempleado = e.IDempleado
        WHERE a.IDasistencia = :id_asistencia
        """,
        {"id_asistencia": id_asistencia},
    )


def registrar_destajo(db: Session, payload: DestajoCreate) -> dict:
    _require_empleado(db, payload.id_empleado)
    contrato = _resolve_contrato_context(db, payload.id_empleado, payload.obra, payload.id_contrato)
    id_contrato = int(contrato["IDcontrato"]) if contrato else None
    obra = str(contrato["Obra"]) if contrato else payload.obra
    total = _money(payload.metrado * payload.tarifa)
    row = fetch_one(
        db,
        """
        INSERT INTO dbo.RRHH_Destajo
            (IDempleado, IDcontrato, Fecha, Obra, Partida, Metrado, Tarifa, Total, Observacion)
        OUTPUT INSERTED.IDdestajo AS IDdestajo
        VALUES
            (:id_empleado, :id_contrato, :fecha, :obra, :partida, :metrado, :tarifa, :total, :observacion)
        """,
        {
            "id_empleado": payload.id_empleado,
            "id_contrato": id_contrato,
            "fecha": payload.fecha,
            "obra": obra,
            "partida": payload.partida,
            "metrado": payload.metrado,
            "tarifa": payload.tarifa,
            "total": total,
            "observacion": payload.observacion,
        },
    )
    id_destajo = int(row["IDdestajo"])
    _audit(
        db,
        "destajo",
        "REGISTRAR_DESTAJO",
        "RRHH_Destajo",
        id_destajo,
        f"Destajo {payload.partida} registrado por S/ {total}",
        {**payload.model_dump(mode="json"), "total": str(total)},
    )
    return require_one(
        db,
        """
        SELECT d.*, e.NumeroDocumento, CONCAT(e.Nombres, ' ', e.ApellidoPaterno) AS Empleado
        FROM dbo.RRHH_Destajo d
        JOIN dbo.Empleado e ON d.IDempleado = e.IDempleado
        WHERE d.IDdestajo = :id_destajo
        """,
        {"id_destajo": id_destajo},
    )


def list_planilla(db: Session, desde: date | None = None, hasta: date | None = None) -> list[dict]:
    params: dict[str, Any] = {"desde": desde, "hasta": hasta}
    return fetch_all(
        db,
        """
        SELECT *
        FROM dbo.Vista_RRHH_Planilla_Resumen
        WHERE (:desde IS NULL OR Fecha >= :desde)
          AND (:hasta IS NULL OR Fecha <= :hasta)
        ORDER BY Area ASC, Fecha DESC, Empleado ASC
        """,
        params,
    )


def reportes_globales(db: Session) -> dict:
    personal_activo = fetch_all(
        db,
        """
        SELECT *
        FROM dbo.Vista_RRHH_Contratos_Alertas
        WHERE Estado <> 'liquidado'
        ORDER BY Area ASC, Empleado ASC
        """,
    )
    planilla_total = fetch_all(
        db,
        """
        SELECT
            IDempleado,
            NumeroDocumento,
            Empleado,
            Area,
            SUM(Jornal) AS Jornal,
            SUM(Extras) AS Extras,
            SUM(TotalDestajo) AS TotalDestajo,
            SUM(TotalPlanilla) AS TotalPlanilla
        FROM dbo.Vista_RRHH_Planilla_Resumen
        GROUP BY IDempleado, NumeroDocumento, Empleado, Area
        ORDER BY Area ASC, TotalPlanilla DESC
        """,
    )
    contratos_30 = alertas_contratos(db, 30)
    return {
        "personal_activo": personal_activo,
        "planilla_total": planilla_total,
        "contratos_por_vencer": contratos_30,
    }


REPORTE_TITULOS = {
    "contratos": "Contratos generales",
    "contratos_activos": "Contratos activos",
    "contratos_vencidos": "Contratos vencidos",
    "contratos_por_vencer": "Contratos por vencer",
    "empleados_area": "Empleados por area",
    "ingresantes_rango": "Ingresantes por rango",
    "planilla_rango": "Planilla por rango",
    "asistencia_mes_pago": "Asistencia por mes de pago",
}


def _columnas_reporte(tipo: str, include_area: bool = True) -> list[tuple[str, str]]:
    if tipo == "asistencia_mes_pago":
        columns = [
            ("CodigoContrato", "Contrato"),
            ("Empleado", "Empleado"),
            ("NumeroDocumento", "Documento"),
            ("Area", "Area"),
            ("Obra", "Obra"),
            ("PeriodoPago", "Periodo"),
            ("DiasPeriodo", "Dias"),
            ("DiasRegistrados", "Reg."),
            ("Presentes", "Presentes"),
            ("Faltas", "Faltas"),
            ("Tardanzas", "Tardanzas"),
            ("Descansos", "Descansos"),
            ("Permisos", "Permisos"),
            ("Horas", "Horas"),
            ("Extras", "Extras"),
            ("FechasFalta", "Fechas falta"),
        ]
        return columns if include_area else [column for column in columns if column[0] != "Area"]
    if tipo == "planilla_rango":
        columns = [
            ("Fecha", "Fecha"),
            ("Empleado", "Empleado"),
            ("NumeroDocumento", "Documento"),
            ("Area", "Area"),
            ("Obra", "Obra"),
            ("HorasLaboradas", "Horas"),
            ("Jornal", "Jornal"),
            ("Extras", "Extras"),
            ("TotalDestajo", "Destajo"),
            ("TotalPlanilla", "Total"),
        ]
        return columns if include_area else [column for column in columns if column[0] != "Area"]
    columns = [
        ("CodigoContrato", "Contrato"),
        ("Empleado", "Empleado"),
        ("NumeroDocumento", "Documento"),
        ("Area", "Area"),
        ("Obra", "Obra"),
        ("Cargo", "Cargo"),
        ("FechaInicio", "Ingreso"),
        ("FechaFin", "Fin"),
        ("DiasRestantes", "Dias"),
        ("Estado", "Estado"),
        ("Semaforo", "Semaforo"),
    ]
    return columns if include_area else [column for column in columns if column[0] != "Area"]


def _valor_reporte(value: Any) -> str:
    if value is None or value == "":
        return "-"
    if isinstance(value, (date, datetime)):
        return _fmt_date(value)
    if isinstance(value, Decimal):
        return f"{_money(value):,.2f}"
    if isinstance(value, float):
        return f"{value:,.2f}".rstrip("0").rstrip(".")
    return str(value)


def _reporte_filtros(
    tipo: str,
    area: str | None,
    estado: str | None,
    desde: date | None,
    hasta: date | None,
    q: str | None,
    dias: int,
    total: int,
    mes_pago: str | None = None,
) -> list[tuple[str, Any]]:
    return [
        ("Tipo", REPORTE_TITULOS.get(tipo, tipo)),
        ("Mes de pago", mes_pago or "-"),
        ("Area", area or "Todas"),
        ("Estado", estado or "Todos"),
        ("Desde", desde or "-"),
        ("Hasta", hasta or "-"),
        ("Busqueda", q or "-"),
        ("Dias alerta", dias),
        ("Registros", total),
        ("Generado", date.today()),
    ]


def _row_area(row: dict) -> str:
    value = str(row.get("Area") or "Sin area").strip()
    return value or "Sin area"


def _group_reporte_rows(rows: list[dict]) -> list[tuple[str, list[dict]]]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        groups[_row_area(row)].append(row)
    return sorted(groups.items(), key=lambda item: item[0].lower())


def _reporte_resumen(rows: list[dict], tipo: str) -> dict[str, Any]:
    areas = sorted({_row_area(row) for row in rows}, key=str.lower)
    estados: dict[str, int] = defaultdict(int)
    semaforo: dict[str, int] = defaultdict(int)
    by_area: dict[str, dict[str, Any]] = {}
    total_planilla = Decimal("0")
    total_destajo = Decimal("0")
    total_horas = Decimal("0")
    total_faltas = 0
    total_tardanzas = 0
    total_sin_registro = 0

    for area, group in _group_reporte_rows(rows):
        if tipo == "asistencia_mes_pago":
            area_horas = sum((_decimal(row.get("Horas")) for row in group), Decimal("0"))
            area_faltas = sum(int(row.get("Faltas") or 0) for row in group)
            area_tardanzas = sum(int(row.get("Tardanzas") or 0) for row in group)
            area_sin_registro = sum(int(row.get("DiasSinRegistro") or 0) for row in group)
            by_area[area] = {
                "registros": len(group),
                "horas": area_horas,
                "faltas": area_faltas,
                "tardanzas": area_tardanzas,
                "sin_registro": area_sin_registro,
            }
            total_horas += area_horas
            total_faltas += area_faltas
            total_tardanzas += area_tardanzas
            total_sin_registro += area_sin_registro
        elif tipo == "planilla_rango":
            area_planilla = sum((_decimal(row.get("TotalPlanilla")) for row in group), Decimal("0"))
            area_destajo = sum((_decimal(row.get("TotalDestajo")) for row in group), Decimal("0"))
            area_horas = sum((_decimal(row.get("HorasLaboradas")) for row in group), Decimal("0"))
            by_area[area] = {
                "registros": len(group),
                "planilla": area_planilla,
                "destajo": area_destajo,
                "horas": area_horas,
            }
            total_planilla += area_planilla
            total_destajo += area_destajo
            total_horas += area_horas
        else:
            area_semaforo: dict[str, int] = defaultdict(int)
            area_estado: dict[str, int] = defaultdict(int)
            for row in group:
                area_semaforo[str(row.get("Semaforo") or "sin dato").lower()] += 1
                area_estado[str(row.get("Estado") or "sin dato").lower()] += 1
            by_area[area] = {
                "registros": len(group),
                "rojo": area_semaforo.get("rojo", 0),
                "amarillo": area_semaforo.get("amarillo", 0),
                "verde": area_semaforo.get("verde", 0),
                "activos": area_estado.get("activo", 0),
            }

        for row in group:
            estados[str(row.get("Estado") or "sin dato").lower()] += 1
            semaforo[str(row.get("Semaforo") or "sin dato").lower()] += 1

    if tipo == "asistencia_mes_pago":
        kpis = [
            ("Contratos", len(rows)),
            ("Areas", len(areas)),
            ("Faltas", total_faltas),
            ("Tardanzas", total_tardanzas),
            ("Horas", _valor_reporte(total_horas)),
            ("Sin registro", total_sin_registro),
        ]
    elif tipo == "planilla_rango":
        kpis = [
            ("Registros", len(rows)),
            ("Areas", len(areas)),
            ("Horas", _valor_reporte(total_horas)),
            ("Planilla total", f"S/ {_money(total_planilla):,.2f}"),
        ]
    else:
        kpis = [
            ("Registros", len(rows)),
            ("Areas", len(areas)),
            ("Rojo", semaforo.get("rojo", 0)),
            ("Amarillo", semaforo.get("amarillo", 0)),
            ("Verde", semaforo.get("verde", 0)),
            ("Activos", estados.get("activo", 0)),
        ]

    return {
        "kpis": kpis,
        "areas": areas,
        "by_area": by_area,
        "estados": dict(estados),
        "semaforo": dict(semaforo),
        "total_planilla": total_planilla,
        "total_destajo": total_destajo,
        "total_horas": total_horas,
        "total_faltas": total_faltas,
        "total_tardanzas": total_tardanzas,
        "total_sin_registro": total_sin_registro,
    }


def _excel_col(index: int) -> str:
    letters = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def _xml_text(value: Any) -> str:
    text = _valor_reporte(value)
    text = "".join(char for char in text if char in "\t\n\r" or ord(char) >= 32)
    return html_lib.escape(text, quote=False)


def _xlsx_cell(row: int, col: int, value: Any, style: int = 0) -> str:
    ref = f"{_excel_col(col)}{row}"
    style_attr = f' s="{style}"' if style else ""
    if isinstance(value, (int, float, Decimal)) and not isinstance(value, bool):
        numeric = format(value, "f") if isinstance(value, Decimal) else str(value)
        return f'<c r="{ref}"{style_attr}><v>{numeric}</v></c>'
    return f'<c r="{ref}"{style_attr} t="inlineStr"><is><t xml:space="preserve">{_xml_text(value)}</t></is></c>'


def _xlsx_row(row_number: int, values: list[Any], style: int = 0) -> str:
    cells = "".join(_xlsx_cell(row_number, index + 1, value, style) for index, value in enumerate(values))
    return f'<row r="{row_number}">{cells}</row>'


def _xlsx_worksheet(sheet_rows: list[str], col_count: int) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheetViews>
    <sheetView workbookViewId="0"/>
  </sheetViews>
  <cols>
    <col min="1" max="1" width="22" customWidth="1"/>
    <col min="2" max="{max(2, col_count)}" width="20" customWidth="1"/>
  </cols>
  <sheetData>
    {''.join(sheet_rows)}
  </sheetData>
</worksheet>"""


def _xlsx_reporte(titulo: str, filtros: list[tuple[str, Any]], columnas: list[tuple[str, str]], rows: list[dict], tipo: str) -> bytes:
    resumen = _reporte_resumen(rows, tipo)
    summary_rows: list[str] = []
    current = 1
    summary_rows.append(_xlsx_row(current, [f"TPS MAAQ - {titulo}"], 1))
    current += 1
    summary_rows.append(_xlsx_row(current, ["Modelo ejecutivo de reporte RRHH"], 0))
    current += 2

    summary_rows.append(_xlsx_row(current, ["Resumen general"], 2))
    current += 1
    for label, value in resumen["kpis"]:
        summary_rows.append(_xlsx_row(current, [label, value], 5))
        current += 1
    current += 1

    summary_rows.append(_xlsx_row(current, ["Filtros aplicados"], 2))
    current += 1
    for label, value in filtros:
        summary_rows.append(_xlsx_row(current, [label, value]))
        current += 1
    current += 1

    summary_rows.append(_xlsx_row(current, ["Resumen por area"], 2))
    current += 1
    if tipo == "asistencia_mes_pago":
        summary_rows.append(_xlsx_row(current, ["Area", "Contratos", "Faltas", "Tardanzas", "Horas", "Sin registro"], 3))
        current += 1
        for area, data in resumen["by_area"].items():
            summary_rows.append(_xlsx_row(current, [area, data["registros"], data["faltas"], data["tardanzas"], data["horas"], data["sin_registro"]]))
            current += 1
    elif tipo == "planilla_rango":
        summary_rows.append(_xlsx_row(current, ["Area", "Registros", "Horas", "Destajo", "Planilla"], 3))
        current += 1
        for area, data in resumen["by_area"].items():
            summary_rows.append(_xlsx_row(current, [area, data["registros"], data["horas"], data["destajo"], data["planilla"]]))
            current += 1
    else:
        summary_rows.append(_xlsx_row(current, ["Area", "Registros", "Activos", "Rojo", "Amarillo", "Verde"], 3))
        current += 1
        for area, data in resumen["by_area"].items():
            summary_rows.append(_xlsx_row(current, [area, data["registros"], data["activos"], data["rojo"], data["amarillo"], data["verde"]]))
            current += 1

    detail_rows: list[str] = []
    current = 1
    detail_rows.append(_xlsx_row(current, [f"Detalle - {titulo}"], 1))
    current += 2
    if not rows:
        detail_rows.append(_xlsx_row(current, ["No hay registros para los filtros seleccionados"]))
    for area, group in _group_reporte_rows(rows):
        detail_rows.append(_xlsx_row(current, [area.upper(), f"{len(group)} registros"], 4))
        current += 1
        detail_rows.append(_xlsx_row(current, [label for _, label in columnas], 3))
        current += 1
        for item in group:
            detail_rows.append(_xlsx_row(current, [item.get(key) for key, _ in columnas]))
            current += 1
        current += 1

    summary_sheet = _xlsx_worksheet(summary_rows, 6)
    detail_sheet = _xlsx_worksheet(detail_rows, len(columnas))
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>""",
        )
        archive.writestr(
            "_rels/.rels",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>""",
        )
        archive.writestr(
            "xl/workbook.xml",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="Resumen" sheetId="1" r:id="rId1"/>
    <sheet name="Detalle" sheetId="2" r:id="rId2"/>
  </sheets>
</workbook>""",
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>""",
        )
        archive.writestr(
            "xl/styles.xml",
"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="3"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Calibri"/></font></fonts>
  <fills count="6"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF111827"/><bgColor indexed="64"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFEFF4EA"/><bgColor indexed="64"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FF0F766E"/><bgColor indexed="64"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFFFF7ED"/><bgColor indexed="64"/></patternFill></fill></fills>
  <borders count="2"><border><left/><right/><top/><bottom/><diagonal/></border><border><left style="thin"><color rgb="FFD8DED2"/></left><right style="thin"><color rgb="FFD8DED2"/></right><top style="thin"><color rgb="FFD8DED2"/></top><bottom style="thin"><color rgb="FFD8DED2"/></bottom><diagonal/></border></borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="6"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="2" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1"/><xf numFmtId="0" fontId="1" fillId="3" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1"/><xf numFmtId="0" fontId="1" fillId="5" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1"/><xf numFmtId="0" fontId="2" fillId="4" borderId="0" xfId="0" applyFont="1" applyFill="1"/><xf numFmtId="0" fontId="0" fillId="5" borderId="1" xfId="0" applyFill="1" applyBorder="1"/></cellXfs>
</styleSheet>""",
        )
        archive.writestr("xl/worksheets/sheet1.xml", summary_sheet)
        archive.writestr("xl/worksheets/sheet2.xml", detail_sheet)
    return buffer.getvalue()


def _pdf_summary_table(resumen: dict[str, Any], styles: dict[str, ParagraphStyle]) -> Table:
    cells = [Paragraph(f"<b>{_pdf_text(label)}</b><br/>{_pdf_text(value)}", styles["small"]) for label, value in resumen["kpis"]]
    rows = [cells[index : index + 3] for index in range(0, len(cells), 3)]
    while rows and len(rows[-1]) < 3:
        rows[-1].append(Paragraph("", styles["small"]))
    table = Table(rows, colWidths=[8.7 * cm, 8.7 * cm, 8.7 * cm], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f2f6ef")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#d8ded2")),
                ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#d8ded2")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return table


def _pdf_area_summary_table(resumen: dict[str, Any], tipo: str, styles: dict[str, ParagraphStyle]) -> Table:
    if tipo == "asistencia_mes_pago":
        headers = ["Area", "Contratos", "Faltas", "Tardanzas", "Horas", "Sin registro"]
        data = [
            [area, values["registros"], values["faltas"], values["tardanzas"], _valor_reporte(values["horas"]), values["sin_registro"]]
            for area, values in resumen["by_area"].items()
        ]
    elif tipo == "planilla_rango":
        headers = ["Area", "Registros", "Horas", "Destajo", "Planilla"]
        data = [
            [area, values["registros"], _valor_reporte(values["horas"]), _valor_reporte(values["destajo"]), _valor_reporte(values["planilla"])]
            for area, values in resumen["by_area"].items()
        ]
    else:
        headers = ["Area", "Registros", "Activos", "Rojo", "Amarillo", "Verde"]
        data = [
            [area, values["registros"], values["activos"], values["rojo"], values["amarillo"], values["verde"]]
            for area, values in resumen["by_area"].items()
        ]
    table_data = [[Paragraph(f"<b>{_pdf_text(item)}</b>", styles["small"]) for item in headers]]
    table_data.extend([[Paragraph(_pdf_text(_valor_reporte(item)), styles["small"]) for item in row] for row in data])
    table = Table(table_data, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef2ea")),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#d8ded2")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def _pdf_col_widths(tipo: str) -> list[float]:
    if tipo == "asistencia_mes_pago":
        return [1.8 * cm, 3.6 * cm, 2.0 * cm, 2.7 * cm, 2.8 * cm, 1.1 * cm, 1.1 * cm, 1.3 * cm, 1.1 * cm, 1.2 * cm, 1.2 * cm, 1.2 * cm, 1.3 * cm, 1.3 * cm, 3.0 * cm]
    if tipo == "planilla_rango":
        return [1.8 * cm, 4.2 * cm, 2.0 * cm, 3.5 * cm, 1.4 * cm, 1.7 * cm, 1.7 * cm, 1.8 * cm, 1.8 * cm]
    return [2.0 * cm, 4.0 * cm, 2.0 * cm, 3.1 * cm, 3.2 * cm, 1.8 * cm, 1.8 * cm, 1.1 * cm, 1.5 * cm, 1.6 * cm]


def _pdf_area_header(area: str, count: int, styles: dict[str, ParagraphStyle]) -> Table:
    table = Table([[Paragraph(f"<b>{_pdf_text(area.upper())}</b>", styles["small"]), Paragraph(f"{count} registros", styles["small"])]], colWidths=[21.5 * cm, 4.5 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#0f766e")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def _pdf_reporte(titulo: str, filtros: list[tuple[str, Any]], columnas: list[tuple[str, str]], rows: list[dict], tipo: str) -> bytes:
    styles = _pdf_styles()
    resumen = _reporte_resumen(rows, tipo)
    story: list[Any] = [
        _pdf_header(styles),
        Spacer(1, 0.35 * cm),
        Paragraph(f"TPS MAAQ - {titulo}", styles["title"]),
        _p("Modelo ejecutivo de reporte RRHH con resumen, filtros aplicados y detalle agrupado por area.", styles["small"]),
        Spacer(1, 0.25 * cm),
        _pdf_summary_table(resumen, styles),
        Spacer(1, 0.35 * cm),
        Paragraph("Filtros aplicados", styles["subtitle"]),
        _info_table([(label, _valor_reporte(value)) for label, value in filtros], styles),
        Spacer(1, 0.35 * cm),
        Paragraph("Resumen por area", styles["subtitle"]),
        _pdf_area_summary_table(resumen, tipo, styles),
        Spacer(1, 0.45 * cm),
        Paragraph("Detalle del reporte", styles["subtitle"]),
    ]
    if not rows:
        story.append(_p("No hay registros para los filtros seleccionados.", styles["normal"]))
    for area, group in _group_reporte_rows(rows):
        table_data: list[list[Any]] = [[Paragraph(f"<b>{_pdf_text(label)}</b>", styles["small"]) for _, label in columnas]]
        for item in group:
            table_data.append([Paragraph(_pdf_text(_valor_reporte(item.get(key))), styles["small"]) for key, _ in columnas])
        table = LongTable(table_data, colWidths=_pdf_col_widths(tipo), repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef2ea")),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#d8ded2")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 3),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.extend([Spacer(1, 0.18 * cm), _pdf_area_header(area, len(group), styles), table])
    return _pdf_document(story, pagesize=landscape(A4))


def _parse_mes_pago(mes_pago: str | None, desde: date | None = None) -> date:
    if mes_pago:
        try:
            year_text, month_text = mes_pago.split("-", 1)
            year = int(year_text)
            month = int(month_text)
            return date(year, month, 1)
        except ValueError as exc:
            raise AppError("El mes de pago debe tener formato AAAA-MM", 422, "MES_PAGO_INVALIDO", "mes_pago") from exc
    if desde:
        return date(desde.year, desde.month, 1)
    today_value = date.today()
    return date(today_value.year, today_value.month, 1)


def reporte_asistencia_mes_pago(
    db: Session,
    mes_pago: str | None = None,
    area: str | None = None,
    estado: str | None = None,
    q: str | None = None,
    limit: int = 1000,
    desde: date | None = None,
) -> list[dict]:
    mes_base = _parse_mes_pago(mes_pago, desde)
    params: dict[str, Any] = {"mes_base": mes_base, "limit": limit}
    where = ["b.FechaInicio <= b.PeriodoFin", "b.FechaFin >= b.PeriodoInicio"]
    if area:
        where.append("b.Area = :area")
        params["area"] = area
    if estado:
        where.append("b.Estado = :estado")
        params["estado"] = estado
    if q:
        where.append(
            """
            (
                b.Empleado LIKE :q
                OR b.NumeroDocumento LIKE :q
                OR b.CodigoContrato LIKE :q
                OR b.Obra LIKE :q
                OR b.Cargo LIKE :q
            )
            """
        )
        params["q"] = f"%{q}%"

    return fetch_all(
        db,
        f"""
        WITH contratos AS (
            SELECT
                c.IDcontrato,
                c.CodigoContrato,
                c.IDempleado,
                c.NumeroDocumento,
                c.Empleado,
                c.Area,
                c.Obra,
                c.Cargo,
                c.FechaInicio,
                c.FechaFin,
                c.Estado,
                periodo.PeriodoInicio,
                periodo.PeriodoFin
            FROM dbo.Vista_RRHH_Contratos_Alertas c
            CROSS APPLY (
                SELECT
                    DATEFROMPARTS(
                        YEAR(:mes_base),
                        MONTH(:mes_base),
                        CASE
                            WHEN DAY(c.FechaInicio) > DAY(EOMONTH(:mes_base)) THEN DAY(EOMONTH(:mes_base))
                            ELSE DAY(c.FechaInicio)
                        END
                    ) AS PeriodoInicio,
                    DATEFROMPARTS(
                        YEAR(DATEADD(MONTH, 1, :mes_base)),
                        MONTH(DATEADD(MONTH, 1, :mes_base)),
                        CASE
                            WHEN DAY(c.FechaInicio) > DAY(EOMONTH(DATEADD(MONTH, 1, :mes_base))) THEN DAY(EOMONTH(DATEADD(MONTH, 1, :mes_base)))
                            ELSE DAY(c.FechaInicio)
                        END
                    ) AS PeriodoFin
            ) periodo
            WHERE c.Estado <> 'liquidado'
        ),
        base AS (
            SELECT *
            FROM contratos b
            WHERE {" AND ".join(where)}
        )
        SELECT TOP (:limit)
            b.IDcontrato,
            b.CodigoContrato,
            b.IDempleado,
            b.NumeroDocumento,
            b.Empleado,
            b.Area,
            b.Obra,
            b.Cargo,
            b.FechaInicio,
            b.FechaFin,
            b.Estado,
            b.PeriodoInicio,
            b.PeriodoFin,
            CONCAT(CONVERT(varchar(10), b.PeriodoInicio, 23), ' al ', CONVERT(varchar(10), b.PeriodoFin, 23)) AS PeriodoPago,
            DATEDIFF(DAY, b.PeriodoInicio, b.PeriodoFin) + 1 AS DiasPeriodo,
            COUNT(a.IDasistencia) AS DiasRegistrados,
            (DATEDIFF(DAY, b.PeriodoInicio, b.PeriodoFin) + 1) - COUNT(a.IDasistencia) AS DiasSinRegistro,
            SUM(CASE WHEN a.Estado = 'presente' THEN 1 ELSE 0 END) AS Presentes,
            SUM(CASE WHEN a.Estado = 'inasistencia' THEN 1 ELSE 0 END) AS Faltas,
            SUM(CASE WHEN a.Estado = 'tardanza' THEN 1 ELSE 0 END) AS Tardanzas,
            SUM(CASE WHEN a.Estado = 'descanso' THEN 1 ELSE 0 END) AS Descansos,
            SUM(CASE WHEN a.Estado = 'permiso' THEN 1 ELSE 0 END) AS Permisos,
            ISNULL(SUM(a.Horas), 0) AS Horas,
            ISNULL(SUM(a.Extras), 0) AS Extras,
            ISNULL(STRING_AGG(CASE WHEN a.Estado = 'inasistencia' THEN CONVERT(varchar(10), a.Fecha, 23) END, ', '), '-') AS FechasFalta
        FROM base b
        LEFT JOIN dbo.RRHH_Asistencia a
            ON a.IDcontrato = b.IDcontrato
           AND a.Fecha BETWEEN b.PeriodoInicio AND b.PeriodoFin
        GROUP BY
            b.IDcontrato,
            b.CodigoContrato,
            b.IDempleado,
            b.NumeroDocumento,
            b.Empleado,
            b.Area,
            b.Obra,
            b.Cargo,
            b.FechaInicio,
            b.FechaFin,
            b.Estado,
            b.PeriodoInicio,
            b.PeriodoFin
        ORDER BY b.Area ASC, Faltas DESC, b.Empleado ASC
        """,
        params,
    )


def reporte_personalizado(
    db: Session,
    tipo: str = "contratos",
    area: str | None = None,
    estado: str | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    q: str | None = None,
    dias: int = 30,
    limit: int = 1000,
    mes_pago: str | None = None,
) -> list[dict]:
    tipo = (tipo or "contratos").strip().lower()
    params: dict[str, Any] = {"limit": limit, "dias": dias}

    if tipo == "asistencia_mes_pago":
        return reporte_asistencia_mes_pago(db, mes_pago=mes_pago, area=area, estado=estado, q=q, limit=limit, desde=desde)

    if tipo == "planilla_rango":
        where = ["1 = 1"]
        if area:
            where.append("Area = :area")
            params["area"] = area
        if desde:
            where.append("Fecha >= :desde")
            params["desde"] = desde
        if hasta:
            where.append("Fecha <= :hasta")
            params["hasta"] = hasta
        if q:
            where.append(
                """
                (
                    Empleado LIKE :q
                    OR NumeroDocumento LIKE :q
                    OR Obra LIKE :q
                )
                """
            )
            params["q"] = f"%{q}%"
        return fetch_all(
            db,
            f"""
            SELECT TOP (:limit)
                Fecha,
                IDempleado,
                NumeroDocumento,
                Empleado,
                Area,
                Obra,
                HorasLaboradas,
                Jornal,
                Extras,
                TotalDestajo,
                TotalPlanilla
            FROM dbo.Vista_RRHH_Planilla_Resumen
            WHERE {" AND ".join(where)}
            ORDER BY Fecha DESC, Area ASC, Empleado ASC
            """,
            params,
        )

    where = ["1 = 1"]
    if tipo == "contratos_activos":
        where.append("Estado = 'activo'")
    elif tipo == "contratos_vencidos":
        where.append("FechaFin < CAST(GETDATE() AS date)")
    elif tipo == "contratos_por_vencer":
        where.append("DiasRestantes BETWEEN 0 AND :dias")
    elif tipo == "ingresantes_rango":
        where.append("1 = 1")
    elif tipo == "empleados_area":
        where.append("1 = 1")
    elif tipo != "contratos":
        raise AppError("Tipo de reporte no soportado", 422, "REPORTE_TIPO_INVALIDO", "tipo")

    if area:
        where.append("Area = :area")
        params["area"] = area
    if estado and tipo not in {"contratos_activos"}:
        where.append("Estado = :estado")
        params["estado"] = estado

    fecha_columna = "FechaInicio" if tipo in {"ingresantes_rango", "empleados_area"} else "FechaFin"
    if desde:
        where.append(f"{fecha_columna} >= :desde")
        params["desde"] = desde
    if hasta:
        where.append(f"{fecha_columna} <= :hasta")
        params["hasta"] = hasta

    if q:
        where.append(
            """
            (
                Empleado LIKE :q
                OR NumeroDocumento LIKE :q
                OR CodigoContrato LIKE :q
                OR Obra LIKE :q
                OR Cargo LIKE :q
            )
            """
        )
        params["q"] = f"%{q}%"

    return fetch_all(
        db,
        f"""
        SELECT TOP (:limit)
            IDcontrato,
            CodigoContrato,
            IDempleado,
            NumeroDocumento,
            Empleado,
            Area,
            Obra,
            Cargo,
            FechaInicio,
            FechaFin,
            SalarioDiario,
            Estado,
            FechaLiquidacion,
            TotalLiquidacion,
            DiasRestantes,
            Semaforo
        FROM dbo.Vista_RRHH_Contratos_Alertas
        WHERE {" AND ".join(where)}
        ORDER BY
            Area ASC,
            CASE Semaforo WHEN 'rojo' THEN 1 WHEN 'amarillo' THEN 2 WHEN 'verde' THEN 3 ELSE 4 END,
            FechaFin ASC,
            Empleado ASC
        """,
        params,
    )


def exportar_reporte_personalizado(
    db: Session,
    formato: str,
    tipo: str = "contratos",
    area: str | None = None,
    estado: str | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    q: str | None = None,
    dias: int = 30,
    limit: int = 1000,
    mes_pago: str | None = None,
) -> dict[str, Any]:
    tipo = (tipo or "contratos").strip().lower()
    formato = (formato or "excel").strip().lower()
    rows = reporte_personalizado(db, tipo, area, estado, desde, hasta, q, dias, limit, mes_pago)
    columnas = _columnas_reporte(tipo, include_area=False)
    titulo = REPORTE_TITULOS.get(tipo, "Reporte personalizado")
    filtros = _reporte_filtros(tipo, area, estado, desde, hasta, q, dias, len(rows), mes_pago)
    slug = tipo.replace("_", "-")

    if formato == "excel":
        filename = f"reporte-{slug}-maaq.xlsx"
        content = _xlsx_reporte(titulo, filtros, columnas, rows, tipo)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif formato == "pdf":
        filename = f"reporte-{slug}-maaq.pdf"
        content = _pdf_reporte(titulo, filtros, columnas, rows, tipo)
        media_type = "application/pdf"
    else:
        raise AppError("Formato de reporte no soportado", 422, "REPORTE_FORMATO_INVALIDO", "formato")

    _audit(
        db,
        "reportes",
        f"EXPORTAR_{formato.upper()}",
        "RRHH_Reporte",
        None,
        f"Reporte {titulo} exportado en {formato}",
        {
            "tipo": tipo,
            "area": area,
            "estado": estado,
            "desde": str(desde) if desde else None,
            "hasta": str(hasta) if hasta else None,
            "q": q,
            "dias": dias,
            "limit": limit,
            "mes_pago": mes_pago,
            "total": len(rows),
            "filename": filename,
        },
    )
    return {"filename": filename, "content": content, "media_type": media_type}


def buscar_empleados(db: Session, q: str) -> list[dict]:
    return fetch_all(
        db,
        """
        SELECT TOP 50
            e.IDempleado,
            e.NumeroDocumento,
            e.Nombres,
            e.ApellidoPaterno,
            e.ApellidoMaterno,
            e.Email,
            e.Celular,
            ISNULL(NULLIF(det.Area, ''), 'Sin area') AS Area,
            c.IDcontrato,
            c.IDproyecto,
            c.CodigoContrato,
            COALESCE(p.Nombre, c.Obra) AS Obra,
            c.Cargo,
            c.Estado AS EstadoContrato,
            c.FechaFin
        FROM dbo.Empleado e
        LEFT JOIN dbo.RRHH_Contrato c ON e.IDempleado = c.IDempleado
        LEFT JOIN dbo.Proyecto p ON c.IDproyecto = p.IDproyecto
        OUTER APPLY (
            SELECT TOP 1 Area
            FROM dbo.Detalle_Empleado de
            WHERE de.IDempleado = e.IDempleado
            ORDER BY de.IDdetalleEmpleado DESC
        ) det
        WHERE e.NumeroDocumento LIKE :q
           OR e.Nombres LIKE :q
           OR e.ApellidoPaterno LIKE :q
           OR e.ApellidoMaterno LIKE :q
           OR det.Area LIKE :q
        ORDER BY Area ASC, e.IDempleado DESC, c.IDcontrato DESC
        """,
        {"q": f"%{q}%"},
    )


def _require_contrato_documento(db: Session, id_contrato: int) -> dict:
    return require_one(
        db,
        """
        SELECT
            c.IDcontrato,
            c.CodigoContrato,
            c.IDempleado,
            c.IDproyecto,
            COALESCE(p.Nombre, c.Obra) AS Obra,
            c.Cargo,
            c.FechaInicio,
            c.FechaFin,
            c.SalarioDiario,
            c.Estado,
            c.FechaLiquidacion,
            c.TotalLiquidacion,
            e.IDtipoDocumento,
            ISNULL(td.TipoDocumento, 'DNI') AS TipoDocumento,
            e.NumeroDocumento,
            e.Nombres,
            e.ApellidoPaterno,
            e.ApellidoMaterno,
            e.Email,
            e.Celular,
            CONCAT(e.Nombres, ' ', e.ApellidoPaterno, ' ', e.ApellidoMaterno) AS Empleado,
            ISNULL(NULLIF(det.Area, ''), 'Sin area') AS Area
        FROM dbo.RRHH_Contrato c
        JOIN dbo.Empleado e ON c.IDempleado = e.IDempleado
        LEFT JOIN dbo.Tipo_Documento td ON e.IDtipoDocumento = td.IDtipoDocumento
        LEFT JOIN dbo.Proyecto p ON c.IDproyecto = p.IDproyecto
        OUTER APPLY (
            SELECT TOP 1 Area
            FROM dbo.Detalle_Empleado de
            WHERE de.IDempleado = e.IDempleado
            ORDER BY de.IDdetalleEmpleado DESC
        ) det
        WHERE c.IDcontrato = :id_contrato
        """,
        {"id_contrato": id_contrato},
        "Contrato no encontrado",
    )


def _document_shell(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{_txt(title)}</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: #111827;
      background: #e5e7eb;
      font-family: Arial, Helvetica, sans-serif;
      line-height: 1.45;
    }}
    .print-toolbar {{
      position: sticky;
      top: 0;
      z-index: 10;
      display: flex;
      justify-content: center;
      gap: 10px;
      padding: 12px;
      background: #111827;
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.22);
    }}
    .print-toolbar button {{
      min-height: 38px;
      padding: 0 14px;
      color: #fff;
      background: #0f766e;
      border: 0;
      border-radius: 6px;
      font-weight: 700;
      cursor: pointer;
    }}
    .page {{
      width: min(210mm, calc(100vw - 24px));
      min-height: 297mm;
      margin: 18px auto;
      padding: 18mm;
      background: #fff;
      box-shadow: 0 18px 40px rgba(0, 0, 0, 0.12);
    }}
    .doc-header {{
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 18px;
      padding-bottom: 14px;
      border-bottom: 2px solid #111827;
    }}
    .doc-brand strong {{
      display: block;
      font-size: 18px;
      letter-spacing: 0.02em;
    }}
    .doc-brand span,
    .doc-meta span {{
      display: block;
      color: #4b5563;
      font-size: 12px;
    }}
    h1 {{
      margin: 26px 0 18px;
      text-align: center;
      font-size: 24px;
      letter-spacing: 0.03em;
      text-transform: uppercase;
    }}
    h2 {{
      margin: 18px 0 8px;
      font-size: 15px;
      text-transform: uppercase;
    }}
    p {{ margin: 0 0 11px; text-align: justify; }}
    .grid-2 {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px 18px;
      margin: 14px 0;
    }}
    .field-line {{
      min-height: 30px;
      padding: 6px 0;
      border-bottom: 1px solid #9ca3af;
      font-size: 13px;
    }}
    .field-line strong {{
      display: inline-block;
      min-width: 132px;
      color: #374151;
    }}
    .signature-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 60px;
      margin-top: 54px;
      text-align: center;
    }}
    .signature-line {{
      padding-top: 8px;
      border-top: 1px solid #111827;
      font-weight: 700;
    }}
    .certificate {{
      padding-top: 18mm;
    }}
    .certificate h1 {{
      margin-top: 58px;
      margin-bottom: 40px;
      font-size: 28px;
    }}
    .certificate-body {{
      max-width: 160mm;
      margin: 0 auto;
      font-size: 16px;
    }}
    .certificate-date {{
      margin-top: 40px;
      font-style: italic;
    }}
    .boleta {{
      padding: 10mm;
      font-size: 11px;
    }}
    .boleta h1 {{
      margin: 0 0 8px;
      color: #4d8b14;
      font-size: 19px;
      line-height: 1.25;
    }}
    .boleta-table {{
      width: 100%;
      border-collapse: collapse;
      table-layout: fixed;
    }}
    .boleta-table th,
    .boleta-table td {{
      padding: 4px 5px;
      border: 1px solid #111827;
      vertical-align: top;
      word-break: normal;
    }}
    .boleta-table th {{
      background: #eef1df;
      text-align: center;
      text-transform: uppercase;
    }}
    .boleta-label {{
      width: 18%;
      background: #eef1df;
      font-weight: 700;
    }}
    .boleta-section {{
      min-height: 132mm;
      background: #f3f5e8;
    }}
    .boleta-row {{
      display: flex;
      justify-content: space-between;
      gap: 8px;
      min-height: 18px;
    }}
    .boleta-total {{
      background: #eef1df;
      font-weight: 800;
      text-transform: uppercase;
    }}
    @page {{ size: A4; margin: 0; }}
    @media print {{
      body {{ background: #fff; }}
      .print-toolbar {{ display: none; }}
      .page {{
        width: 210mm;
        min-height: 297mm;
        margin: 0;
        box-shadow: none;
      }}
    }}
  </style>
</head>
<body>
  <div class="print-toolbar">
    <button onclick="window.print()">Imprimir / guardar PDF</button>
    <button onclick="window.close()">Cerrar</button>
  </div>
  {body}
</body>
</html>"""


def _document_response(db: Session, tipo: str, id_contrato: int, filename: str, html: str, data: dict[str, Any]) -> dict:
    _audit(
        db,
        "documentos",
        f"GENERAR_{tipo.upper()}",
        "RRHH_Contrato",
        id_contrato,
        f"Documento {tipo} generado para contrato {id_contrato}",
        {"filename": filename, "data": _json_safe(data)},
    )
    return {"tipo": tipo, "filename": filename, "html": html, "data": _json_safe(data)}


def generar_documento_contrato(db: Session, id_contrato: int) -> dict:
    contrato = _require_contrato_documento(db, id_contrato)
    salario_mensual = salario_mensual_area(contrato["Area"], contrato["SalarioDiario"])
    data = {
        "empresa": EMPRESA,
        "contrato": contrato,
        "salario_mensual": salario_mensual,
        "salario_diario": salario_diario_area(contrato["Area"], contrato["SalarioDiario"]),
    }
    body = f"""
  <main class="page">
    <header class="doc-header">
      <div class="doc-brand">
        <strong>{_txt(EMPRESA["nombre"])}</strong>
        <span>RUC {_txt(EMPRESA["ruc"])}</span>
        <span>{_txt(EMPRESA["direccion"])}</span>
      </div>
      <div class="doc-meta">
        <span>Codigo: {_txt(contrato["CodigoContrato"])}</span>
        <span>Fecha: {_txt(_fmt_date(date.today()))}</span>
      </div>
    </header>
    <h1>Contrato de trabajo sujeto a modalidad</h1>
    <p>
      Conste por el presente documento el contrato de trabajo que celebran, de una parte
      <strong>{_txt(EMPRESA["nombre"])}</strong>, con RUC <strong>{_txt(EMPRESA["ruc"])}</strong>,
      con domicilio en {_txt(EMPRESA["direccion"])}, debidamente representada por
      {_txt(EMPRESA["representante"])}, a quien en adelante se denominara EL EMPLEADOR; y de la otra parte
      <strong>{_txt(contrato["Empleado"])}</strong>, identificado con {_txt(contrato["TipoDocumento"])}
      Nro. <strong>{_txt(contrato["NumeroDocumento"])}</strong>, a quien en adelante se denominara EL TRABAJADOR.
    </p>
    <div class="grid-2">
      <div class="field-line"><strong>Area</strong>{_txt(contrato["Area"])}</div>
      <div class="field-line"><strong>Cargo</strong>{_txt(contrato["Cargo"])}</div>
      <div class="field-line"><strong>Obra</strong>{_txt(contrato["Obra"])}</div>
      <div class="field-line"><strong>Remuneracion</strong>{_txt(_fmt_money(salario_mensual))} mensual</div>
      <div class="field-line"><strong>Inicio</strong>{_txt(contrato["FechaInicio"])}</div>
      <div class="field-line"><strong>Fin</strong>{_txt(contrato["FechaFin"])}</div>
    </div>
    <h2>Primera: objeto</h2>
    <p>
      EL EMPLEADOR contrata los servicios personales de EL TRABAJADOR para desempeñar el cargo indicado,
      brindando apoyo a las actividades operativas y administrativas vinculadas a la obra asignada.
    </p>
    <h2>Segunda: plazo</h2>
    <p>
      El presente contrato rige desde el {_txt(contrato["FechaInicio"])} hasta el {_txt(contrato["FechaFin"])},
      pudiendo renovarse por acuerdo de las partes y segun las necesidades del proyecto.
    </p>
    <h2>Tercera: remuneracion y jornada</h2>
    <p>
      EL TRABAJADOR percibira una remuneracion bruta mensual simulada de
      <strong>{_txt(_fmt_money(salario_mensual))}</strong>, equivalente a un jornal referencial de
      <strong>{_txt(_fmt_money(data["salario_diario"]))}</strong>. La jornada ordinaria se registrara en el
      modulo de asistencia y destajo del TPS MAAQ.
    </p>
    <h2>Cuarta: obligaciones</h2>
    <p>
      EL TRABAJADOR se obliga a cumplir las indicaciones de seguridad, calidad, asistencia, reserva de informacion
      y demas politicas internas aplicables a la obra o area en la que presta servicios.
    </p>
    <h2>Quinta: conformidad</h2>
    <p>
      Leido el presente documento, ambas partes manifiestan su conformidad y firman en senal de aceptacion.
    </p>
    <p>Lima, {_txt(_fecha_larga(date.today()))}.</p>
    <div class="signature-grid">
      <div><div class="signature-line">EL EMPLEADOR</div><small>RUC {_txt(EMPRESA["ruc"])}</small></div>
      <div><div class="signature-line">EL TRABAJADOR</div><small>{_txt(contrato["NumeroDocumento"])}</small></div>
    </div>
  </main>
"""
    return _document_response(
        db,
        "contrato",
        id_contrato,
        f"contrato-{contrato['CodigoContrato']}.html",
        _document_shell("Contrato de trabajo", body),
        data,
    )


def generar_documento_certificado(db: Session, id_contrato: int, fecha_fin: date | None = None) -> dict:
    contrato = _require_contrato_documento(db, id_contrato)
    fecha_hasta = fecha_fin or contrato["FechaLiquidacion"] or contrato["FechaFin"]
    data = {"empresa": EMPRESA, "contrato": contrato, "fecha_hasta": fecha_hasta}
    body = f"""
  <main class="page certificate">
    <header class="doc-header">
      <div class="doc-brand">
        <strong>{_txt(EMPRESA["nombre"])}</strong>
        <span>Tus aliados para el exito</span>
      </div>
      <div class="doc-meta">
        <span>RUC {_txt(EMPRESA["ruc"])}</span>
      </div>
    </header>
    <h1>Certificado de trabajo</h1>
    <section class="certificate-body">
      <p>
        <strong>{_txt(EMPRESA["nombre"])}</strong>, con RUC <strong>{_txt(EMPRESA["ruc"])}</strong>,
        debidamente representada por {_txt(EMPRESA["representante"])}, identificado con DNI
        {_txt(EMPRESA["dni_representante"])}, certifica que el Sr(a).
        <strong>{_txt(contrato["Empleado"])}</strong>, identificado con {_txt(contrato["TipoDocumento"])}
        <strong>{_txt(contrato["NumeroDocumento"])}</strong>, ha laborado en nuestra empresa en el cargo de
        <strong>{_txt(contrato["Cargo"])}</strong>, area <strong>{_txt(contrato["Area"])}</strong>,
        desde el {_txt(contrato["FechaInicio"])} hasta el {_txt(fecha_hasta)}.
      </p>
      <p>
        Se expide la presente a solicitud del interesado, para los fines que crea conveniente. Sin otro particular,
        quedamos a su disposicion.
      </p>
      <p class="certificate-date">Lima, {_txt(_fecha_larga(date.today()))}.</p>
      <div class="signature-grid">
        <div></div>
        <div><div class="signature-line">R.U.C. {_txt(EMPRESA["ruc"])}</div></div>
      </div>
    </section>
  </main>
"""
    return _document_response(
        db,
        "certificado",
        id_contrato,
        f"certificado-{contrato['CodigoContrato']}.html",
        _document_shell("Certificado de trabajo", body),
        data,
    )


def generar_pdf_contrato(db: Session, id_contrato: int) -> dict[str, Any]:
    contrato = _require_contrato_documento(db, id_contrato)
    salario_mensual = salario_mensual_area(contrato["Area"], contrato["SalarioDiario"])
    salario_diario = salario_diario_area(contrato["Area"], contrato["SalarioDiario"])
    styles = _pdf_styles()
    story: list[Any] = [
        _pdf_header(styles),
        Spacer(1, 0.45 * cm),
        Paragraph("CONTRATO DE TRABAJO SUJETO A MODALIDAD", styles["title"]),
        Paragraph(
            "Conste por el presente documento el contrato de trabajo que celebran, de una parte "
            f"<b>{_pdf_text(EMPRESA['nombre'])}</b>, con RUC <b>{_pdf_text(EMPRESA['ruc'])}</b>, "
            f"con domicilio en {_pdf_text(EMPRESA['direccion'])}, debidamente representada por "
            f"{_pdf_text(EMPRESA['representante'])}, a quien en adelante se denominara EL EMPLEADOR; "
            f"y de la otra parte <b>{_pdf_text(contrato['Empleado'])}</b>, identificado con "
            f"{_pdf_text(contrato['TipoDocumento'])} Nro. <b>{_pdf_text(contrato['NumeroDocumento'])}</b>, "
            "a quien en adelante se denominara EL TRABAJADOR.",
            styles["normal"],
        ),
        Spacer(1, 0.15 * cm),
        _info_table(
            [
                ("Codigo de contrato", contrato["CodigoContrato"]),
                ("Area", contrato["Area"]),
                ("Cargo", contrato["Cargo"]),
                ("Obra", contrato["Obra"]),
                ("Fecha de inicio", contrato["FechaInicio"]),
                ("Fecha fin", contrato["FechaFin"]),
                ("Remuneracion mensual", f"{_fmt_money(salario_mensual)}"),
                ("Jornal diario referencial", f"{_fmt_money(salario_diario)}"),
            ],
            styles,
        ),
        Spacer(1, 0.35 * cm),
        Paragraph("PRIMERA: OBJETO", styles["subtitle"]),
        _p(
            "EL EMPLEADOR contrata los servicios personales de EL TRABAJADOR para desempenar el cargo indicado, "
            "brindando apoyo a las actividades operativas y administrativas vinculadas a la obra asignada.",
            styles["normal"],
        ),
        Paragraph("SEGUNDA: PLAZO", styles["subtitle"]),
        _p(
            f"El presente contrato rige desde el {_fmt_date(contrato['FechaInicio'])} hasta el "
            f"{_fmt_date(contrato['FechaFin'])}, pudiendo renovarse por acuerdo de las partes y segun las "
            "necesidades del proyecto.",
            styles["normal"],
        ),
        Paragraph("TERCERA: REMUNERACION Y JORNADA", styles["subtitle"]),
        _p(
            f"EL TRABAJADOR percibira una remuneracion bruta mensual simulada de {_fmt_money(salario_mensual)}, "
            f"equivalente a un jornal referencial de {_fmt_money(salario_diario)}. La jornada ordinaria se "
            "registrara en el modulo de asistencia y destajo del TPS MAAQ.",
            styles["normal"],
        ),
        Paragraph("CUARTA: OBLIGACIONES", styles["subtitle"]),
        _p(
            "EL TRABAJADOR se obliga a cumplir las indicaciones de seguridad, calidad, asistencia, reserva de "
            "informacion y demas politicas internas aplicables a la obra o area en la que presta servicios.",
            styles["normal"],
        ),
        Paragraph("QUINTA: CONFORMIDAD", styles["subtitle"]),
        _p(
            "Leido el presente documento, ambas partes manifiestan su conformidad y firman en senal de aceptacion.",
            styles["normal"],
        ),
        Spacer(1, 0.2 * cm),
        _p(f"Lima, {_fecha_larga(date.today())}.", styles["normal"]),
        Spacer(1, 0.55 * cm),
        _signature_table("EL EMPLEADOR", "EL TRABAJADOR"),
    ]
    filename = f"contrato-{contrato['CodigoContrato']}.pdf"
    _audit(
        db,
        "documentos",
        "DESCARGAR_CONTRATO_PDF",
        "RRHH_Contrato",
        id_contrato,
        f"PDF de contrato generado para {contrato['CodigoContrato']}",
        {"filename": filename},
    )
    return {"filename": filename, "content": _pdf_document(story)}


def generar_pdf_certificado(db: Session, id_contrato: int, fecha_fin: date | None = None) -> dict[str, Any]:
    contrato = _require_contrato_documento(db, id_contrato)
    fecha_hasta = fecha_fin or contrato["FechaLiquidacion"] or contrato["FechaFin"]
    styles = _pdf_styles()
    story: list[Any] = [
        _pdf_header(styles),
        Spacer(1, 2.0 * cm),
        Paragraph("CERTIFICADO DE TRABAJO", styles["title"]),
        Spacer(1, 0.9 * cm),
        Paragraph(
            f"<b>{_pdf_text(EMPRESA['nombre'])}</b>, con RUC <b>{_pdf_text(EMPRESA['ruc'])}</b>, "
            f"debidamente representada por {_pdf_text(EMPRESA['representante'])}, identificado con DNI "
            f"{_pdf_text(EMPRESA['dni_representante'])}, certifica que el Sr(a). "
            f"<b>{_pdf_text(contrato['Empleado'])}</b>, identificado con {_pdf_text(contrato['TipoDocumento'])} "
            f"<b>{_pdf_text(contrato['NumeroDocumento'])}</b>, ha laborado en nuestra empresa en el cargo de "
            f"<b>{_pdf_text(contrato['Cargo'])}</b>, area <b>{_pdf_text(contrato['Area'])}</b>, desde el "
            f"{_pdf_text(contrato['FechaInicio'])} hasta el {_pdf_text(fecha_hasta)}.",
            styles["normal"],
        ),
        Spacer(1, 0.35 * cm),
        _p(
            "Se expide la presente a solicitud del interesado, para los fines que crea conveniente. "
            "Sin otro particular, quedamos a su disposicion.",
            styles["normal"],
        ),
        Spacer(1, 0.7 * cm),
        _p(f"Lima, {_fecha_larga(date.today())}.", styles["normal"]),
        Spacer(1, 3.8 * cm),
        _signature_table("", f"R.U.C. {EMPRESA['ruc']}"),
    ]
    filename = f"certificado-{contrato['CodigoContrato']}.pdf"
    _audit(
        db,
        "documentos",
        "DESCARGAR_CERTIFICADO_PDF",
        "RRHH_Contrato",
        id_contrato,
        f"PDF de certificado generado para {contrato['CodigoContrato']}",
        {"filename": filename, "fecha_hasta": str(fecha_hasta)},
    )
    return {"filename": filename, "content": _pdf_document(story)}


def _boleta_periodo(db: Session, contrato: dict, fecha_cese: date) -> dict[str, Any]:
    fecha_inicio = contrato["FechaInicio"]
    fecha_fin_contrato = contrato["FechaFin"]
    if fecha_cese < fecha_inicio:
        raise AppError("La fecha de cese no puede ser anterior al inicio del contrato", 422, "FECHA_CESE_INVALIDA", "fecha_cese")

    periodo_fin = min(fecha_cese, fecha_fin_contrato)
    periodo_inicio = max(date(periodo_fin.year, periodo_fin.month, 1), fecha_inicio)
    dias_periodo = max(0, (periodo_fin - periodo_inicio).days + 1)

    asistencia = fetch_one(
        db,
        """
        SELECT
            ISNULL(SUM(CASE WHEN Estado IN ('presente', 'tardanza') THEN Horas ELSE 0 END), 0) AS HorasRegistradas,
            ISNULL(SUM(CASE WHEN Estado = 'inasistencia' THEN 1 ELSE 0 END), 0) AS Inasistencias,
            ISNULL(SUM(CASE WHEN Estado = 'descanso' THEN 1 ELSE 0 END), 0) AS Descansos,
            ISNULL(SUM(CASE WHEN Estado = 'permiso' THEN 1 ELSE 0 END), 0) AS Permisos,
            ISNULL(SUM(CASE WHEN Estado = 'tardanza' THEN 1 ELSE 0 END), 0) AS Tardanzas,
            ISNULL(SUM(Extras), 0) AS Extras
        FROM dbo.RRHH_Asistencia
        WHERE IDempleado = :id_empleado
          AND Fecha BETWEEN :periodo_inicio AND :periodo_fin
          AND (IDcontrato = :id_contrato OR (IDcontrato IS NULL AND Obra = :obra))
        """,
        {
            "id_empleado": contrato["IDempleado"],
            "id_contrato": contrato["IDcontrato"],
            "obra": contrato["Obra"],
            "periodo_inicio": periodo_inicio,
            "periodo_fin": periodo_fin,
        },
    ) or {}
    destajo = fetch_one(
        db,
        """
        SELECT ISNULL(SUM(Total), 0) AS TotalDestajo
        FROM dbo.RRHH_Destajo
        WHERE IDempleado = :id_empleado
          AND Fecha BETWEEN :periodo_inicio AND :periodo_fin
          AND (IDcontrato = :id_contrato OR (IDcontrato IS NULL AND Obra = :obra))
        """,
        {
            "id_empleado": contrato["IDempleado"],
            "id_contrato": contrato["IDcontrato"],
            "obra": contrato["Obra"],
            "periodo_inicio": periodo_inicio,
            "periodo_fin": periodo_fin,
        },
    ) or {}

    salario_mensual = salario_mensual_area(contrato["Area"], contrato["SalarioDiario"])
    salario_diario = _money(salario_mensual / Decimal("30"))
    inasistencias = _decimal(asistencia.get("Inasistencias"))
    descansos = _decimal(asistencia.get("Descansos"))
    tardanzas = _decimal(asistencia.get("Tardanzas"))
    extras = _money(_decimal(asistencia.get("Extras")))
    pago_destajo = _money(_decimal(destajo.get("TotalDestajo")))
    horas_laboradas = max(Decimal("0"), Decimal(dias_periodo * 8) - (inasistencias * Decimal("8")))

    remuneracion_basica = _money(salario_diario * Decimal(dias_periodo))
    descuento_inasistencias = _money(salario_diario * inasistencias)
    total_ingresos = _money(remuneracion_basica + extras + pago_destajo)
    pension_onp = _money(total_ingresos * Decimal("0.13"))
    total_descuentos = _money(pension_onp + descuento_inasistencias)
    aporte_essalud = _money(total_ingresos * Decimal("0.09"))
    neto_pagar = _money(total_ingresos - total_descuentos)

    return {
        "periodo_inicio": periodo_inicio,
        "periodo_fin": periodo_fin,
        "dias_periodo": dias_periodo,
        "salario_mensual": salario_mensual,
        "salario_diario": salario_diario,
        "horas_laboradas": horas_laboradas,
        "inasistencias": inasistencias,
        "descansos": descansos,
        "permisos": _decimal(asistencia.get("Permisos")),
        "tardanzas": tardanzas,
        "remuneracion_basica": remuneracion_basica,
        "extras": extras,
        "destajo": pago_destajo,
        "descuento_inasistencias": descuento_inasistencias,
        "pension_onp": pension_onp,
        "total_ingresos": total_ingresos,
        "total_descuentos": total_descuentos,
        "aporte_essalud": aporte_essalud,
        "total_aportes": aporte_essalud,
        "neto_pagar": neto_pagar,
    }


def _boleta_item(label: str, value: Any = None) -> str:
    rendered = "-" if value is None else _fmt_money(value)
    return f'<div class="boleta-row"><span>{_txt(label)}</span><strong>{_txt(rendered)}</strong></div>'


def generar_documento_boleta(db: Session, id_contrato: int, fecha_cese: date, motivo: str = "renuncia") -> dict:
    contrato = _require_contrato_documento(db, id_contrato)
    periodo = _boleta_periodo(db, contrato, fecha_cese)
    data = {"empresa": EMPRESA, "contrato": contrato, "fecha_cese": fecha_cese, "motivo": motivo, "calculo": periodo}
    body = f"""
  <main class="page boleta">
    <h1>Boleta de pago<br />Articulo 19 del Decreto Supremo Nro 009-2011-TR</h1>
    <table class="boleta-table">
      <tbody>
        <tr>
          <td class="boleta-label">Trabajador</td>
          <td colspan="3">{_txt(contrato["Empleado"])}</td>
          <td class="boleta-label">Cargo</td>
          <td>{_txt(contrato["Cargo"])}</td>
        </tr>
        <tr>
          <td class="boleta-label">Pension</td>
          <td>ONP</td>
          <td class="boleta-label">CUSPP</td>
          <td>-</td>
          <td class="boleta-label">Situacion</td>
          <td>{_txt(motivo)}</td>
        </tr>
        <tr>
          <td class="boleta-label">Fecha de ingreso</td>
          <td>{_txt(contrato["FechaInicio"])}</td>
          <td class="boleta-label">Faltas</td>
          <td>{_txt(periodo["inasistencias"])}</td>
          <td class="boleta-label">Fecha de cese</td>
          <td>{_txt(fecha_cese)}</td>
        </tr>
        <tr>
          <td class="boleta-label">Asistencias</td>
          <td>{_txt(periodo["dias_periodo"])}</td>
          <td class="boleta-label">Tardanzas</td>
          <td>{_txt(periodo["tardanzas"])}</td>
          <td class="boleta-label">Haber basico</td>
          <td>{_txt(_fmt_money(periodo["salario_mensual"]))}</td>
        </tr>
        <tr>
          <td class="boleta-label">Descansos</td>
          <td>{_txt(periodo["descansos"])}</td>
          <td class="boleta-label">Total horas lab</td>
          <td>{_txt(periodo["horas_laboradas"])}</td>
          <td class="boleta-label">Periodo</td>
          <td>{_txt(periodo["periodo_inicio"])} - {_txt(periodo["periodo_fin"])}</td>
        </tr>
      </tbody>
    </table>
    <table class="boleta-table" style="margin-top: 4px;">
      <thead>
        <tr>
          <th>Ingresos trabajador</th>
          <th>Descuentos trabajador</th>
          <th>Aportes empleador</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td class="boleta-section">
            {_boleta_item("Remuneracion basica", periodo["remuneracion_basica"])}
            {_boleta_item("Asignacion familiar", Decimal("0.00"))}
            {_boleta_item("Trabajo feriado o descanso", None)}
            {_boleta_item("Horas extras 25%", periodo["extras"])}
            {_boleta_item("Destajo por obra", periodo["destajo"])}
            {_boleta_item("Remuneracion vacacional", None)}
            {_boleta_item("Gratificaciones", None)}
            {_boleta_item("CTS", None)}
          </td>
          <td class="boleta-section">
            {_boleta_item("ONP 13%", periodo["pension_onp"])}
            {_boleta_item("SPP aporte oblig. 10%", None)}
            {_boleta_item("SPP prima seguro 1.37%", None)}
            {_boleta_item("Renta 5TA retenciones", None)}
            {_boleta_item("Adelantos", None)}
            {_boleta_item("Inasistencias", periodo["descuento_inasistencias"])}
            {_boleta_item("Descuento autorizado", None)}
          </td>
          <td class="boleta-section">
            {_boleta_item("EsSalud 9%", periodo["aporte_essalud"])}
            {_boleta_item("EPS", None)}
            {_boleta_item("Seguro integral de salud", None)}
            {_boleta_item("SCTR salud", None)}
            {_boleta_item("SCTR pension", None)}
          </td>
        </tr>
        <tr class="boleta-total">
          <td>Total ingresos (A) {_txt(_fmt_money(periodo["total_ingresos"]))}</td>
          <td>Total descuentos (B) {_txt(_fmt_money(periodo["total_descuentos"]))}</td>
          <td>Total aportes {_txt(_fmt_money(periodo["total_aportes"]))}</td>
        </tr>
        <tr class="boleta-total">
          <td colspan="2">Neto a pagar (A) - (B)</td>
          <td>{_txt(_fmt_money(periodo["neto_pagar"]))}</td>
        </tr>
      </tbody>
    </table>
    <p style="margin-top: 10px;">Son: {_txt(_fmt_money(periodo["neto_pagar"]))} soles.</p>
    <div class="signature-grid">
      <div><div class="signature-line">EMPLEADOR</div></div>
      <div><div class="signature-line">TRABAJADOR</div></div>
    </div>
  </main>
"""
    return _document_response(
        db,
        "boleta",
        id_contrato,
        f"boleta-{contrato['CodigoContrato']}.html",
        _document_shell("Boleta de pago", body),
        data,
    )


def list_auditoria(db: Session, limit: int = 200) -> list[dict]:
    return fetch_all(
        db,
        """
        SELECT TOP (:limit) *
        FROM dbo.RRHH_Auditoria
        ORDER BY IDaudit DESC
        """,
        {"limit": limit},
    )
