"""FastAPI app, router registration, startup hooks.

Owned by Task 01 — see tasks/01-foundation.md.
"""

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.api import health


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup sequence per docs/backend.md
    # 1. Settings already loaded and validated at import time (fail-fast)
    # 2. Create SQLAlchemy engine/session factory — TODO Task 02
    # 3. Run Base.metadata.create_all() — TODO Task 02
    # 4. Routers already registered below
    # 5. Health endpoint exposed
    yield
    # Shutdown hook — placeholder for future cleanup


app = FastAPI(
    title="PS21 DocuTrust API",
    version="0.1.0",
    lifespan=lifespan,
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    correlation_id = uuid.uuid4().hex
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Internal server error",
                "details": {"correlation_id": correlation_id},
            }
        },
    )


# Register routers under /api/v1 prefix (fixed by api.md)
app.include_router(health.router, prefix="/api/v1")
# TODO Task 04/06/07/10: Include other routers when implemented
# from app.api import document_types, documents, verifications
# app.include_router(document_types.router, prefix="/api/v1")
# app.include_router(documents.router, prefix="/api/v1")
# app.include_router(verifications.router, prefix="/api/v1")