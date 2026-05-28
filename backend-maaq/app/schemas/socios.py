from pydantic import BaseModel, Field


class SocioCreate(BaseModel):
    id_tipo_documento: int = Field(gt=0)
    numero_documento: str = Field(min_length=4, max_length=15)
    apellido_paterno: str = Field(min_length=1, max_length=50)
    apellido_materno: str | None = Field(default=None, max_length=50)
    nombres: str | None = Field(default=None, max_length=50)
    id_codigo_postal: int = Field(gt=0)
    id_tipo_calle: int = Field(gt=0)
    nombre_calle: str = Field(min_length=1, max_length=50)
    numero_calle: str = Field(min_length=1, max_length=9)
    email: str = Field(min_length=5, max_length=50)
    celular: str = Field(min_length=6, max_length=20)


class AsociacionCreate(BaseModel):
    codigo_departamento: str = Field(min_length=1, max_length=8)
    id_codigo_postal: int = Field(gt=0)
    id_tipo_calle: int = Field(gt=0)
    nombre_calle: str = Field(min_length=1, max_length=50)
    numero_calle: str = Field(min_length=1, max_length=9)
    razon_social: str = Field(min_length=1, max_length=50)
    denominacion: str = Field(min_length=1, max_length=50)
    id_departamento: int = Field(gt=0)


class SocioAsociacionCreate(BaseModel):
    id_socio: int = Field(gt=0)
    id_asociacion: int = Field(gt=0)
