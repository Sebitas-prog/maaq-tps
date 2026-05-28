from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api.router import api_router
from app.core.errors import AppError
from app.core.settings import get_settings
from app.schemas.common import ok


settings = get_settings()

app = FastAPI(title=settings.app_name, version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)


@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: AppError):
    payload = {"ok": False, "error": exc.message, "code": exc.code}
    if exc.field:
        payload["campo"] = exc.field
    if exc.details:
        payload["details"] = exc.details
    return JSONResponse(status_code=exc.status_code, content=payload)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "ok": False,
            "error": "Datos invalidos",
            "code": "VALIDATION_ERROR",
            "errores": [
                {"campo": ".".join(str(part) for part in err["loc"] if part != "body"), "mensaje": err["msg"]}
                for err in exc.errors()
            ],
        },
    )


@app.exception_handler(SQLAlchemyError)
async def sql_error_handler(_: Request, exc: SQLAlchemyError):
    return JSONResponse(
        status_code=500,
        content={
            "ok": False,
            "error": "Error de base de datos",
            "code": "DATABASE_ERROR",
            "details": str(exc.__cause__ or exc),
        },
    )


@app.get("/api/health")
def health():
    return ok({"status": "ok", "app": settings.app_name, "environment": settings.environment})


app.include_router(api_router, prefix="/api")
