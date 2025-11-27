# Acme Product Importer – Architectural Plan

Implementation details will follow, but this document captures the agreed plan,
high-level architecture, and API outlines so we can iterate deliberately.

## Requirements Recap
- Upload CSVs (~500k rows) via UI with overwrite-on-SKU semantics and realtime
- Provide full CRUD UI for products with filtering, pagination, inline edits,
  and destructive confirmations.
- Manage multiple webhooks, including add/edit/delete/test and surfacing test
  telemetry .
- Use Python web framework + Celery/Dramatiq, SQLAlchemy (unless Django),
  PostgreSQL, Redis/RabbitMQ for async work, and deploy to a public host.

## Solution Overview
- **Backend**: FastAPI for REST + SSE endpoints, SQLAlchemy ORM on PostgreSQL,
  Celery workers on Redis for CSV ingestion & webhook pings, object storage
  adapter (S3/local) for temporary CSV staging, and Alembic migrations.
- **Frontend**: React (Vite) single-page app with React Query, modular
  components (Upload wizard, product grid, webhook manager), SSE/polling hooks,
  and toast notifications.
- **Async Handling**: Upload requests only enqueue Celery jobs to avoid Heroku
  30s limits. Workers stream CSV chunks, emit progress via Redis, and persist
  results. Webhook tests also run via Celery to keep UI responsive.
- **Deployment**: Containerized services (API, worker, scheduler) suitable for
  Render/Heroku/GCP. Separate managed PostgreSQL + Redis instances.

## Folder Structure
```
backend/
  app/
    api/             # FastAPI routers + schemas + dependencies
    core/            # config/logging/utilities
    db/              # models, session, migrations
    services/        # csv ingest, webhook dispatch, progress tracking
    storage/         # abstraction over S3/local
    utils/           # csv validation, batching helpers
    workers/         # Celery app + tasks
  tests/
    unit/
    integration/
frontend/
  src/
    api/             # REST wrappers
    components/      # Upload wizard, tables, dialogs, etc.
    hooks/           # e.g. useUploadProgress, usePagination
    pages/           # Dashboard with tabs
    state/           # query client + filter store
    utils/           # csv helpers, validators
    styles/
  public/
```

See the actual directories/files in the repo for specific placeholders and
docstrings that describe their intended responsibilities.

## API Outline

### Uploads & Jobs
- `POST /api/uploads/` – accepts CSV via multipart, stages file, spawns Celery
  `import_products` task, returns `job_id`.
- `GET /api/uploads/{job_id}/status` – friendly status tailored for upload UI.
- `GET /api/jobs/{job_id}` – generic job telemetry for other background work.

### Products
- `GET /api/products` – list with filters (`sku`, `name`, `description`,
  `active`) and pagination metadata.
- `POST /api/products` – create record from UI form.
- `PUT /api/products/{product_id}` – update record (inline/modal).
- `DELETE /api/products/{product_id}` – delete single product.
- `DELETE /api/products` – bulk delete (requires confirmation token later).

### Webhooks
- `GET /api/webhooks` – list configs with status + last test result.
- `POST /api/webhooks` – add webhook (URL, event, secret, enabled flag).
- `PUT /api/webhooks/{id}` – edit webhook details.
- `DELETE /api/webhooks/{id}` – remove webhook.
- `POST /api/webhooks/{id}/test` – enqueue webhook test task and surface result.

### Health
- `GET /health/live` – static liveness.
- `GET /health/ready` – future check for DB + Redis connectivity.

All routers/tasks/services include placeholder comments describing the logic we
will implement next, ensuring a clear to-do list for subsequent steps.

## Documentation

### Core Features
- [Upload Flow](docs/upload_flow.md) - CSV upload logic and processing flow
- [Product Management](docs/product_management.md) - Product CRUD operations and soft delete
- [Bulk Delete](docs/bulk_delete.md) - Bulk delete functionality and considerations
- [SSE Implementation](docs/sse_implementation.md) - Server-Sent Events for progress streaming

### Infrastructure
- [Redis & Celery Setup](docs/redis_celery_setup.md) - Infrastructure setup guide
- [Local Testing with Celery & Redis](docs/local_testing_celery_redis.md) - Local development setup and testing
- [Production Celery & Redis Setup](docs/production_celery_redis_setup.md) - Production deployment configuration

### Webhooks
- [Webhook Guide](docs/webhook_guide.md) - Comprehensive webhook configuration and usage
- [Webhook Testing Steps](docs/webhook_testing_steps.md) - Quick reference for testing webhooks
- [Webhook Production Deployment](docs/webhook_production_deployment.md) - Production webhook considerations

### Frontend
- [UI Setup and Testing](docs/ui_setup_and_testing.md) - Complete guide for setting up, building, and testing the React frontend
- [Frontend Deployment Guide](docs/frontend_deployment_guide.md) - Complete guide for deploying frontend to production

### Deployment
- [Backend Deployment Guide](docs/backend_deployment_guide.md) - **Complete step-by-step backend deployment (API + Celery)**
- [Connecting Frontend to Backend](docs/frontend_backend_connection.md) - **How to configure frontend to connect to backend**

### Quick Reference
- [Backend Deployment Summary](docs/backend_deployment_summary.md) - Quick reference for backend deployment

### Deployment
- [Free Tier Backend Deployment](docs/free_tier_backend_deployment.md) - **Recommended**: Complete free tier deployment for API + Celery worker
- [Free Tier Setup Guide](docs/free_tier_setup_guide.md) - Complete step-by-step free tier deployment
- [Free Tier Cloud Services](docs/free_tier_cloud_services.md) - Free tier options for PostgreSQL, Redis, and hosting
- [Celery Worker Hosting](docs/celery_worker_hosting.md) - Complete guide for hosting Celery workers
- [Production Setup Guide](docs/production_setup_guide.md) - Set up PostgreSQL, Redis, and Celery for production testing
- [Production API Testing](docs/production_api_testing.md) - Comprehensive API testing guide for production environment
- [Heroku Deployment](docs/heroku_deployment.md) - Complete Heroku deployment guide with free tier options
- [Heroku Testing Guide](docs/heroku_testing_guide.md) - Testing procedures for deployed application

## Next Steps
1. Flesh out database migrations, session dependency, and repository layer.
2. Implement CSV staging + Celery workflow with progress publisher.
3. Build frontend components incrementally, starting with UploadWizard +
   progress indicator, then Product and Webhook tabs.
4. Add tests (unit/integration) and deployment assets (Docker, CI).