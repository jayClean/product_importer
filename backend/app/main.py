"""FastAPI application bootstrap with router wiring placeholders."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import uploads, products, webhooks, jobs, health


def create_app() -> FastAPI:
    """Instantiate the FastAPI app and include top-level routers."""
    app = FastAPI(title="Acme Product Importer", version="0.1.0")

    # Configure CORS for frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",  # Vite dev server
            "http://localhost:3000",  # Alternative dev port
            # Add production frontend URL when deployed
            # "https://your-frontend-domain.com",
        ],
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
