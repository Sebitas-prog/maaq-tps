from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.services.db import fetch_all, fetch_one


CATALOGS: dict[str, dict[str, Any]] = {
    "tipo-documento": {
        "table": "Tipo_Documento",
        "id": "IDtipoDocumento",
        "fields": ["TipoDocumento"],
        "label": "[TipoDocumento]",
    },
    "tipo-calle": {
        "table": "Tipo_Calle",
        "id": "IDtipoCalle",
        "fields": ["Abreviatura", "TipoCalle"],
        "label": "CONCAT([Abreviatura], ' - ', [TipoCalle])",
    },
    "codigo-postal": {
        "table": "Codigo_Postal",
        "id": "IDcodigoPostal",
        "fields": ["Codigo", "Capital", "Distrito", "Provincia", "Departamento"],
        "label": "CONCAT([Codigo], ' - ', [Distrito], ', ', [Departamento])",
    },
    "cliente-pais": {
        "table": "Cliente_Pais",
        "id": "IDpais",
        "fields": ["Pais"],
        "label": "[Pais]",
    },
    "tipo-sector": {
        "table": "Tipo_Sector",
        "id": "IDsector",
        "fields": ["Sector"],
        "label": "[Sector]",
    },
    "tipo-edificacion": {
        "table": "Tipo_Edificacion",
        "id": "IDtipoEdificacion",
        "fields": ["TipoEdificacion"],
        "label": "[TipoEdificacion]",
    },
    "tipo-estado": {
        "table": "Tipo_Estado",
        "id": "IDtipoEstado",
        "fields": ["Estado"],
        "label": "[Estado]",
    },
    "tipo-empleado": {
        "table": "Tipo_Empleado",
        "id": "IDtipoEmpleado",
        "fields": ["TipoEmpleado"],
        "label": "[TipoEmpleado]",
    },
    "departamento": {
        "table": "Departamento",
        "id": "IDdepartamento",
        "fields": ["CodigoDepartamento", "Nombre", "NumeroEmpleados", "IDproyecto"],
        "label": "CONCAT([CodigoDepartamento], ' - ', [Nombre])",
    },
}


def _catalog_or_404(name: str) -> dict[str, Any]:
    catalog = CATALOGS.get(name)
    if catalog is None:
        raise AppError("Catalogo no soportado", 404, "CATALOG_NOT_FOUND")
    return catalog


def list_catalog(db: Session, name: str) -> list[dict[str, Any]]:
    catalog = _catalog_or_404(name)
    fields_sql = ", ".join(f"[{field}]" for field in catalog["fields"])
    return fetch_all(
        db,
        f"""
        SELECT
            [{catalog["id"]}] AS id,
            {catalog["label"]} AS label,
            {fields_sql}
        FROM dbo.[{catalog["table"]}]
        ORDER BY label
        """,
    )


def list_all_catalogs(db: Session) -> dict[str, list[dict[str, Any]]]:
    return {name: list_catalog(db, name) for name in CATALOGS}


def create_catalog_item(db: Session, name: str, payload: dict[str, Any]) -> dict[str, Any]:
    catalog = _catalog_or_404(name)
    missing = [field for field in catalog["fields"] if payload.get(field) in (None, "")]
    if missing:
        raise AppError("Campos obligatorios incompletos", 422, "VALIDATION_ERROR", field=", ".join(missing))

    columns = ", ".join(f"[{field}]" for field in catalog["fields"])
    values = ", ".join(f":{field}" for field in catalog["fields"])
    params = {field: payload[field] for field in catalog["fields"]}
    row = fetch_one(
        db,
        f"""
        INSERT INTO dbo.[{catalog["table"]}] ({columns})
        OUTPUT INSERTED.[{catalog["id"]}] AS id
        VALUES ({values});
        """,
        params,
    )
    return fetch_one(
        db,
        f"""
        SELECT
            [{catalog["id"]}] AS id,
            {catalog["label"]} AS label
        FROM dbo.[{catalog["table"]}]
        WHERE [{catalog["id"]}] = :id
        """,
        {"id": row["id"]},
    )
