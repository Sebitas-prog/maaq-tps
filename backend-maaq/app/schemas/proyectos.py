from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class ProyectoCreate(BaseModel):
    id_sector: int = Field(gt=0)
    id_tipo_edificacion: int = Field(gt=0)
    nombre: str = Field(min_length=1, max_length=50)
    objetivo: str = Field(min_length=1, max_length=500)
    presupuesto: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    jefe_proyecto: str = Field(min_length=1, max_length=50)
    historial_descripcion: str = Field(min_length=1, max_length=500)
    fecha_actualizacion: date
    id_tipo_estado: int = Field(gt=0)


class ProyectoEstadoUpdate(BaseModel):
    descripcion: str = Field(min_length=1, max_length=500)
    fecha_actualizacion: date
    id_tipo_estado: int = Field(gt=0)


class ClienteProyectoCreate(BaseModel):
    id_cliente: int = Field(gt=0)
    fecha_inicio: date
    fecha_fin: date
    monto_base: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    id_pais: int = Field(gt=0)

    @field_validator("fecha_fin")
    @classmethod
    def validar_fechas(cls, value: date, info):
        inicio = info.data.get("fecha_inicio")
        if inicio and value < inicio:
            raise ValueError("La fecha de fin no puede ser anterior a la fecha de inicio")
        return value


class EquipoProyectoCreate(BaseModel):
    id_equipo: int = Field(gt=0)
