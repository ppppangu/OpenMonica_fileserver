"""
File Server API - Main Application Entry Point

This file configures and initializes the FastAPI application, including:
- Setting up the application lifecycle (startup/shutdown events).
- Configuring CORS middleware.
- Including API routers from different versions (legacy, v2).
"""

import sys
from pathlib import Path
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

# --- Path Correction ---
# Add the project root to sys.path to allow for absolute imports
# across directories (e.g., from src, from app).
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# --- Module Imports ---
# Import routers from the versioned API directories.
from app.legacy.endpoints import router as legacy_router
from app.v1.endpoints import router as v1_router
from app.v2.endpoints import router as v2_router

# Import legacy components required for startup.
# This dependency should be removed as the legacy code is phased out.
from app.legacy.compatibility_adapter import mk_need_path


# --- Logging Configuration ---
log_path = Path(__file__).parent / "logs"
logger.add(log_path / f"{datetime.now().strftime('%Y-%m-%d')}.log", rotation="100 MB")


# --- Application Lifecycle ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages application startup and shutdown events.
    """
    logger.info("--- Starting File Server API ---")
    # Perform startup tasks, e.g., creating necessary directories.
    # This currently relies on a legacy function.
    mk_need_path()
    logger.info("Application startup tasks complete.")
    
    yield
    
    logger.info("--- Shutting Down File Server API ---")
    # Perform cleanup tasks here if needed.


# --- FastAPI App Initialization ---
app = FastAPI(
    title="File Server API",
    description="API for file uploading, processing, and management.",
    version="2.0.0",  # Updated version to reflect new structure
    lifespan=lifespan,
)

# --- Middleware Configuration ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production for security
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# --- API Router Inclusion ---
# Include the legacy API router.
# All these endpoints will be available at the root path (e.g., /upload_minio).
app.include_router(legacy_router, tags=["Legacy"])

# Include the new V1 API router with a version prefix.
# All V1 endpoints will be available under /v1 (e.g., /v1/files).
app.include_router(v1_router, prefix="/v1", tags=["V1"])

# Include the new V2 API router with a version prefix.
# All V2 endpoints will be available under /v2 (e.g., /v2/status).
app.include_router(v2_router, prefix="/v2", tags=["V2"])


# --- Health Check Endpoint ---
@app.get("/health", tags=["Monitoring"])
async def health_check():
    """
    A simple health check endpoint for the root application.
    """
    return {"status": "ok", "message": "API is running."}


# --- Main Execution Block ---
if __name__ == "__main__":
    import uvicorn

    # It's recommended to run the server using a process manager like Gunicorn with Uvicorn workers in production.
    # Example: uvicorn app.main:app --host 0.0.0.0 --port 8087 --reload
    uvicorn.run(app, host="0.0.0.0", port=8087)