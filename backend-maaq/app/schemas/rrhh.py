from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ContratacionCreate(BaseModel):
    id_tipo_documento: int = Field(default=1, gt=0)
    numero_documento: str = Field(min_length=4, max_length=15)
    apellido_paterno: str = Field(min_length=1, max_length=50)
    apellido_materno: str = Field(min_length=1, max_length=50)
    nombres: str = Field(min_length=1, max_length=50)
    email: str = Field(min_length=5, max_length=100)
    celular: str = Field(min_length=6, max_length=20)
    id_tipo_empleado: int | None = Field(default=None, gt=0)
    area: str | None = Field(default=None, max_length=50)
    obra: str = Field(min_length=1, max_length=100)
    cargo: str = Field(min_length=1, max_length=80)
    fecha_inicio: date
    fecha_fin: date
    salario_diario: Decimal = Field(gt=0, decimal_places=2)

    @field_validator("fecha_fin")
    @classmethod
    def validar_rango(cls, value: date, info):
        inicio = info.data.get("fecha_inicio")
        if inicio and value < inicio:
            raise ValueError("La fecha fin no puede ser anterior al inicio")
        return value


class RenovacionContrato(BaseModel):
    fecha_fin: date


class AsistenciaCreate(BaseModel):
    id_empleado: int = Field(gt=0)
    id_contrato: int | None = Field(default=None, gt=0)
    fecha: date
    obra: str = Field(min_length=1, max_length=100)
    estado: Literal["presente", "tardanza", "inasistencia", "permiso", "descanso"] = "presente"
    horas: Decimal = Field(default=Decimal("8.00"), ge=0, le=24, decimal_places=2)
    extras: Decimal = Field(default=Decimal("0.00"), ge=0, decimal_places=2)
    observacion: str | None = Field(default=None, max_length=250)


class DestajoCreate(BaseModel):
    id_empleado: int = Field(gt=0)
    id_contrato: int | None = Field(default=None, gt=0)
    fecha: date
    obra: str = Field(min_length=1, max_length=100)
    partida: str = Field(min_length=1, max_length=120)
    metrado: Decimal = Field(gt=0, decimal_places=2)
    tarifa: Decimal = Field(ge=0, decimal_places=2)
    observacion: str | None = Field(default=None, max_length=250)


class AreaEmpleadoUpdate(BaseModel):
    area: str = Field(min_length=1, max_length=50)
    id_tipo_empleado: int | None = Field(default=None, gt=0)
