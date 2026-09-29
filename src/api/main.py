from fastapi import FastAPI

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

    logger.info(f"Initialized {settings.PROJECT_NAME} v{settings.VERSION}")
    return app


app = create_app()
