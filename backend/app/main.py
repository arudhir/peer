"""Main FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.api.routes import experiments, metadata, tiles
from app.config import config

# Configure logger
logger.add(
    "logs/pica_{time}.log",
    rotation="500 MB",
    retention="10 days",
    level=config.log_level,
)

# Create FastAPI app
app = FastAPI(
    title="PICA Microscopy Viewer API",
    description="High-performance microscopy image viewer for OME-TIFF and OME-Zarr",
    version="0.1.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# TODO: Add authentication middleware when features.enable_auth is True
# Example:
# if config.features.enable_auth:
#     from app.auth import CognitoAuthMiddleware
#     app.add_middleware(CognitoAuthMiddleware)


# Include routers
app.include_router(experiments.router, prefix="/api", tags=["experiments"])
app.include_router(metadata.router, prefix="/api", tags=["metadata"])
app.include_router(tiles.router, prefix="/api", tags=["tiles"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "PICA Microscopy Viewer API",
        "version": "0.1.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    from app.core.cache import get_cache

    cache_stats = None
    if config.cache.enabled:
        try:
            cache = get_cache()
            cache_stats = cache.stats()
        except Exception as e:
            logger.warning(f"Could not get cache stats: {e}")

    return {
        "status": "healthy",
        "config": {
            "s3_endpoint": config.s3.endpoint_url,
            "cache_enabled": config.cache.enabled,
            "use_zarr": config.features.use_zarr,
        },
        "cache": cache_stats,
    }


@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    logger.info("Starting PICA Microscopy Viewer API")
    logger.info(f"S3 endpoint: {config.s3.endpoint_url}")
    logger.info(f"S3 bucket: {config.s3.bucket_name}")
    logger.info(f"Cache enabled: {config.cache.enabled}")
    logger.info(f"Cache root: {config.cache.root_path}")
    logger.info(f"Use Zarr: {config.features.use_zarr}")

    # Initialize cache
    if config.cache.enabled:
        from app.core.cache import get_cache

        cache = get_cache()
        logger.info(f"Cache initialized with max size: {config.cache.max_size_gb} GB")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown."""
    logger.info("Shutting down PICA Microscopy Viewer API")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=config.server.host,
        port=config.server.port,
        reload=config.server.reload,
        log_level=config.log_level.lower(),
    )
