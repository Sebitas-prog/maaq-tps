from datetime import date

from pydantic import BaseModel, Field, field_validator


class EmpleadoCreate(BaseModel):
    id_tipo_documento: int = Field(gt=0)
    numero_documento: str = Field(min_length=4, max_length=15)
    apellido_paterno: str = Field(min_length=1, max_length=50)
    apellido_materno: str = Field(min_length=1, max_length=50)
    nombres: str = Field(min_length=1, max_length=50)
    email: str = Field(min_length=5, max_length=100)
    celular: str = Field(min_length=6, max_length=20)
    id_tipo_empleado: int | None = Field(default=None, gt=0)
    area: str | None = Field(default=None, max_length=50)
    id_departamento: int | None = Field(default=None, gt=0)
    id_equipo: int | None = Field(default=None, gt=0)
    fecha_asignacion: date | None = None
    fecha_culminacion: date | None = None

    @field_validator("fecha_culminacion")
    @classmethod
    def validar_fechas(cls, value: date | None, info):
        inicio = info.data.get("fecha_asignacion")
        if value and inicio and value < inicio:
            raise ValueError("La fecha de culminacion no puede ser anterior a la asignacion")
        return value


class EmpleadoUpdate(BaseModel):
    id_tipo_documento: int | None = Field(default=None, gt=0)
    numero_documento: str | None = Field(default=None, min_length=4, max_length=15)
    apellido_paterno: str | None = Field(default=None, min_length=1, max_length=50)
    apellido_materno: str | None = Field(default=None, min_length=1, max_length=50)
    nombres: str | None = Field(default=None, min_length=1, max_length=50)
    email: str | None = Field(default=None, min_length=5, max_length=100)
    celular: str | None = Field(default=None, min_length=6, max_length=20)
    usuario: str = Field(default="sistema", max_length=50)


class EquipoEmpleadoAssign(BaseModel):
    id_empleado: int = Field(gt=0)
    fecha_asignacion: date
    fecha_culminacion: date

    @field_validator("fecha_culminacion")
    @classmethod
    def validar_rango(cls, value: date, info):
        inicio = info.data.get("fecha_asignacion")
        if inicio and value < inicio:
            raise ValueError("La fecha de culminacion no puede ser anterior a la asignacion")
        return value
