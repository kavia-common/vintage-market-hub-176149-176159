# Package init for API routers.
# Expose commonly used routers (optional)
try:
    from .auth import router as auth_router  # noqa: F401
    from .users import router as users_router  # noqa: F401
    from .regions import router as regions_router  # noqa: F401
    from .categories import router as categories_router  # noqa: F401
    from .listings import router as listings_router  # noqa: F401
    from .offers import router as offers_router  # noqa: F401
    from .negotiations import router as negotiations_router  # noqa: F401
    from .swaps import router as swaps_router  # noqa: F401
    from .transactions import router as transactions_router  # noqa: F401
    from .webhooks import router as webhooks_router  # noqa: F401
except Exception:
    # During certain tooling operations, imports may fail; ignore to avoid side effects.
    pass
