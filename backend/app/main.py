"""FastAPI application bootstrap with router wiring placeholders."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import logging

from app.api.routers import uploads, products, webhooks, jobs, health
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class CORSDebugMiddleware(BaseHTTPMiddleware):
    """Middleware to log CORS-related headers for debugging."""
    async def dispatch(self, request: Request, call_next):
        origin = request.headers.get("Origin")
        if origin:
            logger.info(f"[CORS Debug] Request Origin: {origin}")
            print(f"[CORS Debug] Request Origin: {origin}")
        response = await call_next(request)
        return response


def create_app() -> FastAPI:
    """Instantiate the FastAPI app and include top-level routers."""
    app = FastAPI(title="Acme Product Importer", version="0.1.0")
    
    settings = get_settings()
    
    # Debug: Log CORS origins being used
    cors_origins = settings.cors_origins
    logger.info(f"[CORS] Allowed origins: {cors_origins}")
    print(f"[CORS] Allowed origins: {cors_origins}")  # Also print to stdout for Render logs

    # Add CORS debug middleware to log incoming origins
    app.add_middleware(CORSDebugMiddleware)

    # Configure CORS for frontend
    # Allow origins from environment variable CORS_ORIGINS (comma-separated)
    # Defaults to localhost for development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,  # Already a list from property
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],  # Expose all headers to frontend
    )

    app.include_router(health.router)
    app.include_router(uploads.router, prefix="/api/uploads", tags=["uploads"])
    app.include_router(products.router, prefix="/api/products", tags=["products"])
    app.include_router(webhooks.router, prefix="/api/webhooks", tags=["webhooks"])
    app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])

    return app


app = create_app()
