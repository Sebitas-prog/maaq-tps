from datetime import date
from io import BytesIO
from typing import Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.common import ok
from app.schemas.rrhh import AreaEmpleadoUpdate, AsistenciaCreate, ContratacionCreate, DestajoCreate, RenovacionContrato
from app.services import rrhh as service


router = APIRouter()


def pdf_response(documento: dict):
    return StreamingResponse(
        BytesIO(documento["content"]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{documento["filename"]}"'},
    )


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    return ok(service.get_dashboard(db))


@router.post("/contratacion", status_code=201)
def contratacion(payload: ContratacionCreate, db: Session = Depends(get_db)):
    return ok(service.contratar(db, payload))


@router.get("/altas")
def altas(limit: int = Query(default=100, ge=1, le=500), db: Session = Depends(get_db)):
    data = service.list_altas(db, limit=limit)
    return ok(data, {"total": len(data)})


@router.get("/contratos")
def contratos(q: str | None = None, db: Session = Depends(get_db)):
    data = service.list_contratos(db, q=q)
    return ok(data, {"total": len(data)})


@router.get("/contratos/alertas")
def contratos_alertas(dias: int = Query(default=30, ge=1, le=365), db: Session = Depends(get_db)):
    data = service.alertas_contratos(db, dias=dias)
    return ok(data, {"total": len(data), "dias": dias})


@router.post("/contratos/{id_contrato}/renovar")
def renovar(id_contrato: int, payload: RenovacionContrato, db: Session = Depends(get_db)):
    return ok(service.renovar_contrato(db, id_contrato, payload.fecha_fin))


@router.post("/contratos/{id_contrato}/liquidar")
def liquidar(id_contrato: int, db: Session = Depends(get_db)):
    return ok(service.liquidar_contrato(db, id_contrato))


@router.get("/contratos/{id_contrato}/documentos/contrato")
def documento_contrato(id_contrato: int, db: Session = Depends(get_db)):
    return ok(service.generar_documento_contrato(db, id_contrato))


@router.get("/contratos/{id_contrato}/documentos/contrato/pdf")
def documento_contrato_pdf(id_contrato: int, db: Session = Depends(get_db)):
    return pdf_response(service.generar_pdf_contrato(db, id_contrato))


@router.get("/contratos/{id_contrato}/documentos/certificado")
def documento_certificado(id_contrato: int, fecha_fin: date | None = None, db: Session = Depends(get_db)):
    return ok(service.generar_documento_certificado(db, id_contrato, fecha_fin=fecha_fin))


@router.get("/contratos/{id_contrato}/documentos/certificado/pdf")
def documento_certificado_pdf(id_contrato: int, fecha_fin: date | None = None, db: Session = Depends(get_db)):
    return pdf_response(service.generar_pdf_certificado(db, id_contrato, fecha_fin=fecha_fin))


@router.get("/contratos/{id_contrato}/documentos/boleta")
def documento_boleta(
    id_contrato: int,
    fecha_cese: date,
    motivo: Literal["renuncia", "despido"] = "renuncia",
    db: Session = Depends(get_db),
):
    return ok(service.generar_documento_boleta(db, id_contrato, fecha_cese=fecha_cese, motivo=motivo))


@router.post("/asistencia", status_code=201)
def asistencia(payload: AsistenciaCreate, db: Session = Depends(get_db)):
    return ok(service.registrar_asistencia(db, payload))


@router.post("/destajo", status_code=201)
def destajo(payload: DestajoCreate, db: Session = Depends(get_db)):
    return ok(service.registrar_destajo(db, payload))


@router.get("/planilla")
def planilla(desde: date | None = None, hasta: date | None = None, db: Session = Depends(get_db)):
    data = service.list_planilla(db, desde=desde, hasta=hasta)
    return ok(data, {"total": len(data)})


@router.get("/reportes/globales")
def reportes_globales(db: Session = Depends(get_db)):
    return ok(service.reportes_globales(db))


@router.get("/buscar")
def buscar(q: str = Query(min_length=1, max_length=80), db: Session = Depends(get_db)):
    data = service.buscar_empleados(db, q)
    return ok(data, {"total": len(data)})


@router.patch("/empleados/{id_empleado}/area")
def actualizar_area(id_empleado: int, payload: AreaEmpleadoUpdate, db: Session = Depends(get_db)):
    return ok(service.actualizar_area_empleado(db, id_empleado, payload.area, payload.id_tipo_empleado))


@router.get("/auditoria")
def auditoria(limit: int = Query(default=200, ge=1, le=500), db: Session = Depends(get_db)):
    data = service.list_auditoria(db, limit=limit)
    return ok(data, {"total": len(data)})
