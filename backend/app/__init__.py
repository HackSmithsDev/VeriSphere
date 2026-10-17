from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import APP_NAME, FRONTEND_ORIGINS
from app.core.exceptions import register_exception_handlers
from app.core.lifespan import lifespan
from app.api.router import router as api_router


def create_app() -> FastAPI:
    application = FastAPI(
        title=APP_NAME,
        description=(
            "Web platform for verified academic milestones, co-curricular student "
            "achievements, shareable portfolios, and institutional activity reports."
        ),
        version="1.0.0",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=FRONTEND_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_exception_handlers(application)
    application.include_router(api_router)

    @application.get("/health", tags=["operations"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return application