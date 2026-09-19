"""FastAPI app, router registration, startup hooks.

Owned by Task 01 — see tasks/01-foundation.md.
"""

import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.engine import make_url

from app.config import settings
from app.db import Base, engine
from app import models  # noqa: F401 — registers all model classes with Base
from app.api import health


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the database when the application starts."""

    # Create the parent directory for a file-based SQLite database.
    database_url = make_url(settings.DATABASE_URL)

    if database_url.get_backend_name() == "sqlite":
        database_path = database_url.database

        if database_path and database_path != ":memory:":
            Path(database_path).parent.mkdir(parents=True, exist_ok=True)

    # Create all tables defined by the registered SQLAlchemy models.
    Base.metadata.create_all(bind=engine)

    yield

    # No additional shutdown cleanup is currently required.


app = FastAPI(
    title="PS21 DocuTrust API",
    version="0.1.0",
    lifespan=lifespan,
)


@app.exception_handler(Exception)
async def global_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
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


# Register routers under the /api/v1 prefix.
app.include_router(health.router, prefix="/api/v1")

# TODO Task 04/06/07/10: Include other routers when implemented.
# from app.api import document_types, documents, verifications
# app.include_router(document_types.router, prefix="/api/v1")
# app.include_router(documents.router, prefix="/api/v1")
# app.include_router(verifications.router, prefix="/api/v1")