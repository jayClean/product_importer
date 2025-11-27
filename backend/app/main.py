"""FastAPI application bootstrap with router wiring placeholders."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import uploads, products, webhooks, jobs, health
from app.core.config import get_settings


def create_app() -> FastAPI:
    """Instantiate the FastAPI app and include top-level routers."""
    app = FastAPI(title="Acme Product Importer", version="0.1.0")

    settings = get_settings()

    # Configure CORS for frontend
    # Allow origins from environment variable CORS_ORIGINS (comma-separated)
    # Defaults to localhost for development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,  # Already a list from property
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(uploads.router, prefix="/api/uploads", tags=["uploads"])
    app.include_router(products.router, prefix="/api/products", tags=["products"])
    app.include_router(webhooks.router, prefix="/api/webhooks", tags=["webhooks"])
    app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])

    return app


app = create_app()
