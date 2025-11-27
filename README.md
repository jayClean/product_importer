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
  Celery workers on Redis for CSV ingestion & webhook pings, local disk storage
  for CSV staging (shared filesystem between API and worker), and Alembic migrations.
- **Frontend**: React (Vite) single-page app with React Query, modular
  components (Upload wizard, product grid, webhook manager), SSE/polling hooks,
  and toast notifications.
- **Async Handling**: Upload requests only enqueue Celery jobs to avoid timeout
  limits. Workers stream CSV chunks, emit progress via Redis, and persist
  results. Webhook tests also run via Celery to keep UI responsive.
- **Deployment**: Single containerized service (API + worker together) on Railway,
  frontend on Vercel, with managed PostgreSQL (Supabase) and Redis (Upstash) instances.
  All services use free tier options for zero-cost deployment.

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

## Deployment Strategy

This application is deployed using a **free-tier stack** that keeps costs at $0/month while providing production-ready infrastructure.

### Architecture Overview

The application uses a **monolithic service approach** where both the FastAPI API server and Celery worker run in the same container. This design choice allows them to share the filesystem for uploaded CSV files, avoiding the need for external object storage (S3) and keeping the deployment simple.

### Production Stack

#### Backend (Railway)
- **Hosting**: Railway (free tier with $5/month credit)
- **Service Type**: Single web service running both API and Celery worker
- **Start Command**: Uses `backend/start.sh` script that:
  - Starts Celery worker in background with `--pool=solo` (single-threaded, optimized for containers)
  - Starts FastAPI server in foreground
  - Both processes share the same filesystem for uploads
- **Key Configuration**:
  - Celery uses `solo` pool (no forking, better for containers)
  - File uploads stored in `storage/uploads` directory (absolute path resolution)
  - Graceful shutdown handling for both processes

#### Database (Supabase)
- **Service**: Supabase PostgreSQL (free tier)
- **Features**: 500 MB storage, automatic backups, connection pooling
- **Connection**: Direct connection string with SSL

#### Cache/Message Broker (Upstash)
- **Service**: Upstash Redis (free tier)
- **Usage**: 
  - Celery message broker and result backend
  - Progress tracking for CSV imports
  - 10,000 commands/day free tier limit
- **Configuration**: SSL-enabled connection (`rediss://`) with certificate validation disabled (required by Celery)

#### Frontend (Vercel)
- **Hosting**: Vercel (free tier)
- **Framework**: React + Vite
- **Build**: Static site generation
- **Environment**: Configured with `VITE_API_BASE_URL` pointing to Railway backend

### Key Deployment Decisions

1. **Single Service for API + Worker**
   - **Why**: Allows shared filesystem for CSV uploads without S3
   - **Trade-off**: Both processes share resources, but sufficient for free tier usage
   - **Implementation**: `start.sh` script manages both processes with proper cleanup

2. **Local Disk Storage**
   - **Why**: Avoids S3 costs and complexity for MVP
   - **How**: Absolute path resolution ensures consistency across processes
   - **Location**: `backend/storage/uploads` (resolved to absolute path)

3. **Celery Solo Pool**
   - **Why**: Better for containerized environments, avoids fork issues
   - **Benefit**: Simpler, more reliable, lower resource usage
   - **Trade-off**: Single-threaded (but sufficient for CSV processing)

4. **Free Tier Services**
   - **Cost**: $0/month total
   - **Limitations**: 
     - Railway: Limited to $5/month credit (usually sufficient)
     - Upstash: 10k commands/day (enough for moderate usage)
     - Supabase: 500 MB database (sufficient for MVP)

### Environment Variables

**Backend (Railway)**:
- `DATABASE_URL`: Supabase PostgreSQL connection string
- `REDIS_URL`: Upstash Redis connection string
- `CELERY_BROKER_URL`: Same as REDIS_URL
- `CELERY_RESULT_URL`: Same as REDIS_URL
- `UPLOADS_DIR`: Optional (defaults to `backend/storage/uploads`)
- `LOG_LEVEL`: Logging level (default: INFO)
- `CORS_ORIGINS`: Comma-separated list of allowed frontend origins
- `CELERY_MEMORY_BASELINE`: Memory warning threshold (default: `500M`)
- `CELERY_MEMORY_LIMIT`: Hard memory limit (default: `800M`)

**Frontend (Vercel)**:
- `VITE_API_BASE_URL`: Backend API URL (e.g., `https://your-api.railway.app`)

### Deployment Process

1. **Backend Setup**:
   - Create Supabase project and get connection string
   - Create Upstash Redis database and get connection string
   - Deploy to Railway with start command: `cd backend && bash start.sh`
   - Configure all environment variables
   - Run database migrations: `alembic upgrade head`

2. **Frontend Setup**:
   - Build frontend: `cd frontend && npm run build`
   - Deploy to Vercel with root directory: `frontend`
   - Set `VITE_API_BASE_URL` environment variable
   - Configure CORS on backend to allow Vercel domain

3. **Verification**:
   - Test API health endpoint
   - Verify Celery worker is running (check Railway logs)
   - Test CSV upload and processing
   - Verify frontend can connect to backend

### Scaling Considerations

For production at scale, consider:
- **Separate services**: Deploy API and worker separately for better resource isolation
- **Object storage**: Move to S3 for file uploads when using separate services
- **Higher concurrency**: Switch Celery to `prefork` pool with multiple workers
- **Database**: Upgrade Supabase plan for more storage/connections
- **Redis**: Upgrade Upstash plan for higher command limits

## Documentation

Detailed guides are available in the `docs/` directory covering:
- Core features (upload flow, product management, webhooks, SSE)
- Infrastructure setup (Redis, Celery, local and production testing)
- Deployment guides (backend, frontend, free tier options)
- Memory management and OOM prevention
- API testing and troubleshooting

## Next Steps
1. Flesh out database migrations, session dependency, and repository layer.
2. Implement CSV staging + Celery workflow with progress publisher.
3. Build frontend components incrementally, starting with UploadWizard +
   progress indicator, then Product and Webhook tabs.
4. Add tests (unit/integration) and deployment assets (Docker, CI).