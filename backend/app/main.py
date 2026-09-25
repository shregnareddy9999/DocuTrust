"""FastAPI app, router registration, startup hooks.

Owned by Task 01 — see tasks/01-foundation.md.
"""

import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.engine import make_url

from app.config import settings
from app.db import Base, engine
from app import models  # noqa: F401 — registers all model classes with Base
from app.api import health, documents, document_types, verifications


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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def root() -> str:
    """Browser landing page. API contracts live under /api/v1 (docs/api.md)."""

    return """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>DocuTrust API</title>
    <style>
      body { font-family: system-ui, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; }
      main { max-width: 40rem; margin: 12vh auto; padding: 0 1.5rem; }
      h1 { font-size: 2rem; margin-bottom: 0.35rem; }
      p { color: #cbd5e1; line-height: 1.5; }
      a { color: #93c5fd; }
      ul { line-height: 1.8; }
    </style>
  </head>
  <body>
    <main>
      <h1>DocuTrust</h1>
      <p>This is the API service for the DocuTrust demonstration. It is not a government service and does not prove that a real document is authentic.</p>
      <p>Open the application UI at <a href="http://localhost:5173/">http://localhost:5173/</a>.</p>
      <ul>
        <li><a href="/docs">Interactive API docs</a></li>
        <li><a href="/api/v1/health">Health check</a></li>
      </ul>
    </main>
  </body>
</html>
"""


@app.exception_handler(HTTPException)
async def http_exception_handler(
    request: Request,
    exc: HTTPException,
) -> JSONResponse:
    # HTTPException raised by our code with detail={"error": {...}}
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail,
        )
    # Fallback for any other HTTPException
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": "HTTP_ERROR",
                "message": str(exc.detail),
                "details": {},
            }
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    if isinstance(exc, HTTPException):
        raise exc
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
app.include_router(documents.router, prefix="/api/v1")
app.include_router(document_types.router, prefix="/api/v1")
app.include_router(verifications.router, prefix="/api/v1")