from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.schemas.clientes import (
    ClienteJuridicoCreate,
    ClienteNaturalCreate,
    ContactoJuridicoUpdate,
    ContactoNaturalUpdate,
    DireccionClienteUpdate,
)
from app.services.db import execute, fetch_all, fetch_one, require_one


def list_clientes(db: Session, tipo: str | None = None, q: str | None = None) -> list[dict]:
    filters = []
    params: dict[str, object] = {}
    if tipo == "natural":
        filters.append("pn.IDcliente IS NOT NULL")
    if tipo == "juridico":
        filters.append("pj.IDcliente IS NOT NULL")
    if q:
        filters.append(
            "(c.NumeroDocumento LIKE :q OR pn.Nombres LIKE :q OR pn.ApellidoPaterno LIKE :q OR pj.RazonSocial LIKE :q)"
        )
        params["q"] = f"%{q}%"

    where = f"WHERE {' AND '.join(filters)}" if filters else ""
    return fetch_all(
        db,
        f"""
        SELECT
            c.IDcliente,
            c.IDtipoDocumento,
            c.NumeroDocumento,
            CAST(c.Email AS varchar(100)) AS Email,
            c.IDcodigoPostal,
            c.IDtipoCalle,
            c.NombreCalle,
            c.NumeroCalle,
            pn.ApellidoPaterno,
            pn.ApellidoMaterno,
            pn.Nombres,
            pn.Celular,
            pj.RazonSocial,
            pj.Telefono,
            CASE
                WHEN pn.IDcliente IS NOT NULL THEN 'natural'
                WHEN pj.IDcliente IS NOT NULL THEN 'juridico'
                ELSE 'sin_tipo'
            END AS TipoCliente
        FROM dbo.Cliente c
        LEFT JOIN dbo.Persona_Natural pn ON c.IDcliente = pn.IDcliente
        LEFT JOIN dbo.Persona_Juridica pj ON c.IDcliente = pj.IDcliente
        {where}
        ORDER BY c.IDcliente DESC
        """,
        params,
    )


def get_cliente(db: Session, id_cliente: int) -> dict:
    item = fetch_one(
        db,
        """
        SELECT
            c.IDcliente,
            c.IDtipoDocumento,
            c.NumeroDocumento,
            CAST(c.Email AS varchar(100)) AS Email,
            c.IDcodigoPostal,
            c.IDtipoCalle,
            c.NombreCalle,
            c.NumeroCalle,
            pn.ApellidoPaterno,
            pn.ApellidoMaterno,
            pn.Nombres,
            pn.Celular,
            pj.RazonSocial,
            pj.Telefono,
            CASE
                WHEN pn.IDcliente IS NOT NULL THEN 'natural'
                WHEN pj.IDcliente IS NOT NULL THEN 'juridico'
                ELSE 'sin_tipo'
            END AS TipoCliente
        FROM dbo.Cliente c
        LEFT JOIN dbo.Persona_Natural pn ON c.IDcliente = pn.IDcliente
        LEFT JOIN dbo.Persona_Juridica pj ON c.IDcliente = pj.IDcliente
        WHERE c.IDcliente = :id_cliente
        """,
        {"id_cliente": id_cliente},
    )
    if item is None:
        raise AppError("Cliente no encontrado", 404, "CLIENTE_NOT_FOUND")
    return item


def _validate_duplicate(db: Session, id_tipo_documento: int, numero_documento: str) -> None:
    exists = fetch_one(
        db,
        """
        SELECT IDcliente
        FROM dbo.Cliente
        WHERE IDtipoDocumento = :id_tipo_documento AND NumeroDocumento = :numero_documento
        """,
        {"id_tipo_documento": id_tipo_documento, "numero_documento": numero_documento},
    )
    if exists:
        raise AppError("El documento ya esta registrado", 409, "DOCUMENTO_DUPLICADO", "numero_documento")


def _insert_cliente_base(db: Session, payload) -> int:
    row = fetch_one(
        db,
        """
        INSERT INTO dbo.Cliente
            (IDtipoDocumento, NumeroDocumento, Email, IDcodigoPostal, IDtipoCalle, NombreCalle, NumeroCalle)
        OUTPUT INSERTED.IDcliente AS IDcliente
        VALUES
            (:id_tipo_documento, :numero_documento, :email, :id_codigo_postal, :id_tipo_calle, :nombre_calle, :numero_calle)
        """,
        payload.model_dump(),
    )
    return int(row["IDcliente"])


def create_natural(db: Session, payload: ClienteNaturalCreate) -> dict:
    _validate_duplicate(db, payload.id_tipo_documento, payload.numero_documento)
    id_cliente = _insert_cliente_base(db, payload)
    execute(
        db,
        """
        INSERT INTO dbo.Persona_Natural
            (IDcliente, ApellidoPaterno, ApellidoMaterno, Nombres, Celular)
        VALUES
            (:id_cliente, :apellido_paterno, :apellido_materno, :nombres, :celular)
        """,
        {
            "id_cliente": id_cliente,
            "apellido_paterno": payload.apellido_paterno,
            "apellido_materno": payload.apellido_materno,
            "nombres": payload.nombres,
            "celular": payload.celular,
        },
    )
    return get_cliente(db, id_cliente)


