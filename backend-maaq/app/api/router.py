from fastapi import APIRouter

from app.api.routes import auth, catalogos, clientes, dashboard, empleados, equipos, proyectos, rrhh, socios


api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(catalogos.router, prefix="/catalogos", tags=["catalogos"])
api_router.include_router(clientes.router, prefix="/clientes", tags=["clientes"])
api_router.include_router(empleados.router, prefix="/empleados", tags=["empleados"])
api_router.include_router(proyectos.router, prefix="/proyectos", tags=["proyectos"])
api_router.include_router(equipos.router, prefix="/equipos", tags=["equipos"])
api_router.include_router(socios.router, prefix="/socios", tags=["socios"])
api_router.include_router(rrhh.router, prefix="/rrhh", tags=["rrhh"])
