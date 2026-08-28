import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1.ai import router as ai_router
from app.api.v1.auth import router as auth_router
from app.api.v1.concepts import router as concepts_router
from app.api.v1.graph import router as graph_router
from app.api.v1.learning_paths import router as learning_paths_router
from app.api.v1.notebooks import router as notebooks_router
from app.api.v1.notes import router as notes_router
from app.api.v1.progress import router as progress_router
from app.api.v1.search import router as search_router
from app.api.v1.tags import router as tags_router
from app.api.v1.tutor import router as tutor_router
from app.core.config import settings
from app.db.session import Base, engine


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("nova")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up NOVA backend...")
    # Initialize pgvector extension and create tables if not existing
    try:
        if engine.dialect.name == "postgresql":
            async with engine.connect() as conn:
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                await conn.commit()
            await engine.dispose()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.warning(f"Database initialization note: {e}")
    yield
    logger.info("Shutting down NOVA backend...")


app = FastAPI(
    title="NOVA — Personal Knowledge OS API",
    description="Backend API for NOVA: Capture. Connect. Learn.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global Exception Handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    code = f"HTTP_{exc.status_code}"
    if exc.status_code == 404:
        code = "NOT_FOUND"
    elif exc.status_code == 401:
        code = "UNAUTHORIZED"
    elif exc.status_code == 403:
        code = "FORBIDDEN"
    elif exc.status_code == 400:
        code = "BAD_REQUEST"

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "data": None,
            "error": {
                "code": code,
                "message": exc.detail,
            },
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for err in exc.errors():
        loc = " -> ".join(str(item) for item in err.get("loc", []))
        errors.append(f"{loc}: {err.get('msg')}")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "data": None,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid request parameters",
                "details": errors,
            },
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled internal error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "data": None,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred. Please try again.",
            },
        },
    )


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "app": "NOVA",
        "version": "1.0.0",
        "environment": settings.APP_ENV,
    }


# Include Routers under both /api/v1 and /api for convenience
for prefix in ["/api/v1", "/api"]:
    app.include_router(auth_router, prefix=prefix)
    app.include_router(notebooks_router, prefix=prefix)
    app.include_router(notes_router, prefix=prefix)
    app.include_router(concepts_router, prefix=prefix)
    app.include_router(tags_router, prefix=prefix)
    app.include_router(graph_router, prefix=prefix)
    app.include_router(search_router, prefix=prefix)
    app.include_router(tutor_router, prefix=prefix)
    app.include_router(learning_paths_router, prefix=prefix)
    app.include_router(ai_router, prefix=prefix)
    app.include_router(progress_router, prefix=prefix)

