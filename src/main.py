"""
Main FastAPI application entry point.
"""
from fastapi import FastAPI

app = FastAPI(title="Research Paper RAG System")

# Import routes
from src.api.routes.query import router as query_router

# Add API metadata
app.description = """
Research Paper RAG System API

This API provides intelligent query capabilities across research papers using RAG (Retrieval Augmented Generation).
"""

# Include routes
app.include_router(
    query_router,
    prefix="/api/v1",
    tags=["query"]
)