def create_juridico(db: Session, payload: ClienteJuridicoCreate) -> dict:
    _validate_duplicate(db, payload.id_tipo_documento, payload.numero_documento)
    id_cliente = _insert_cliente_base(db, payload)
    execute(
        db,
        """
        INSERT INTO dbo.Persona_Juridica
            (IDcliente, RazonSocial, Telefono)
        VALUES
            (:id_cliente, :razon_social, :telefono)
        """,
        {"id_cliente": id_cliente, "razon_social": payload.razon_social, "telefono": payload.telefono},
    )
    return get_cliente(db, id_cliente)


def update_direccion(db: Session, id_cliente: int, payload: DireccionClienteUpdate) -> dict:
    current = require_one(
        db,
        """
        SELECT IDcodigoPostal, IDtipoCalle, NombreCalle, NumeroCalle
        FROM dbo.Cliente
        WHERE IDcliente = :id_cliente
        """,
        {"id_cliente": id_cliente},
        "Cliente no encontrado",
    )
    execute(
        db,
        """
        UPDATE dbo.Cliente
        SET IDcodigoPostal = :id_codigo_postal,
            IDtipoCalle = :id_tipo_calle,
            NombreCalle = :nombre_calle,
            NumeroCalle = :numero_calle
        WHERE IDcliente = :id_cliente
        """,
        {**payload.model_dump(), "id_cliente": id_cliente},
    )
    execute(
        db,
        """
        INSERT INTO dbo.Historial_Direccion_Cliente
            (IDcliente, IDcodigoPostalAnterior, IDtipoCalleAnterior, NombreCalleAnterior, NumeroCalleAnterior,
             IDcodigoPostalActual, IDtipoCalleActual, NombreCalleActual, NumeroCalleActual, FechaCambio, Usuario)
        VALUES
            (:id_cliente, :old_codigo_postal, :old_tipo_calle, :old_nombre_calle, :old_numero_calle,
             :id_codigo_postal, :id_tipo_calle, :nombre_calle, :numero_calle, CONVERT(date, GETDATE()), :usuario)
        """,
        {
            "id_cliente": id_cliente,
            "old_codigo_postal": current["IDcodigoPostal"],
            "old_tipo_calle": current["IDtipoCalle"],
            "old_nombre_calle": current["NombreCalle"],
            "old_numero_calle": current["NumeroCalle"],
            **payload.model_dump(),
        },
    )
    return get_cliente(db, id_cliente)


def update_contacto_natural(db: Session, id_cliente: int, payload: ContactoNaturalUpdate) -> dict:
    current = require_one(
        db,
        """
        SELECT pn.Celular, CAST(c.Email AS varchar(100)) AS Email
        FROM dbo.Cliente c
        JOIN dbo.Persona_Natural pn ON c.IDcliente = pn.IDcliente
        WHERE c.IDcliente = :id_cliente
        """,
        {"id_cliente": id_cliente},
        "Cliente natural no encontrado",
    )
    execute(db, "UPDATE dbo.Persona_Natural SET Celular = :celular WHERE IDcliente = :id_cliente", {"celular": payload.celular, "id_cliente": id_cliente})
    execute(db, "UPDATE dbo.Cliente SET Email = :email WHERE IDcliente = :id_cliente", {"email": payload.email, "id_cliente": id_cliente})
    execute(
        db,
        """
        INSERT INTO dbo.Historial_Contacto_Cliente_Natural
            (IDcliente, CelularAnterior, CelularActual, EmailAnterior, EmailActual, FechaCambio, Usuario)
        VALUES
            (:id_cliente, :celular_anterior, :celular_actual, :email_anterior, :email_actual, CONVERT(date, GETDATE()), :usuario)
        """,
        {
            "id_cliente": id_cliente,
            "celular_anterior": current["Celular"],
            "celular_actual": payload.celular,
            "email_anterior": current["Email"],
            "email_actual": payload.email,
            "usuario": payload.usuario,
        },
    )
    return get_cliente(db, id_cliente)


def update_contacto_juridico(db: Session, id_cliente: int, payload: ContactoJuridicoUpdate) -> dict:
    current = require_one(
        db,
        """
        SELECT pj.Telefono, CAST(c.Email AS varchar(100)) AS Email
        FROM dbo.Cliente c
        JOIN dbo.Persona_Juridica pj ON c.IDcliente = pj.IDcliente
        WHERE c.IDcliente = :id_cliente
        """,
        {"id_cliente": id_cliente},
        "Cliente juridico no encontrado",
    )
    execute(db, "UPDATE dbo.Persona_Juridica SET Telefono = :telefono WHERE IDcliente = :id_cliente", {"telefono": payload.telefono, "id_cliente": id_cliente})
    execute(db, "UPDATE dbo.Cliente SET Email = :email WHERE IDcliente = :id_cliente", {"email": payload.email, "id_cliente": id_cliente})
    execute(
        db,
        """
        INSERT INTO dbo.Historial_Contacto_Cliente_Juridico
            (IDcliente, TelefonoAnterior, TelefonoActual, EmailAnterior, EmailActual, FechaCambio, Usuario)
        VALUES
            (:id_cliente, :telefono_anterior, :telefono_actual, :email_anterior, :email_actual, CONVERT(date, GETDATE()), :usuario)
        """,
        {
            "id_cliente": id_cliente,
            "telefono_anterior": current["Telefono"],
            "telefono_actual": payload.telefono,
            "email_anterior": current["Email"],
            "email_actual": payload.email,
            "usuario": payload.usuario,
        },
    )
    return get_cliente(db, id_cliente)
