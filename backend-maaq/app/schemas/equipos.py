from pydantic import BaseModel, Field


class EquipoCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=50)
    descripcion: str = Field(min_length=1, max_length=500)
