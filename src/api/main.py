import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI

from src.api.routes.ap import router as ap_router
from src.api.routes.ar import router as ar_router
from src.api.routes.audit import router as audit_router
from src.api.routes.documents import router as documents_router
from src.api.routes.governance import router as governance_router
from src.api.routes.health import router as health_router
from src.api.routes.risk import router as risk_router
from src.core.config import settings
from src.core.logging import logger
from src.database.audit_repository import default_audit_repository


@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_running_loop()
    default_audit_repository.set_event_loop(loop)
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        debug=settings.DEBUG,
        lifespan=lifespan,
    )

    app.include_router(health_router)
    app.include_router(documents_router)
    app.include_router(ap_router)
    app.include_router(ar_router)
    app.include_router(governance_router)
    app.include_router(risk_router)
    app.include_router(audit_router)

    logger.info(f"Initialized {settings.PROJECT_NAME} v{settings.VERSION} with Documents, AP, AR, Governance, Risk, and Audit routes.")

    return app


app = create_app()
