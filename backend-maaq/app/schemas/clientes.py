from pydantic import BaseModel, ConfigDict, Field


class ClienteBase(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id_tipo_documento: int = Field(gt=0)
    numero_documento: str = Field(min_length=4, max_length=15)
    email: str | None = Field(default=None, max_length=100)
    id_codigo_postal: int = Field(gt=0)
    id_tipo_calle: int = Field(gt=0)
    nombre_calle: str = Field(min_length=1, max_length=50)
    numero_calle: str = Field(min_length=1, max_length=9)


class ClienteNaturalCreate(ClienteBase):
    apellido_paterno: str = Field(min_length=1, max_length=50)
    apellido_materno: str = Field(min_length=1, max_length=50)
    nombres: str | None = Field(default=None, max_length=50)
    celular: str = Field(min_length=6, max_length=10)


class ClienteJuridicoCreate(ClienteBase):
    razon_social: str = Field(min_length=1, max_length=50)
    telefono: str | None = Field(default=None, max_length=20)


class DireccionClienteUpdate(BaseModel):
    id_codigo_postal: int = Field(gt=0)
    id_tipo_calle: int = Field(gt=0)
    nombre_calle: str = Field(min_length=1, max_length=50)
    numero_calle: str = Field(min_length=1, max_length=9)
    usuario: str = Field(default="sistema", max_length=50)


class ContactoNaturalUpdate(BaseModel):
    celular: str = Field(min_length=6, max_length=10)
    email: str | None = Field(default=None, max_length=100)
    usuario: str = Field(default="sistema", max_length=50)


class ContactoJuridicoUpdate(BaseModel):
    telefono: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=100)
    usuario: str = Field(default="sistema", max_length=50)
