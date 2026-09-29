from fastapi import FastAPI

from src.api.routes.ap import router as ap_router
from src.api.routes.ar import router as ar_router
from src.api.routes.health import router as health_router
from src.core.config import settings
from src.core.logging import logger


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        debug=settings.DEBUG,
    )

    app.include_router(health_router)
    app.include_router(ap_router)
    app.include_router(ar_router)

    logger.info(f"Initialized {settings.PROJECT_NAME} v{settings.VERSION} with AP and AR routes.")
    return app


app = create_app()
