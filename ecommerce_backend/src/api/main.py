from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="APIs for Vintage Market Hub backend services.",
    version="0.1.0",
    openapi_tags=[
        {"name": "health", "description": "Service health and diagnostics"},
        {"name": "auth", "description": "Authentication and authorization"},
        {"name": "listings", "description": "Product listings management"},
        {"name": "transactions", "description": "Payments and transactions"},
    ],
)

# Configure CORS using environment
allow_origins = settings.CORS_ORIGINS if settings.CORS_ORIGINS else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["health"], summary="Health Check")
def health_check():
    """Simple health check endpoint that returns service status."""
    return {"message": "Healthy"}


# Placeholder for including API routers (to be added in subsequent steps)
# from src.api.v1.endpoints import auth, listings
# app.include_router(auth.router, prefix=settings.API_V1_PREFIX, tags=["auth"])
# app.include_router(listings.router, prefix=settings.API_V1_PREFIX, tags=["listings"])
