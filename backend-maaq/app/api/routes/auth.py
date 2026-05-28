from fastapi import APIRouter

from app.core.errors import AppError
from app.core.settings import get_settings
from app.schemas.auth import LoginRequest
from app.schemas.common import ok


router = APIRouter()


@router.get("/demo")
def demo_credentials():
    settings = get_settings()
    return ok({"email": settings.demo_email, "password": settings.demo_password})


@router.post("/login")
def login(payload: LoginRequest):
    settings = get_settings()
    if payload.email != settings.demo_email or payload.password != settings.demo_password:
        raise AppError("Credenciales incorrectas", 401, "INVALID_CREDENTIALS")

    return ok(
        {
            "token": "demo-maaq-token",
            "usuario": {
                "id": 1,
                "nombre": "Administrador MAAQ",
                "email": settings.demo_email,
                "rol": "demo",
            },
        }
    )
