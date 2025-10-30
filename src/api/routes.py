"""
Main router configuration.
"""
from fastapi import APIRouter
from .routes import query, papers, analytics

router = APIRouter()

# Include all route modules
router.include_router(query.router, tags=["query"])
router.include_router(papers.router, tags=["papers"])
router.include_router(analytics.router, tags=["analytics"])