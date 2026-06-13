import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

from src.infrastructure.config import settings
from src.api.routes import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic goes here
    print("🚀 Starting up application services...")

    # Ensure media directories exist
    os.makedirs("media/", exist_ok=True)

    yield
    # Shutdown logic goes here
    print("🛑 Shutting down application services...")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc"
    )

    # 1. Configure Middlewares
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 2. Attach Routers
    app.include_router(api_router, prefix="/api/v1")
    app.mount("/media", StaticFiles(directory="media"), name="media")

    @app.get("/healthz", tags=["health"])
    async def healthz():
        from fastapi import Response
        return Response(content="OK", media_type="text/plain")

    return app


# The actual FastAPI instance
app = create_app()