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
        {"name": "users", "description": "User profiles and preferences"},
        {"name": "listings", "description": "Product listings management"},
        {"name": "offers", "description": "Offers lifecycle and actions"},
        {"name": "negotiations", "description": "Negotiation threads for offers"},
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


# Include API routers
from src.api.routers.auth import router as auth_router  # noqa: E402
from src.api.routers.users import router as users_router  # noqa: E402
from src.api.routers.listings import router as listings_router  # noqa: E402
from src.api.routers.offers import router as offers_router  # noqa: E402
from src.api.routers.negotiations import router as negotiations_router  # noqa: E402

app.include_router(auth_router, prefix=settings.API_V1_PREFIX, tags=["auth"])
app.include_router(users_router, prefix=settings.API_V1_PREFIX, tags=["users"])
app.include_router(listings_router, prefix=settings.API_V1_PREFIX, tags=["listings"])
app.include_router(offers_router, prefix=settings.API_V1_PREFIX, tags=["offers"])
app.include_router(negotiations_router, prefix=settings.API_V1_PREFIX, tags=["negotiations"])
