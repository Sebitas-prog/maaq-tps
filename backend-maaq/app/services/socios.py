from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.schemas.socios import AsociacionCreate, SocioAsociacionCreate, SocioCreate
from app.services.db import execute, fetch_all, fetch_one, require_one


def list_socios(db: Session, q: str | None = None) -> list[dict]:
    params: dict[str, object] = {}
    where = ""
    if q:
        where = """
        WHERE NumeroDocumento LIKE :q
           OR Nombres LIKE :q
           OR ApellidoPaterno LIKE :q
           OR Email LIKE :q
        """
        params["q"] = f"%{q}%"
    return fetch_all(db, f"SELECT * FROM dbo.Socio {where} ORDER BY IDsocio DESC", params)


def create_socio(db: Session, payload: SocioCreate) -> dict:
    exists = fetch_one(db, "SELECT IDsocio FROM dbo.Socio WHERE NumeroDocumento = :numero_documento", {"numero_documento": payload.numero_documento})
    if exists:
        raise AppError("El documento del socio ya esta registrado", 409, "DOCUMENTO_DUPLICADO", "numero_documento")
    row = fetch_one(
        db,
        """
        INSERT INTO dbo.Socio
            (IDtipoDocumento, NumeroDocumento, ApellidoPaterno, ApellidoMaterno, Nombres,
             IDcodigoPostal, IDtipoCalle, NombreCalle, NumeroCalle, Email, Celular)
        OUTPUT INSERTED.IDsocio AS IDsocio
        VALUES
            (:id_tipo_documento, :numero_documento, :apellido_paterno, :apellido_materno, :nombres,
             :id_codigo_postal, :id_tipo_calle, :nombre_calle, :numero_calle, :email, :celular)
        """,
        payload.model_dump(),
    )
    return require_one(db, "SELECT * FROM dbo.Socio WHERE IDsocio = :id_socio", {"id_socio": row["IDsocio"]}, "Socio no encontrado")


def list_asociaciones(db: Session) -> list[dict]:
    return fetch_all(
        db,
        """
        SELECT
            a.*,
            d.Nombre AS DepartamentoNombre,
            (SELECT COUNT(1) FROM dbo.Socio_Asociacion sa WHERE sa.IDasociacion = a.IDasociacion) AS TotalSocios
        FROM dbo.Asociacion a
        LEFT JOIN dbo.Departamento d ON a.IDdepartamento = d.IDdepartamento
        ORDER BY a.IDasociacion DESC
        """,
    )


def create_asociacion(db: Session, payload: AsociacionCreate) -> dict:
    row = fetch_one(
        db,
        """
        INSERT INTO dbo.Asociacion
            (CodigoDepartamento, IDcodigoPostal, IDtipoCalle, NombreCalle, NumeroCalle,
             RazonSocial, Denominacion, IDdepartamento)
        OUTPUT INSERTED.IDasociacion AS IDasociacion
        VALUES
            (:codigo_departamento, :id_codigo_postal, :id_tipo_calle, :nombre_calle, :numero_calle,
             :razon_social, :denominacion, :id_departamento)
        """,
        payload.model_dump(),
    )
    return require_one(db, "SELECT * FROM dbo.Asociacion WHERE IDasociacion = :id_asociacion", {"id_asociacion": row["IDasociacion"]}, "Asociacion no encontrada")


def link_socio_asociacion(db: Session, payload: SocioAsociacionCreate) -> dict:
    require_one(db, "SELECT IDsocio FROM dbo.Socio WHERE IDsocio = :id_socio", {"id_socio": payload.id_socio}, "Socio no encontrado")
    require_one(db, "SELECT IDasociacion FROM dbo.Asociacion WHERE IDasociacion = :id_asociacion", {"id_asociacion": payload.id_asociacion}, "Asociacion no encontrada")
    exists = fetch_one(
        db,
        """
        SELECT IDsocioAsociacion
        FROM dbo.Socio_Asociacion
        WHERE IDsocio = :id_socio AND IDasociacion = :id_asociacion
        """,
        payload.model_dump(),
    )
    if exists:
        raise AppError("El socio ya esta vinculado a esta asociacion", 409, "VINCULO_DUPLICADO")
    row = fetch_one(
        db,
        """
        INSERT INTO dbo.Socio_Asociacion (IDsocio, IDasociacion)
        OUTPUT INSERTED.IDsocioAsociacion AS IDsocioAsociacion
        VALUES (:id_socio, :id_asociacion)
        """,
        payload.model_dump(),
    )
    return {"id_socio_asociacion": row["IDsocioAsociacion"], **payload.model_dump()}


def list_vinculos(db: Session) -> list[dict]:
    return fetch_all(db, "SELECT TOP 200 * FROM dbo.Vista_Socios_Asociacion ORDER BY IDsocio DESC")
